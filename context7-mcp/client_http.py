"""Very simple Python MCP client for Context7's HTTP-transport MCP server.

Same idea as client.py, but instead of spawning a stdio subprocess it talks to
a Context7 MCP server already listening over HTTP (start it with:

    npx -y @upstash/context7-mcp --transport http --port 3000

). Uses ``streamable_http_client`` (streamable HTTP transport, protocol
2025-06-18) from the official MCP SDK — the same transport opencode uses for
remote MCP servers.

Usage:
    python client_http.py                     # connect + list tools
    python client_http.py resolve NAME QUERY  # two-step flow: resolve ID, then fetch docs
    python client_http.py call TOOL ARGS_JSON # call any single tool with JSON args
"""

from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_URL = "http://127.0.0.1:3000/mcp"


def print_result(result) -> None:
    for content in result.content:
        if getattr(content, "type", "") == "text":
            print(content.text)
        else:
            print(content)


async def list_tools() -> None:
    async with streamable_http_client(SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            info = session.server_info
            print(f"[info] connected to HTTP {info.name} v{info.version}")
            tools = await session.list_tools()
            print(f"[info] server exposes {len(tools.tools)} tools:")
            for t in tools.tools:
                props = ", ".join(t.input_schema.get("properties", {}))
                print(f"  - {t.name}({props})")


async def demo_resolve(library_name: str, query: str) -> None:
    async with streamable_http_client(SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print(f"\n>>> step 1: resolve-library-id(libraryName={library_name!r}, query={query!r})")
            result = await session.call_tool(
                "resolve-library-id",
                arguments={"libraryName": library_name, "query": query},
            )
            print_result(result)

            library_id = input("\nPaste the Context7 library ID to query docs (e.g. /vercel/next.js): ").strip()
            if not library_id:
                print("[info] no library ID given, stopping")
                return

            print(f"\n>>> step 2: query-docs(libraryId={library_id!r}, query={query!r})")
            result = await session.call_tool(
                "query-docs",
                arguments={"libraryId": library_id, "query": query},
            )
            print_result(result)


async def call_tool(tool_name: str, tool_args: dict | None) -> None:
    async with streamable_http_client(SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"\n>>> call_tool({tool_name!r}, {tool_args!r})")
            result = await session.call_tool(tool_name, arguments=tool_args or {})
            if result.is_error:
                print("[error] server returned an error result")
            print_result(result)


def main() -> None:
    if len(sys.argv) >= 4 and sys.argv[1] == "resolve":
        asyncio.run(demo_resolve(sys.argv[2], sys.argv[3]))
    elif len(sys.argv) >= 2 and sys.argv[1] == "call":
        tool_args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
        asyncio.run(call_tool(sys.argv[2], tool_args))
    else:
        asyncio.run(list_tools())


if __name__ == "__main__":
    main()