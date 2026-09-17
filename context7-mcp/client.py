"""Very simple Python MCP client for Context7's LOCAL MCP server.

Spawns ``@upstash/context7-mcp`` (Node.js) as a local stdio subprocess and
talks to it over stdin/stdout using the official MCP protocol — exactly what
opencode/Claude/Cursor do when you register a "local" MCP server.

Usage:
    python client.py                     # connect + list tools
    python client.py resolve NAME QUERY  # two-step flow: resolve ID, then fetch docs
    python client.py call TOOL ARGS_JSON # call any single tool with JSON args
"""

from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CMD = "npx"
ARGS = ["-y", "@upstash/context7-mcp"]
SERVER_NAME = "context7-local"


def print_result(result) -> None:
    for content in result.content:
        if getattr(content, "type", "") == "text":
            print(content.text)
        else:
            print(content)


async def list_tools() -> None:
    async with stdio_client(StdioServerParameters(command=CMD, args=ARGS)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            info = session.server_info
            print(f"[info] connected to local {info.name} v{info.version}")
            tools = await session.list_tools()
            print(f"[info] server exposes {len(tools.tools)} tools:")
            for t in tools.tools:
                props = ", ".join(t.input_schema.get("properties", {}))
                print(f"  - {t.name}({props})")


async def demo_resolve(library_name: str, query: str) -> None:
    async with stdio_client(StdioServerParameters(command=CMD, args=ARGS)) as (read, write):
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
    async with stdio_client(StdioServerParameters(command=CMD, args=ARGS)) as (read, write):
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