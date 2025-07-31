import json
import logging
import os
import textwrap
import time
import asyncio
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from fastmcp import FastMCP

from ..agent import Agent
from ..structs import FrameData, GameAction
from .rest_agent import RestAgent

logger = logging.getLogger('arc')

class MCPAgent(RestAgent):
    """An MCP-enabled agent that receives actions from MCP client using FastMCP."""

    MAX_ACTIONS = 400

    def main(self) -> None:
        """Override main method to run FastMCP server directly in main."""
        logger.info("Starting MCP agent with FastMCP server")
        
        # Initialize FastMCP
        try:
            mcp = FastMCP(stateless_http=True)
            
            # Register game action handler
            @mcp.tool()
            async def game_action(action: str, x: int = None, y: int = None, object_number: int = None):
                """Execute a game action (RESET, ACTION1-6)."""
                return await self.handle_game_action({
                    "action": action,
                    "x": x,
                    "y": y,
                    "object_number": object_number
                })
            
            logger.info("FastMCP initialized with game action tool")
            
            # Start FastMCP server - actions will be executed immediately when received
            logger.info("FastMCP server started - waiting for actions")
            host = os.environ.get('MCP_HOST', 'localhost')
            port = os.environ.get('MCP_PORT', 8000)
            mcp.run(f'streamable-http', host=host, port=port)
            
        except Exception as e:
            logger.error(f"Failed to initialize FastMCP: {e}")
            return
        finally:
            # Cleanup
            logger.info("MCP agent cleanup complete") 