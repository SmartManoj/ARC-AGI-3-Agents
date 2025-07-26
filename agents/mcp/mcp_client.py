from fastmcp import Client
import asyncio

async def main():
    async with Client("http://localhost:8000/mcp") as client:
        # tools = await client.call_tool('game_action', arguments={'action': 'RESET', 'x': 32, 'y': 32, 'object_number': 1})
        # click 2,4,6,8
        x,y = 10, 15
        # tools = await client.call_tool('game_action', arguments={'action': 'ACTION6', 'x': x, 'y': y,})
        tools = await client.call_tool('game_action', arguments={'action': 'ACTION6', 'object_number': 2})
        tools = await client.call_tool('game_action', arguments={'action': 'ACTION6', 'object_number': 4})
        tools = await client.call_tool('game_action', arguments={'action': 'ACTION6', 'object_number': 6})
        tools = await client.call_tool('game_action', arguments={'action': 'ACTION6', 'object_number': 8})
        print(tools)
           

if __name__ == "__main__":
    asyncio.run(main())
