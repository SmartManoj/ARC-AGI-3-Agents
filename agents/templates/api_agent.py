import json
import logging
import os
import textwrap
import time
import asyncio

import uvicorn
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from fastapi import FastAPI

from ..agent import Agent
from ..structs import FrameData, GameAction

logger = logging.getLogger('arc')

class ActionRequest(BaseModel):
    """Action request structure."""
    action: str = Field(description="The action to take (RESET, ACTION1-6)")
    x: Optional[int] = Field(description="Coordinate X for ACTION6", default=None)
    y: Optional[int] = Field(description="Coordinate Y for ACTION6", default=None)
    object_number: Optional[int] = Field(description="Object number (1-9) for ACTION6", default=None)


class APIAgent(Agent):
    """An agent that receives actions from a API client."""

    MAX_ACTIONS = 400

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

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

    def execute_action(self, action_request: ActionRequest):
        try:
            # Convert action request to GameAction
            action_name = action_request.action
            action = GameAction.from_name(action_name)
            
            # Set coordinates for ACTION6
            x = y = None
            if action_name == "ACTION6":
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

            current_frame = self.get_current_frame()
            action.reasoning = {
                "agent_type": "api_agent",
                'action_chosen': action.name,
                "game_context": {
                    "score": current_frame.score if current_frame else 0,
                    "state": current_frame.state.name if current_frame else "UNKNOWN",
                    "action_counter": self.action_counter,
                    "frame_count": len(self.frames),
                },
            }
            if action == GameAction.ACTION6:
                action.reasoning['x'] = x
                action.reasoning['y'] = y
                action.reasoning['object_number'] = action_request.object_number

            # Execute the action
            if frame_data := self.take_action(action):
                # Set guid from server response for subsequent actions
                if frame_data.guid and not self.guid:
                    self.guid = frame_data.guid
                    logger.info(f"Received guid from server: {self.guid}")
                
                self.append_frame(frame_data)
                
                extra = f' ({x}, {y})' if action.name == "ACTION6" else ''
                logger.info(f"action executed: {action.name}{extra}, score: {frame_data.score}")
                self.action_counter += 1
                
                return {
                    "success": True,
                    "frame": frame_data.frame,
                    "score": frame_data.score,
                    "state": frame_data.state.name
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to execute action - no frame returned"
                }

        except Exception as e:
            logger.error(f"Error executing action: {e}")
            return {
                "success": False,
                "error": f"Error executing action: {e}"
            }

    def is_done(self, frames: List[FrameData], latest_frame: FrameData) -> bool:
        """Check if the game is done."""
        return latest_frame.state.value in ["WIN", "GAME_OVER"]

    def choose_action(
        self, frames: List[FrameData], latest_frame: FrameData
    ) -> GameAction:
        """Required abstract method - Agent doesn't choose actions, they come from client."""
        # Return RESET as default fallback
        return GameAction.RESET

    async def handle_game_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle game action from FastAPI."""
        try:
            action_request = ActionRequest(**action_data)
            response = self.execute_action(action_request)
            return response
        except Exception as e:
            logger.error(f"Error handling game action: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def main(self) -> None:
        """Override main method to run FastAPI server directly in main."""
        logger.info("Starting agent with FastAPI server")
        
        try:
            # start the game
            self.execute_action(ActionRequest(action="START"))

            app = FastAPI()

            @app.get("/")
            async def read_root():
                return {"message": f"API Agent for game {self.game_id} is running"}
            
            @app.get("/execute_action")
            async def execute_action(action: str, x: int = None, y: int = None, object_number: int = None):
                """Execute a game action (RESET, ACTION1-6)."""
                return await self.handle_game_action({
                    "action": action,
                    "x": x,
                    "y": y,
                    "object_number": object_number
                })
            
            logger.info("FastAPI initialized with game action tool")
            
            # Start FastAPI server - actions will be executed immediately when received
            logger.info("FastAPI server started - waiting for actions")
            host = os.environ.get('API_HOST', 'localhost')
            port = int(os.environ.get('API_PORT', 8000)) + self.game_idx
            uvicorn.run(app, host=host, port=port)
            
        except Exception as e:
            logger.error(f"Failed to initialize FastAPI: {e}")
            return
        finally:
            # Cleanup
            logger.info("Agent cleanup complete") 