import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = "https://mcp.deepwiki.com/mcp"


async def main():
    async with streamable_http_client(URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.list_tools()

            for tool in result.tools:
                print(f"\nTool: {tool.name}")
                print(tool.description)
                print(json.dumps(tool.input_schema, indent=2))



# interactive, use this:
#await main()

# run from terminal, use this
#asyncio.run(main())
