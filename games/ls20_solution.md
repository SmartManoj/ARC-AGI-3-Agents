# LS20 Locksmith Game Solution

## Overview
This document describes the solution approach for the LS20 locksmith game, which involves navigating a locksmith character to collect the correct key, rotate it if needed, and unlock doors while managing limited movement steps.

## Game Elements

### Core Objects
- **Locksmith** (Orange cap): The player character that moves around the grid
- **Lock** (Black object): Contains the expected key pattern
- **Key** (9x9 grid): The current key that needs to be matched with lock requirements
- **Key Chooser** (6x6 blue object): Tool to select different keys
- **Key Rotator** (6x6 light gray object): Tool to rotate the current key
- **Key Color Chooser** (8x8 white object): Tool to change key colors
- **Refill Steps** (Small object): Replenishes available movement steps
- **Available Steps** (1x1 objects): Individual movement tokens

## Solution Strategy

### 1. Grid Analysis & Helper Functions
```python
# Import utility functions from arc_tools.helper
from arc_tools.helper import find_path, compress_grid, scale_to_9x9

# Detect all objects in the grid
objs = detect_objects(grid, ignore_color=FrameColor.DARK_GRAY)
filter_colors = [FrameColor.RED.value, FrameColor.GREEN.value]
objs = [obj for obj in objs if obj.color not in filter_colors]
```

### 2. Key Pattern Matching
- Extract expected key patterns from lock objects
- Rotate expected keys to match actual key's corner colors
- Use similarity checking to determine if current key is correct

```python
# Generate expected keys from locks
for obj in objs:
    if FrameColor.BLACK.value in obj.colors:
        lock = obj
        expected_key = scale_to_9x9(detect_objects(Grid(lock))[0])
        expected_keys.append(expected_key)

# Check if current key matches any expected pattern
is_correct_key = any(expected_key.is_similar(key, ignore_color=1) for expected_key in expected_keys)
```

### 3. Decision Logic
The solution prioritizes actions based on game state:

#### Priority Order:
1. **Key Color Mismatch**: Go to key color chooser or recome
2. **Correct Key**: 
   - If no rotation needed: Go directly to lock
   - If rotation needed: Go to key rotator first
3. **Incorrect Key**: Go to key chooser to get correct key
4. **Low Steps**: Go to refill steps if movement is limited

```python
if key_color_mismatch:
    if key_color_chooser is None:
        path_directions = recome(grid, locksmith, scale_factor)
    else:
        path_directions = find_path(grid, locksmith, key_color_choosers[0], scale_factor)
elif is_correct_key:
    if key_rotate_count == 0:
        path_directions = find_path(grid, locksmith, lock, scale_factor)
    else:
        path_directions = find_path(grid, locksmith, key_rotator, scale_factor)
elif not path_directions_to_refill or (len(available_steps)) - 2 >= len(path_directions_to_refill):
    if key_chooser is None:
        path_directions = recome(grid, locksmith, scale_factor)
    else:
        path_directions = find_path(grid, locksmith, key_chooser, scale_factor)
else:
    path_directions = path_directions_to_refill
```

### 5. Movement Execution
- Convert path coordinates to movement commands
- Execute actions using `execute_action()`


## Key Features

### Obstacle Management
- Dynamically blocks unnecessary tools based on current state
- Prevents locksmith from visiting tools that aren't needed

### Step Management
- Tracks available movement steps
- Prioritizes refill when steps are limited
- Ensures path length doesn't exceed available steps

### Recome Strategy
- Implements "recome" (return) movement when no direct path exists
- Allows locksmith to backtrack and find alternative routes

## Technical Implementation

### Dependencies
- `arc_tools.grid`: Grid manipulation and object detection
- `arc_tools.plot`: Visualization utilities
- `arc_tools.helper`: Utility functions (pathfinding, grid compression, scaling)
- `game_handler`: Game action execution

### Key Functions
- `find_path()`: BFS pathfinding implementation (imported from arc_tools.helper)
- `compress_grid()`: Reduce grid size for pathfinding (imported from arc_tools.helper)
- `scale_to_9x9()`: Normalize grids to 9x9 format (imported from arc_tools.helper)
- `recome()`: Return movement strategy

## Success Metrics
- Successfully navigates locksmith to correct tools
- Manages limited movement steps efficiently
- Matches key patterns with lock requirements
- Handles key rotation and color changes
- Completes level within step constraints 