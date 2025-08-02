import game_handler

from game_handler import execute_action


import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('../ARC Tools')

from arc_tools.grid import Grid, detect_objects, GridRegion, GridPoint
from arc_tools.plot import plot_grids, plot_grid
from arc_tools.grid import Square
from arc_tools.logger import logger



from agents.structs import FrameColor
from game_handler import execute_action
from glob import glob
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

fp = glob(r'C:\Users\smart\Desktop\GD\ARC-AGI-3-Agents\recordings\ls20-*.apiagent.*')[-1]
print(fp)
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
# filter purple; max steps
# level indicator ; height 1
filter_colors = [FrameColor.RED.value, FrameColor.PURPLE.value]
objs = [obj for obj in objs if obj.color not in filter_colors and obj.height != 1]
print('number of objs',len(objs))

# locksmith cap - Orange
# lock - Black
# key_chooser - 6*6
# key - 9*9
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

# compare both
if expected_key.compare(key):
    print('key is correct')
    # go to lock directly
    x_steps = (lock.region.x1 - locksmith.region.x1) // 8
    y_steps = (lock.region.y1 - locksmith.region.y1) // 8
    print(f'steps to open lock: {x_steps}, {y_steps}')
else:
    print('key is incorrect')
    # go to key_chooser
    # 1 step = 8 cells
    # calculate how many steps to key_chooser
    x_steps = (key_chooser.region.x1 - locksmith.region.x1) // 8
    y_steps = (key_chooser.region.y1 - locksmith.region.y1) // 8
    print(f'steps to key_chooser: {x_steps}, {y_steps}')
from pymsgbox import confirm
if confirm('Continue?') == 'OK':
    if x_steps < 0:
        action = 'move_left'
        x_steps = -x_steps
    elif x_steps > 0:
        action = 'move_right'
    for _ in range(x_steps):
        execute_action(action)
    if y_steps < 0:
        action = 'move_up'
        y_steps = -y_steps
    elif y_steps > 0:
        action = 'move_down'
    for _ in range(y_steps):
        execute_action(action)
    # execute_action('place_object')





