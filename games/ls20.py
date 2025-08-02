import game_handler

from game_handler import execute_action


import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('../ARC Tools')

from arc_tools.grid import Grid, detect_objects, GridRegion, GridPoint, SubGrid
from arc_tools.plot import plot_grids, plot_grid
from arc_tools.grid import Square
from arc_tools.logger import logger
from typing import List, Tuple, Optional


from agents.structs import FrameColor
from game_handler import execute_action
from glob import glob
from collections import deque
game_handler.PORT = 8002

def scale_3to2(grid):
    """Scale 9x9 grid to 6x6 by factor 3/2"""
    if len(grid) != 9 or len(grid[0]) != 9:
        raise ValueError("Input grid must be 9x9")
    
    result = [[0 for _ in range(6)] for _ in range(6)]
    
    for i in range(6):
        for j in range(6):
            # Map 6x6 position to 9x9 position
            src_i = int(i * 1.5)
            src_j = int(j * 1.5)
            # Take the value from the source position
            result[i][j] = grid[src_i][src_j]
    
    return Grid(result)

def scale_to_9x9(grid: Grid):
    """Scale grid to 9x9 by factor"""
    grid_size = len(grid)
    new_size = 9
    result = [[0 for _ in range(new_size)] for _ in range(new_size)]
    factor = grid_size / new_size
    
    for i in range(new_size):
        for j in range(new_size):
            # Map 9x9 position to 6x6 position
            src_i = int(i * factor)
            src_j = int(j * factor)
            
            # Take the value from the source position
            result[i][j] = grid[src_i][src_j]
    result = Grid(result, grid.background_color)
    if type(grid) != Grid:
        result = result.as_sub_grid()
    return result

def path_to_moves(path):
    moves = []
    for i in range(1, len(path)):
        prev_row, prev_col = path[i-1]
        curr_row, curr_col = path[i]
        
        if curr_row < prev_row:
            moves.append("move_up")
        elif curr_row > prev_row:
            moves.append("move_down")
        elif curr_col < prev_col:
            moves.append("move_left")
        elif curr_col > prev_col:
            moves.append("move_right")
    return moves

def find_path(grid: Grid, start_obj: SubGrid , end_obj: SubGrid, scale_factor: int) -> Optional[List[Tuple[int, int]]]:
    """
    Find path from S to E in the grid using BFS.
    Returns list of coordinates (row, col) representing the path.
    """
    zone_size = 8 // scale_factor
    start_pos = start_obj.region.x1 // zone_size, start_obj.region.y1 // zone_size
    end_pos = end_obj.region.x1 // zone_size * zone_size / zone_size, end_obj.region.y1 // zone_size * zone_size / zone_size
    grid = compress_grid(grid, start_pos, end_pos, scale_factor)
    print(start_obj.region.start, end_obj.region.start  )
    # print(start_pos, end_pos)
    # for row in grid:
    #     print(''.join(row))
    rows = len(grid)
    cols = len(grid[0])
    
    # Find start (S) and end (E) positions
    start = None
    end = None
    
    for row in range(rows):
        for col in range(cols):
            if grid[row][col] == 'S':
                start = (row, col)
            elif grid[row][col] == 'E':
                end = (row, col)
    
    if not start or not end:
        return []
    
    # BFS to find shortest path
    queue = deque([(start, [start])])
    visited = {start}
    
    # Directions: up, down, left, right
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    
    while queue:
        (row, col), path = queue.popleft()
        
        if (row, col) == end:
            return path_to_moves(path)
        
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            
            # Check bounds
            if (0 <= new_row < rows and 
                0 <= new_col < cols and
                (new_row, new_col) not in visited and
                grid[new_row][new_col] != 'X'):
                
                visited.add((new_row, new_col))
                new_path = path + [(new_row, new_col)]
                queue.append(((new_row, new_col), new_path))
    
    return []

def compress_grid(grid: Grid, start_pos: Tuple[int, int], end_pos: Tuple[int, int], scale_factor: int):
    """Debug function to visualize grid and path"""
    compressed_grid = []
    # zone 8*8 ; grid 64*64
    #  now print zone row 5 only
    zone_size = 8 // scale_factor
    zone_row_idx_start = 0
    zone_row_idx_end = len(grid) // zone_size - 1


    for zone_row_idx, zone_row in enumerate(grid[zone_row_idx_start*zone_size:(zone_row_idx_end+1)*zone_size:zone_size], start=zone_row_idx_start):
        row = []
        for zone_col_idx, zone_col in enumerate(zone_row[::zone_size]):
            if (zone_col_idx, zone_row_idx) == start_pos:
                row.append('S')
            elif (zone_col_idx, zone_row_idx) == end_pos:
                row.append('E')
            elif zone_col == grid.background_color:
                row.append('X')
            else:
                row.append('-')
        compressed_grid.append(row)
    
    return compressed_grid

fp = glob(r'C:\Users\smart\Desktop\GD\ARC-AGI-3-Agents\recordings\ls20-*.apiagent.*')[-1]
frame_number = None
# frame_number = 7
def load_grid_data(frame_number):
    # fp=r'C:\Users\smart\Desktop\GD\ARC-AGI-3-Engine\backend\game_data\ft09-16726c5b26ff\level_1\final.json'
    """Load grid data from jsonl"""
    with open(fp, 'r') as f:
        if fp.endswith('.json'):
            data = json.load(f)
            return data['grid']
        else:
            lines = f.readlines()
            if frame_number is None:
                frame_number = len(lines) 
            data = json.loads(lines[frame_number-1])
            return data['data']['frame'][-1]

grid_data = load_grid_data(frame_number)
grid = Grid(grid_data)
grid.background_color = FrameColor.CHARCOAL.value
objs = detect_objects(grid, ignore_color=FrameColor.DARK_GRAY)
# filter red color; lives
# green - level indicator
filter_colors = [FrameColor.RED.value, FrameColor.GREEN.value]
objs = [obj for obj in objs if obj.color not in filter_colors]
print('number of objs',len(objs))

# locksmith cap - Orange
# lock - Black
# key_chooser - 6*6
# key - 9*9
key_chooser = None
key_color_chooser = None
key_rotator = None
refill_steps_obj = None
available_steps = []
orange_objs = detect_objects(grid, required_color=FrameColor.ORANGE)
for obj in orange_objs:
    # check top row is fully
    if all(value == FrameColor.ORANGE.value for value in obj[0]):
        locksmith = obj
        locksmith_width = obj.width
        break
scale_factor = 8 // locksmith_width
refill_steps_size = 4 / scale_factor
key_chooser_size = 6 / scale_factor
key_rotator_size = 6 / scale_factor
key_color_chooser_size = 8 / scale_factor
path_directions_to_refill = []
for obj in objs:
    if obj == locksmith:
        continue
    elif FrameColor.BLACK.value in obj.colors:
        lock = obj
        expected_key = scale_to_9x9(detect_objects(Grid(lock))[0])
        expected_key.background_color = grid.background_color
        expected_key = expected_key.replace_color(FrameColor.BLACK, FrameColor(grid.background_color), replace_in_parent_grid=False)
    elif obj.height == key_chooser_size  and obj.width == key_chooser_size and FrameColor.BLUE.value in obj.colors:
        key_chooser = obj
    elif obj.height == 9 and obj.width == 9:
        key = obj
    elif obj.height == refill_steps_size and obj.width == refill_steps_size:
        refill_steps_obj = obj
        _ =find_path(grid, locksmith, refill_steps_obj, scale_factor)
        if len(_) < len(path_directions_to_refill) or not path_directions_to_refill:
            print(refill_steps_obj.region.start, 'refill_steps_obj')
            path_directions_to_refill = _
    elif obj.height == key_color_chooser_size and obj.width == key_color_chooser_size:
        key_color_chooser = obj
    elif obj.height == key_rotator_size and obj.width == key_rotator_size and FrameColor.LIGHT_GRAY.value in obj.colors:
        key_rotator = obj
    else:
        if obj.height == 1 and obj.width == 1:
            available_steps.append(obj)
        elif 0:
            plot_grid(obj)

for key_rotate_count in range(4):
    if expected_key.get_corner_colors() == key.get_corner_colors():
        break
    key = key.rotate()
logger.info(f'key rotate count: {key_rotate_count}')
print('-'*20)            
def recome(grid, locksmith, scale_factor):
    zone_size = 8 // scale_factor
    x, y = locksmith.region.start
    x, y = x//zone_size, y//zone_size
    compressed_grid = compress_grid(grid, (x, y), (x, y), scale_factor)
    if x-1 >= 0 and compressed_grid[x-1][y] == '-':
        return ['move_left', 'move_right']
    elif x+1 < len(compressed_grid) and compressed_grid[x+1][y] == '-':
        return ['move_right', 'move_left']
    elif y-1 >= 0 and compressed_grid[x][y-1] == '-':
        return ['move_up', 'move_down']
    elif y+1 < len(compressed_grid[0]) and compressed_grid[x][y+1] == '-':
        return ['move_down', 'move_up']
    return []
# plot_grids([expected_key, key], show=1)
key_color_mismatch = expected_key.colors != key.colors
if not key_color_mismatch and key_color_chooser:
    # block key color chooser
    grid[key_color_chooser.region.start.y][key_color_chooser.region.start.x] = grid.background_color
if key_rotate_count == 0 and key_rotator:
    # block key rotator
    grid[key_rotator.region.start.y][key_rotator.region.start.x] = grid.background_color
if key_color_mismatch:
    if key_color_chooser is None:
        logger.info('recome')
        path_directions = recome(grid, locksmith, scale_factor)
    else:
        path_directions = find_path(grid, locksmith, key_color_chooser, scale_factor)
elif expected_key.compare(key):
    logger.info('key is correct')
    # go to lock directly
    if key_rotate_count == 0:
        path_directions = find_path(grid, locksmith, lock, scale_factor)
    else:
        path_directions = find_path(grid, locksmith, key_rotator, scale_factor)
        key_rotate_count -= 1
        for _ in range(key_rotate_count):
            path_directions.extend(recome(grid, locksmith, scale_factor))
    if len(path_directions) > len(available_steps):
        path_directions = path_directions_to_refill
elif not path_directions_to_refill or (len(available_steps)) - 2 >= len(path_directions_to_refill):
        logger.info('key is incorrect')
        if key_chooser is None:
            # check which direction is available
            path_directions = recome(grid, locksmith, scale_factor)
        else:
            # go to key_chooser
            # 1 step = 8 cells
            # calculate how many steps to key_chooser
            path_directions = find_path(grid, locksmith, key_chooser, scale_factor)
else:
    if (len(available_steps)) - 2 < len(path_directions_to_refill):
        path_directions = path_directions_to_refill
print(f'path directions: {path_directions}')
print(f'path directions length: {len(path_directions)}')
print(f'path directions to refill length: {len(path_directions_to_refill)}')
print(f'available steps length: {len(available_steps)}')
# exit()
from pymsgbox import confirm
if confirm('Continue?') == 'OK':
    if path_directions:
        for direction in path_directions:
            execute_action(direction)
