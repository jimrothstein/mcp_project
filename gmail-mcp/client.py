"""Very simple MCP client for Google's hosted Gmail MCP server.

Connects to https://gmailmcp.googleapis.com/mcp/v1 using the shared OAuth
client in credentials.json, runs the authorization-code + PKCE flow with a
local loopback redirect, then lists tools and optionally calls one.

Usage:
    python client.py                 # connect + list tools
    python client.py TOOL ARGS_JSON  # connect + call TOOL with ARGS_JSON
"""

from __future__ import annotations

import asyncio
import json
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx2

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)

SERVER_URL = "https://gmailmcp.googleapis.com/mcp/v1"

# Work around an upstream SDK quirk: Google's PRM advertises its authorization
# server with a trailing slash ("https://accounts.google.com/") while the
# authorization-server metadata issuer omits it. The SDK compares these as raw
# strings and rejects the mismatch, aborting the OAuth flow. Normalize the
# trailing slash before comparing.
import mcp.client.auth.oauth2 as _oauth2

_orig_validate_metadata_issuer = _oauth2.validate_metadata_issuer


def _validate_metadata_issuer(metadata, expected_issuer):
    _orig_validate_metadata_issuer(metadata, expected_issuer.rstrip("/"))


_oauth2.validate_metadata_issuer = _validate_metadata_issuer

HERE = Path(__file__).parent
CREDENTIALS_FILE = HERE / "credentials.json"
TOKEN_FILE = HERE / "mcp_tokens.json"


class JsonTokenStorage:
    """Persist the OAuth client info and tokens to a JSON file."""

    def __init__(self, path: Path):
        self.path = path
        self._client_info = self._load_client_info()

    def _load_client_info(self) -> OAuthClientInformationFull | None:
        # Our client is pre-registered in credentials.json, so the SDK must not
        # perform dynamic client registration (Google doesn't support it).
        creds = json.loads(CREDENTIALS_FILE.read_text())["installed"]
        return OAuthClientInformationFull(
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            token_endpoint_auth_method="client_secret_post",
            redirect_uris=[u for u in creds.get("redirect_uris", [])],
            grant_types=["authorization_code", "refresh_token"],
        )

    async def get_tokens(self) -> OAuthToken | None:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text())
        return OAuthToken.model_validate(data)

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.path.write_text(tokens.model_dump_json(indent=2))
        print(f"[auth] tokens saved to {self.path}")

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self._client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self._client_info = client_info


class LoopbackCallback:
    """Serve the OAuth redirect on a local port and capture the auth code."""

    def __init__(self):
        self._redirect_uri: str | None = None
        self._server: HTTPServer | None = None
        self._result: dict | None = None

    def start(self) -> str:
        host, port = "localhost", 0

        class Handler(BaseHTTPRequestHandler):
            cb = self

            def do_GET(self):
                path = urlparse(self.path)
                params = parse_qs(path.query)
                cb = self.__class__.cb
                cb._result = {k: v[0] for k, v in params.items()}
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                body = (
                    "<html><body><h3>Authorization complete. "
                    "You can close this window and return to the terminal.</h3></body></html>"
                ).encode()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self._server = HTTPServer((host, port), Handler)
        actual_port = self._server.server_address[1]
        self._redirect_uri = f"http://{host}:{actual_port}/"
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self._redirect_uri

    async def wait_for_callback(self):
        while self._result is None:
            await asyncio.sleep(0.1)
        code = self._result.get("code")
        state = self._result.get("state")
        return code, state


def build_client_metadata(redirect_uri: str) -> OAuthClientMetadata:
    creds = json.loads(CREDENTIALS_FILE.read_text())["installed"]
    return OAuthClientMetadata(
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
        redirect_uris=[redirect_uri],
        token_endpoint_auth_method="client_secret_post",
        grant_types=["authorization_code", "refresh_token"],
        scope="openid https://www.googleapis.com/auth/gmail.readonly",
    )


async def run(tool_name: str | None, tool_args: dict | None) -> None:
    callback_server = LoopbackCallback()
    redirect_uri = callback_server.start()

    client_metadata = build_client_metadata(redirect_uri)
    storage = JsonTokenStorage(TOKEN_FILE)

    async def show_auth_url(url: str) -> None:
        print(f"\n[oauth] Authorize here:\n{url}\n", flush=True)
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()

    async def handle_callback():
        code, state = await callback_server.wait_for_callback()
        print(f"[oauth] Received authorization code")
        from mcp.shared.auth import AuthorizationCodeResult

        return AuthorizationCodeResult(code=code, state=state)

    auth = OAuthClientProvider(
        server_url=SERVER_URL,
        client_metadata=client_metadata,
        storage=storage,
        redirect_handler=show_auth_url,
        callback_handler=handle_callback,
    )

    async with create_mcp_http_client(auth=auth) as http_client:
        async with streamable_http_client(SERVER_URL, http_client=http_client) as streams:
            read_stream, write_stream = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print(f"\n[info] Connected to {SERVER_URL}\n")

                tools = await session.list_tools()
                print(f"[info] Server exposes {len(tools.tools)} tools:")
                for t in tools.tools:
                    print(f"  - {t.name}: {t.description.splitlines()[0] if t.description else ''}")

                if tool_name:
                    print(f"\n[info] Calling tool {tool_name!r}...")
                    result = await session.call_tool(tool_name, arguments=tool_args or {})
                    print("\n[result]")
                    for content in result.content:
                        if getattr(content, "type", "") == "text":
                            print(content.text)
                        else:
                            print(content)


def main() -> None:
    tool_name = sys.argv[1] if len(sys.argv) > 1 else None
    tool_args = None
    if len(sys.argv) > 2:
        tool_args = json.loads(sys.argv[2])
    asyncio.run(run(tool_name, tool_args))


if __name__ == "__main__":
    main()
