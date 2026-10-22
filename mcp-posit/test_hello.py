import asyncio

from fastmcp import Client
from server import mcp


async def main():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("Tools:", [tool.name for tool in tools])

        result = await client.call_tool("hello", {})
        print("Result:", result.data)

        assert result.data == "Hello"


asyncio.run(main())