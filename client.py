"""FastMCP Client Example
This example demonstrates how to use the FastMCP client to interact with a server.
Not a part of this application, but a demonstration for debugging and testing purposes.
"""

import asyncio
import os

from fastmcp import Client
from fastmcp.client.auth import BearerAuth
from fastmcp.client.transports import StreamableHttpTransport


async def main():
    token = os.environ.get("ACCESS_TOKEN")
    if not token:
        raise ValueError("Please set the ACCESS_TOKEN environment variable.")
    client = Client(
        StreamableHttpTransport("http://localhost:8000/mcp"),
        auth=BearerAuth(token=token),
    )
    async with client:
        # Basic server interaction
        await client.ping()

        # List available operations
        tools = await client.list_tools()
        print(tools)
        # Call a specific operation
        result = await client.call_tool_mcp(
            name="search", arguments={"q": "what is mcp?"}
        )
        print(result)
        # Call time
        result = await client.call_tool_mcp(name="time", arguments={})
        print(result)
        # Call fetch
        result = await client.call_tool_mcp(
            name="fetch", arguments={"url": ["https://kagi.com"]}
        )
        print(result)


asyncio.run(main())
