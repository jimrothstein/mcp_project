"""Python MCP client for the Hugging Face remote MCP server.

Connects to Hugging Face's hosted MCP server (https://huggingface.co/mcp) over
the streamable HTTP transport — the same transport opencode uses for its
"remote" MCP servers — and speaks the Model Context Protocol to it.

Authentication uses a Hugging Face access token read from the HF_TOKEN
environment variable and sent as an ``Authorization: Bearer <token>`` header.
That is exactly what opencode's ``{env:HF_TOKEN}`` substitution produces for
the ``huggingface`` remote server registered in ``opencode.jsonc``.

Usage:
    python hf_client.py                        # connect + list tools
    python hf_client.py whoami                 # call hf_whoami
    python hf_client.py call TOOL ARGS_JSON    # call any tool with JSON args
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_URL = "https://huggingface.co/mcp"


def token() -> str:
    value = os.environ.get("HF_TOKEN")
    if not value:
        sys.exit(
            "error: HF_TOKEN is not set "
            "(create a token at https://huggingface.co/settings/tokens)"
        )
    return value


def make_http_client() -> httpx2.AsyncClient:
    return httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token()}"},
        timeout=httpx2.Timeout(30, read=300),
    )


def print_result(result) -> None:
    if result.is_error:
        print("[error] server returned an error result")
    for content in result.content:
        if getattr(content, "type", "") == "text":
            print(content.text)
        else:
            print(content)


async def list_tools() -> None:
    async with make_http_client() as http:
        async with streamable_http_client(SERVER_URL, http_client=http) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                info = session.server_info
                print(f"[info] connected to {info.name} v{info.version}")
                tools = await session.list_tools()
                print(f"[info] server exposes {len(tools.tools)} tools:")
                for t in tools.tools:
                    props = ", ".join(t.input_schema.get("properties") or {})
                    desc = (t.description or "").splitlines()[0] if t.description else ""
                    print(f"  - {t.name}({props})  {desc}")


async def call_tool(tool_name: str, tool_args: dict | None) -> None:
    async with make_http_client() as http:
        async with streamable_http_client(SERVER_URL, http_client=http) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print(f">>> call_tool({tool_name!r}, {tool_args!r})")
                result = await session.call_tool(tool_name, arguments=tool_args or {})
                print_result(result)


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "whoami":
        asyncio.run(call_tool("hf_whoami", None))
    elif len(sys.argv) >= 2 and sys.argv[1] == "call":
        if len(sys.argv) < 3:
            sys.exit("usage: python hf_client.py call TOOL [ARGS_JSON]")
        tool_args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
        asyncio.run(call_tool(sys.argv[2], tool_args))
    else:
        asyncio.run(list_tools())


if __name__ == "__main__":
    main()
