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

logger = logging.getLogger('arc')

class MCPActionRequest(BaseModel):
    """MCP action request structure."""
    action: str = Field(description="The action to take (RESET, ACTION1-6)")
    x: Optional[int] = Field(description="Coordinate X for ACTION6", default=None)
    y: Optional[int] = Field(description="Coordinate Y for ACTION6", default=None)
    object_number: Optional[int] = Field(description="Object number (1-9) for ACTION6", default=None)


class MCPAgent(Agent):
    """An MCP-enabled agent that receives actions from MCP client using FastMCP."""

    MAX_ACTIONS = 400

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.mcp = None

    def get_current_frame(self) -> Optional[FrameData]:
        """Get the current frame safely."""
        return self.frames[-1] if self.frames else None

    def get_object_coordinates(self, grid: List[List[int]], object_number: int) -> tuple[int, int]:
        """Get the center coordinates of a specific numbered object (1-9)."""
        try:
            import sys
            sys.path.append('../../ARC Tools')
            from arc_tools.grid import Grid, detect_objects, Square
            
            # Create Grid object and detect objects
            grid_obj = Grid(grid)
            
            # Look for 12x12 square objects specifically
            square_12 = Square(12)
            detected_objects = detect_objects(grid_obj, required_object=square_12, ignore_corners=True)
            
            # If we don't find exactly 9 objects, try a more general approach
            if len(detected_objects) != 9:
                detected_objects = detect_objects(grid_obj, ignore_corners=True, max_count=20)
                filtered_objects = []
                for obj in detected_objects:
                    # Look for objects that are approximately 12x12 (the main grid boxes)
                    if (10 <= obj.width <= 14 and 10 <= obj.height <= 14 and 
                        obj.width < len(grid[0]) * 0.3 and obj.height < len(grid) * 0.3):
                        filtered_objects.append(obj)
                detected_objects = filtered_objects[:9]  # Take only the first 9
            
            # Check if object number is valid
            if object_number < 1 or object_number > len(detected_objects):
                logger.warning(f"Invalid object number: {object_number}. Available: 1-{len(detected_objects)}")
                return (32, 32)  # Default center coordinates
            
            # Get the specified object
            obj = detected_objects[object_number - 1]  # Convert to 0-based index
            
            # Calculate center coordinates
            x1, y1 = obj.region.x1, obj.region.y1
            x2, y2 = obj.region.x2, obj.region.y2
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            return (center_x, center_y)
            
        except Exception as e:
            logger.error(f"Failed to get object coordinates: {e}")
            return (0, 0)

    def execute_action(self, action_request: MCPActionRequest):
        """Execute the action from MCP client immediately."""
        logger.info(f"MCP action received: {action_request.action}")
        try:
            # Convert MCP action request to GameAction
            action = GameAction.from_name(action_request.action)
            
            # Set coordinates for ACTION6
            if action_request.action == "ACTION6":
                x = action_request.x
                y = action_request.y
                
                # If object_number is provided, get coordinates from current frame
                if action_request.object_number:
                    try:
                        current_frame = self.get_current_frame()
                        if current_frame and current_frame.frame:
                            current_grid = current_frame.frame[-1]
                            x, y = self.get_object_coordinates(current_grid, action_request.object_number)
                            logger.debug(f"Object {action_request.object_number} selected, coordinates: ({x}, {y})")
                        else:
                            logger.warning("No current frame available for object coordinates")
                            x, y = 32, 32  # Default center coordinates
                    except Exception as e:
                        logger.warning(f"Failed to get object coordinates: {e}")
                        x, y = 32, 32  # Default center coordinates
                else:
                    if x is None or y is None:
                        # return error
                        return {
                            "success": False,
                            "error": "Failed to execute action - no object number or coordinates provided"
                        }
                action.set_data({"x": x, "y": y})
                logger.info(f"Executing ACTION6 at coordinates ({x}, {y})")
            else:
                logger.info(f"Executing action: {action_request.action}")

            # Add MCP metadata
            current_frame = self.get_current_frame()
            action.reasoning = {
                "agent_type": "mcp_agent",
                "mcp_server": "FastMCP",
                "action_source": "mcp_client",
                "game_context": {
                    "score": current_frame.score if current_frame else 0,
                    "state": current_frame.state.name if current_frame else "UNKNOWN",
                    "action_counter": self.action_counter,
                    "frame_count": len(self.frames),
                },
            }

            # Execute the action
            if frame := self.take_action(action):
                # Set guid from server response for subsequent actions
                if frame.guid and not self.guid:
                    self.guid = frame.guid
                    logger.info(f"Received guid from server: {self.guid}")
                
                self.append_frame(frame)
                logger.info(f"MCP action executed: {action.name}, score: {frame.score}")
                self.action_counter += 1
                
                return {
                    "success": True,
                    "message": f"Action '{action_request.action}' executed successfully",
                    "score": frame.score,
                    "state": frame.state.name
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to execute action - no frame returned"
                }

        except Exception as e:
            logger.error(f"Error executing MCP action: {e}")
            return {
                "success": False,
                "error": f"Error executing MCP action: {e}"
            }

    def is_done(self, frames: List[FrameData], latest_frame: FrameData) -> bool:
        """Check if the game is done."""
        return latest_frame.state.value in ["WIN", "GAME_OVER"]

    def choose_action(
        self, frames: List[FrameData], latest_frame: FrameData
    ) -> GameAction:
        """Required abstract method - MCP agent doesn't choose actions, they come from client."""
        # MCP agent doesn't choose actions - they come from client
        # Return RESET as default fallback
        return GameAction.RESET

    async def handle_game_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle game action from FastMCP."""
        try:
            # Create action request
            action_request = MCPActionRequest(
                action=action_data.get("action"),
                x=action_data.get("x"),
                y=action_data.get("y"),
                object_number=action_data.get("object_number")
            )
            
            # Execute the action immediately and return the response
            response = self.execute_action(action_request)
            
            action_name = action_data.get("action")
            logger.info(f"Game action '{action_name}' executed via FastMCP")
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling game action: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def main(self) -> None:
        """Override main method to run FastMCP server directly in main."""
        logger.info("Starting MCP agent with FastMCP server")
        
        # Initialize FastMCP
        try:
            self.mcp = FastMCP(stateless_http=True)
            
            # Register game action handler
            @self.mcp.tool()
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
            mcp_host = os.environ.get('MCP_HOST', 'localhost')
            mcp_port = os.environ.get('MCP_PORT', 8000)
            self.mcp.run(f'streamable-http', host=mcp_host, port=mcp_port)
            
        except Exception as e:
            logger.error(f"Failed to initialize FastMCP: {e}")
            return
        finally:
            # Cleanup
            logger.info("MCP agent cleanup complete") 