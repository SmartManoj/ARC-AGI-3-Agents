import base64
import io
import json
import logging
import os
import textwrap
from typing import Any, Dict, List, Literal, Optional

from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

from ..structs import FrameData, GameAction, FrameColor
from .llm_agents import ReasoningLLM

logger = logging.getLogger('arc')

draw_zone_coordinates = os.environ.get("DRAW_ZONE_COORDINATES", "false").lower() in ["true", '1']
give_level_1_solution = os.environ.get("GIVE_LEVEL_1_SOLUTION", "false").lower() in ["true", '1']
include_images = os.environ.get("INCLUDE_IMAGES", "true").lower() in ["true", '1']

class ReasoningActionResponse(BaseModel):
    """Action response structure for reasoning agent."""

    name: Literal["ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6", "RESET"] = Field(
        description="The action to take."
    )
    reason: str = Field(
        description="Detailed reasoning for choosing this action",
        min_length=10,
        max_length=5000,
    )
    short_description: str = Field(
        description="Brief description of the action", min_length=5, max_length=500
    )
    hypothesis: str = Field(
        description="Current hypothesis about game mechanics",
        min_length=10,
        max_length=2000,
    )
    aggregated_findings: str = Field(
        description="Summary of discoveries and learnings so far",
        min_length=10,
        max_length=2000,
    )
    x: Optional[str] = Field(
        description="Coordinate X for ACTION6 (must be integer 0-63)",
        default=None,
    )
    y: Optional[str] = Field(
        description="Coordinate Y for ACTION6 (must be integer 0-63)",
        default=None,
    )
    object_number: Optional[str] = Field(
        description="Object number to click (1-9) for ACTION6",
        default=None,
    )
    


class ReasoningAgent(ReasoningLLM):
    """A reasoning agent that tracks screen history and builds hypotheses about game rules."""

    MAX_ACTIONS = 400
    DO_OBSERVATION = True
    MODEL = os.environ.get("LLM_MODEL", "o4-mini")
    MESSAGE_LIMIT = 5
    REASONING_EFFORT = "high"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.history: List[ReasoningActionResponse] = []
        self.screen_history: List[bytes] = []
        self.grid_history: List[List[List[int]]] = []
        self.max_screen_history = 10  # Limit screen history to prevent memory leak
        self.max_grid_history = 10  # Limit grid history to prevent memory leak
        self.client = OpenAI(api_key=os.environ.get("LLM_API_KEY", ""), base_url=os.environ.get("LLM_BASE_URL", ""))

    def clear_history(self) -> None:
        """Clear all history when transitioning between levels."""
        self.history = []
        self.screen_history = []
        self.grid_history = []

    def generate_annotated_grid_image(
        self, grid: List[List[int]], cell_size: int = 40, zone_size: int = 16
    ) -> bytes:
        """Generate PIL image of the grid with colored cells and zone coordinates with anotation."""
        if not grid or not grid[0]:
            # Create empty image
            img = Image.new("RGB", (200, 200), color="black")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()

        height = len(grid)
        width = len(grid[0])

        # Create image
        img = Image.new("RGB", (width * cell_size, height * cell_size), color="white")
        draw = ImageDraw.Draw(img)

        # Color mapping for grid cells
        key_colors = {
            0: "#FFFFFF",
            1: "#CCCCCC",
            2: "#999999",
            3: "#666666",
            4: "#333333",
            5: "#000000",
            6: "#E53AA3",
            7: "#FF7BCC",
            8: "#F93C31",
            9: "#1E93FF",
            10: "#88D8F1",
            11: "#FFDC00",
            12: "#FF851B",
            13: "#921231",
            14: "#4FCC30",
            15: "#A356D6"
        }

        # Draw grid cells
        for y in range(height):
            for x in range(width):
                color = key_colors.get(grid[y][x], "#888888")  # default: floor

                # Draw cell
                draw.rectangle(
                    [
                        x * cell_size,
                        y * cell_size,
                        (x + 1) * cell_size,
                        (y + 1) * cell_size,
                    ],
                    fill=color,
                    outline="#000000",
                    width=1,
                )

        # Draw zone coordinates and borders
        if draw_zone_coordinates:
            for y in range(0, height, zone_size):
                for x in range(0, width, zone_size):
                    # Draw zone coordinate label
                    try:
                        font = ImageFont.load_default()
                        zone_text = f"({x},{y})"
                        draw.text(
                            (x * cell_size + 2, y * cell_size + 2),
                            zone_text,
                            fill="#FFFFFF",
                            font=font,
                        )
                    except (ImportError, OSError) as e:
                        logger.debug(f"Could not load font for zone labels: {e}")
                    except Exception as e:
                        logger.error(f"Failed to draw zone label at ({x},{y}): {e}")

                    # Draw zone boundary
                    zone_width = min(zone_size, width - x) * cell_size
                    zone_height = min(zone_size, height - y) * cell_size
                    draw.rectangle(
                        [
                            x * cell_size,
                            y * cell_size,
                            x * cell_size + zone_width,
                            y * cell_size + zone_height,
                        ],
                        fill=None,
                        outline="#FFD700",  # gold border for zone
                        width=2,
                    )

        # Detect objects and add numbered labels
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
                        obj.width < width * 0.3 and obj.height < height * 0.3):
                        filtered_objects.append(obj)
                detected_objects = filtered_objects[:9]  # Take only the first 9
            
            # Draw black boxes around detected objects and add labels
            for i, obj in enumerate(detected_objects):
                # Get object boundaries
                x1, y1 = obj.region.x1, obj.region.y1
                x2, y2 = obj.region.x2, obj.region.y2
                
                # Draw black rectangle around object
                draw.rectangle(
                    [
                        x1 * cell_size,
                        y1 * cell_size,
                        (x2 + 1) * cell_size,
                        (y2 + 1) * cell_size,
                    ],
                    outline="#000000",
                    width=3,
                )
                
                # Add label at center of object
                center_x = (x1 + x2) / 2 * cell_size + cell_size // 2
                center_y = (y1 + y2) / 2 * cell_size + cell_size // 2
                
                # Draw white circle background for label
                label_radius = 15
                draw.ellipse(
                    [
                        center_x - label_radius,
                        center_y - label_radius,
                        center_x + label_radius,
                        center_y + label_radius,
                    ],
                    fill="#FFFFFF",
                    outline="#000000",
                    width=2,
                )
                
                # Add number label
                try:
                    font = ImageFont.load_default()
                    draw.text(
                        (center_x, center_y),
                        str(i + 1),
                        fill="#000000",
                        font=font,
                        anchor="mm",  # center alignment
                    )
                except Exception as e:
                    logger.error(f"Failed to draw number label: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to detect objects for annotation: {e}")

        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

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

    def build_functions(self) -> list[dict[str, Any]]:
        """Build JSON function description of game actions for LLM."""
        schema = ReasoningActionResponse.model_json_schema()
        # The 'name' property is the action to be taken, so we can remove it from the parameters.
        schema["properties"].pop("name", None)
        if "required" in schema:
            schema["required"].remove("name")

        functions: list[dict[str, Any]] = [
            {
                "name": action.name,
                "description": f"Take action {action.name}",
                "parameters": schema,
            }
            for action in [
                GameAction.RESET,
                GameAction.ACTION1,
                GameAction.ACTION2,
                GameAction.ACTION3,
                GameAction.ACTION4,
                GameAction.ACTION5,
                GameAction.ACTION6,
            ]
        ]
        return functions

    def build_tools(self) -> list[dict[str, Any]]:
        """Support models that expect tool_call format."""
        functions = self.build_functions()
        tools: list[dict[str, Any]] = []
        for f in functions:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": f["name"],
                        "description": f["description"],
                        "parameters": f.get("parameters", {}),
                    },
                }
            )
        return tools

    def build_user_prompt(self, latest_frame: FrameData) -> str:
        """Build the user prompt for hypothesis-driven exploration."""
        level_1_solution = '''Level 1 Solution:
Top right map: 1st cell (blue); 2nd cell (red)
Game grid: 9 x 9
initial state: all cells are blue (except central piece)
central piece is the key map which again consists of 3*3 sub-cells consists of gray and white sub-cells and key sub-cell which is at its center. Replace all outer cells in the place of white sub-cells with the color of the key sub-cell. Remaining with the gray sub-cells.

first state that in which sub cells, the gray small cells are in, if center cell is divided into 3*3 sub cells.

ACTION1-5 are no-ops in this game.
Central object is also a no-op.
'''
        
        # Create color mapping information
        color_info = "Color Mapping:\n"
        for color in FrameColor:
            color_info += f"- {color.value}: {color.name}\n"
        
        return textwrap.dedent(
            f"""
You are playing a video game.

Your ultimate goal is to understand the rules of the game.

The game is super simple.

You need to determine how to win the game on your own.

To do so, we will provide you with a view of the game corresponding to the bird-eye view of the game, along with the raw grid data.

{color_info}

IMPORTANT: The game screen shows numbered objects (1-9) with black frame. You can click on these objects by specifying the object number (1-9).

You can do 7 actions:
- RESET (Initialize or restart the game state to level 1)
- ACTION1 (Move Up or Rotate)
- ACTION2 (Move Down or Flip)
- ACTION3 (Move Left or Undo)
- ACTION4 (Move Right or Confirm)
- ACTION5 (Interact or Select)
- ACTION6 (click object by number 1-9)

You can do one action at once.

Every time an action is performed we will provide you with the previous screen and the current screen.

Determine the game rules based on how the game reacted to the previous action (based on the previous screen and the current screen).

Your goal:

1. Experiment the game to determine how it works based on the screens and your actions.
2. Analyse the impact of your actions by comparing the screens.

Define an hypothesis and an action to validate it.

You are currently at level {latest_frame.score + 1}.

IMPORTANT: New levels will be automatically started. No need to click anything to start.

HINT: Focus on the maps in the game to win the game.
        """
        ) + (level_1_solution if give_level_1_solution else '') + ('Golden color lines are drawn on the map for you to easily identify the coordinates.' if draw_zone_coordinates else '')

    def call_llm_with_structured_output(
        self, messages: List[Dict[str, Any]]
    ) -> ReasoningActionResponse:
        """Call LLM with structured output parsing for reasoning agent."""
        try:
            tools = self.build_tools()

            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                tools=tools,
                tool_choice="required",
            )

            self.track_tokens(
                response.usage.total_tokens, response.choices[0].message.content
            )
            self.capture_reasoning_from_response(response)

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            if tool_calls:
                tool_call = tool_calls[0]
                function_args = json.loads(tool_call.function.arguments)
                function_args["name"] = tool_call.function.name
                return ReasoningActionResponse(**function_args)

            with open('response.json', 'w') as f:
                json.dump(response, f)
            raise ValueError("LLM did not return a tool call.")

        except Exception as e:
            logger.error(f"LLM structured call failed: {e}")
            raise e

    def define_next_action(self, latest_frame: FrameData) -> ReasoningActionResponse:
        """Define next action for the reasoning agent."""
        # Generate map image
        current_grid = latest_frame.frame[-1] if latest_frame.frame else []
        map_image = self.generate_annotated_grid_image(current_grid)

        # Build messages
        system_prompt = self.build_user_prompt(latest_frame)

        # Get latest action from history
        latest_action = self.history[-1] if self.history else None

        # Build user message with images
        user_message_content: List[Dict[str, Any]] = []

        # Use the last screen and grid from history as the 'previous_screen' and 'previous_grid'
        previous_screen = self.screen_history[-1] if self.screen_history else None
        previous_grid = self.grid_history[-1] if self.grid_history else None

        if previous_screen and include_images:
            user_message_content.extend(
                [
                    {"type": "text", "text": "Previous screen:"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64.b64encode(previous_screen).decode()}",
                            "detail": "high",
                        },
                    },
                ]
            )
        
        if previous_grid:
            previous_grid_text = self.pretty_print_3d([previous_grid])
            user_message_content.extend(
                [
                    {"type": "text", "text": "Previous grid data:"},
                    {"type": "text", "text": previous_grid_text},
                ]
            )
            # Compute and show grid changes
            current_grid = latest_frame.frame[-1] if latest_frame.frame else []
            changes = []
            if previous_grid and current_grid and len(previous_grid) == len(current_grid) and len(previous_grid[0]) == len(current_grid[0]):
                for y in range(len(previous_grid)):
                    for x in range(len(previous_grid[0])):
                        old = previous_grid[y][x]
                        new = current_grid[y][x]
                        if old != new:
                            changes.append(f"({x},{y}): {old} -> {new}")
            if changes:
                changes_text = "Grid changes (x, y: old -> new):\n" + "\n".join(changes)
            else:
                changes_text = "No grid changes."
            user_message_content.append({"type": "text", "text": changes_text})

        raw_grid_text = self.pretty_print_3d(latest_frame.frame)
        user_message_text = f"Your previous action was: {json.dumps(latest_action.model_dump() if latest_action else None, indent=2)}\n\nRaw Grid:\n{raw_grid_text}\n\nWhat should you do next?"

        if include_images:
            user_message_text += "\n\nAttached is the visual screen."
            current_image_b64 = base64.b64encode(map_image).decode()
            user_message_content.extend(
                [
                    {"type": "text", "text": user_message_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{current_image_b64}",
                            "detail": "high",
                        },
                    },
                ]
            )
        else:
            user_message_content.append({"type": "text", "text": user_message_text})

        # Build messages
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message_content},
        ]

        # Call LLM with structured output
        result = self.call_llm_with_structured_output(messages)

        # Store current screen and grid for next iteration (after using it)
        self.screen_history.append(map_image)
        if len(self.screen_history) > self.max_screen_history:
            self.screen_history.pop(0)
        
        # Store current grid for next iteration
        current_grid = latest_frame.frame[-1] if latest_frame.frame else []
        self.grid_history.append(current_grid)
        if len(self.grid_history) > self.max_grid_history:
            self.grid_history.pop(0)

        return result

    def choose_action(
        self, frames: List[FrameData], latest_frame: FrameData
    ) -> GameAction:
        """Choose action using parent class tool calling with reasoning enhancement."""
        if latest_frame.full_reset:
            self.clear_history()
            return GameAction.RESET

        if not self.history:  # First action must be RESET
            action = GameAction.RESET
            initial_response = ReasoningActionResponse(
                name="RESET",
                reason="Initial action to start the game and observe the environment.",
                short_description="Start game",
                hypothesis="The game requires a RESET to begin.",
                aggregated_findings="No findings yet.",
            )
            self.history.append(initial_response)
            return action

        # Define the next action based on reasoning
        action_response = self.define_next_action(latest_frame)
        self.history.append(action_response)

        # Map the reasoning action name to a GameAction
        action = GameAction.from_name(action_response.name)

        
            
        # Create and attach reasoning metadata
        reasoning_meta = {
            "model": self.MODEL,
            "reasoning_effort": self.REASONING_EFFORT,
            "reasoning_tokens": self._last_reasoning_tokens,
            "total_reasoning_tokens": self._total_reasoning_tokens,
            "agent_type": "reasoning_agent",
            "hypothesis": action_response.hypothesis,
            "aggregated_findings": action_response.aggregated_findings,
            "short_description": action_response.short_description,
            "response": action_response.reason,
            "action_chosen": action.name,
            "game_context": {
                "score": latest_frame.score,
                "state": latest_frame.state.name,
                "action_counter": self.action_counter,
                "frame_count": len(frames),
            },
        }
        # Set coordinates for ACTION6
        if action == GameAction.ACTION6:
            try:
                # Check if object_number is provided
                object_number = int(action_response.object_number)
                if object_number:
                    current_grid = latest_frame.frame[-1] if latest_frame.frame else []
                    x, y = self.get_object_coordinates(current_grid, object_number)
                    logger.debug(f"Object {object_number} selected, coordinates: ({x}, {y})")
                else:
                    # Fall back to direct coordinates
                    x = int(action_response.x) if action_response.x else 0
                    y = int(action_response.y) if action_response.y else 0
                    logger.info(f"Direct coordinates provided: ({x}, {y})")
                
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid coordinates for ACTION6: x={action_response.x}, y={action_response.y}, object_number={action_response.object_number}. Using defaults. Error: {e}")
                x = y = object_number = 0
            action.set_data({"x": x, "y": y})
            reasoning_meta["x"] = x
            reasoning_meta["y"] = y
            reasoning_meta["object_number"] = object_number
        action.reasoning = reasoning_meta

        return action
