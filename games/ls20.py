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

def scale_2to3(grid):
    """Scale 6x6 grid to 9x9 by factor 2/3"""
    if len(grid) != 6 or len(grid[0]) != 6:
        raise ValueError("Input grid must be 6x6")
    
    result = [[0 for _ in range(9)] for _ in range(9)]
    
    for i in range(9):
        for j in range(9):
            # Map 9x9 position to 6x6 position
            src_i = int(i * 2/3)
            src_j = int(j * 2/3)
            
            # Take the value from the source position
            result[i][j] = grid[src_i][src_j]
    
    return Grid(result)

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

def find_path(grid: Grid, start_obj: SubGrid , end_obj: SubGrid) -> Optional[List[Tuple[int, int]]]:
    """
    Find path from S to E in the grid using BFS.
    Returns list of coordinates (row, col) representing the path.
    """
    start_pos = start_obj.region.x1 / 8, start_obj.region.y1 / 8
    end_pos = end_obj.region.x1 // 8 * 8 / 8, end_obj.region.y1 // 8 * 8 / 8
    grid = compress_grid(grid, start_pos, end_pos)
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
        return None
    
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
    
    return None

def compress_grid(grid: Grid, start_pos: Tuple[int, int], end_pos: Tuple[int, int]):
    """Debug function to visualize grid and path"""
    compressed_grid = []
    # zone 8*8 ; grid 64*64
    #  now print zone row 5 only
    zone_row_idx_start = 0
    zone_row_idx_end = 7

    for zone_row_idx, zone_row in enumerate(grid[zone_row_idx_start*8:(zone_row_idx_end+1)*8:8], start=zone_row_idx_start):
        row = []
        for zone_col_idx, zone_col in enumerate(zone_row[::8]):
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
refill_steps_obj = None
available_steps = []
for obj in objs:
    if FrameColor.ORANGE.value in obj.colors:
        locksmith = obj
    elif FrameColor.BLACK.value in obj.colors:
        lock = obj
        expected_key = scale_2to3(detect_objects(Grid(lock))[0])
        expected_key = expected_key.replace_color(FrameColor.BLACK, FrameColor(grid.background_color))

    elif obj.height == 6 and obj.width == 6:
        key_chooser = obj
    elif obj.height == 9 and obj.width == 9:
        key = obj
    elif obj.height == 4 and obj.width == 4:
        refill_steps_obj = obj
    else:
        available_steps.append(obj)
path_directions_to_refill=find_path(grid, locksmith, refill_steps_obj) if refill_steps_obj else None
if expected_key.compare(key):
    print('key is correct')
    # go to lock directly
    path_directions = find_path(grid, locksmith, lock)
    if len(path_directions) > len(available_steps):
        path_directions = path_directions_to_refill
elif (len(available_steps)) != len(path_directions_to_refill):
        print('key is incorrect')
        if key_chooser is None:
            # undo last action & redo,
            # now do up and down
            path_directions = ['move_up', 'move_down']
        else:
            # go to key_chooser
            # 1 step = 8 cells
            # calculate how many steps to key_chooser
            path_directions = find_path(grid, locksmith, key_chooser)

print(f'path directions: {path_directions}')
print(f'path directions length: {len(path_directions)}')
print(f'available steps length: {len(available_steps)}')
from pymsgbox import confirm
if confirm('Continue?') == 'OK':
    if path_directions:
        for direction in path_directions:
            execute_action(direction)
        
    # execute_action('place_object')





