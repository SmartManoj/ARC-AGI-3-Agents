import game_handler
from pymsgbox import alert
from game_handler import execute_action


import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('../ARC Tools')

from arc_tools.grid import Grid, detect_objects, GridRegion, GridPoint, SubGrid
from arc_tools.plot import plot_grids, plot_grid
from arc_tools.grid import Square
from arc_tools.helper import scale_to_9x9, compress_grid, find_path
from arc_tools.logger import logger
from typing import List, Tuple, Optional


from agents.structs import FrameColor
from game_handler import execute_action
from glob import glob
from collections import deque
game_handler.PORT = 8002

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
expected_keys = []
key_color_choosers = []
for obj in objs:
    if obj == locksmith:
        continue
    elif FrameColor.BLACK.value in obj.colors:
        lock = obj
        expected_key = scale_to_9x9(detect_objects(Grid(lock))[0])
        expected_key.background_color = grid.background_color
        expected_key = expected_key.replace_color(FrameColor.BLACK, FrameColor(grid.background_color), replace_in_parent_grid=False)
        expected_keys.append(expected_key)
    elif obj.height == key_chooser_size  and obj.width == key_chooser_size and FrameColor.BLUE.value in obj.colors:
        key_chooser = obj
    elif obj.height == 9 and obj.width == 9:
        key = obj
    elif obj.height == refill_steps_size and obj.width == refill_steps_size:
        refill_steps_obj = obj
        _ = find_path(grid, locksmith, refill_steps_obj, scale_factor)
        if len(_) < len(path_directions_to_refill) or not path_directions_to_refill:
            # logger.info(refill_steps_obj.region.start, 'refill_steps_obj')
            path_directions_to_refill = _
            best_refill_steps_obj = obj
    elif obj.height == key_color_chooser_size and obj.width == key_color_chooser_size and obj[0][0] == FrameColor.WHITE.value:
        key_color_chooser = obj
        key_color_choosers.append(obj)
    elif obj.height == key_rotator_size and obj.width == key_rotator_size and FrameColor.LIGHT_GRAY.value in obj.colors:
        key_rotator = obj
    else:
        if obj.height == 1 and obj.width == 1:
            available_steps.append(obj)
        elif 0:
            plot_grid(obj)
key_rotate_counts = []
for i in range(len(expected_keys)):
    for key_rotate_count in range(4):
        if expected_keys[i].get_corner_colors().index(FrameColor.BLUE.value) == key.get_corner_colors().index(FrameColor.BLUE.value):
            break
        expected_keys[i] = expected_keys[i].rotate()
    key_rotate_count = (4-key_rotate_count)%4
    key_rotate_counts.append(key_rotate_count)
logger.info(f'key rotate counts: {key_rotate_counts}')
logger.info('-'*20)            
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
key_color_mismatch = expected_keys[-1].colors != key.colors and 1

is_correct_key = any(expected_key.is_similar(key, ignore_color=1) for expected_key in expected_keys)
# plot_grids([*expected_keys, key], show=1)
if is_correct_key and key_chooser:
    # block key chooser
    grid[key_chooser.region.start.y][key_chooser.region.start.x] = grid.background_color
if not key_color_mismatch and key_color_chooser:
    # block key color chooser
    grid[key_color_chooser.region.start.y][key_color_chooser.region.start.x] = grid.background_color
if key_rotate_count == 0 and key_rotator:
    # block key rotator
    grid[key_rotator.region.start.y][key_rotator.region.start.x] = grid.background_color

# find again after removing obstacles
path_directions_to_refill = find_path(grid, locksmith, best_refill_steps_obj, scale_factor)

if key_color_mismatch:
    if key_color_chooser is None:
        logger.info('recome')
        path_directions = recome(grid, locksmith, scale_factor)
    else:
        logger.info('key color chooser')
        path_directions = find_path(grid, locksmith, key_color_choosers[0], scale_factor)
        # TODO: auto recome
elif is_correct_key:
    logger.info('key is correct')
    # go to lock directly
    if key_rotate_count == 0:
        logger.info('lock')
        path_directions = find_path(grid, locksmith, lock, scale_factor)
    else:
        logger.info('key rotator')
        path_directions = find_path(grid, locksmith, key_rotator, scale_factor)
        logger.info(key_rotate_count)
        key_rotate_count -= 1
        for _ in range(key_rotate_count):
            path_directions.extend(recome(grid, locksmith, scale_factor))
    
elif not path_directions_to_refill or (len(available_steps)) - 2 >= len(path_directions_to_refill):
        logger.info('key is incorrect')
        if key_chooser is None:
            logger.info('recome')
            path_directions = recome(grid, locksmith, scale_factor)
        else:
            logger.info('key chooser')
            path_directions = find_path(grid, locksmith, key_chooser, scale_factor)
else:
    if (len(available_steps)) - 2 < len(path_directions_to_refill):
        logger.info('path directions to refill')
        path_directions = path_directions_to_refill
    else:
        logger.info('no way')
if len(path_directions) > len(available_steps):
    logger.info(f'path directions to refill for {len(path_directions)} steps')
    path_directions = path_directions_to_refill        
logger.info('-'*20)
logger.info(f'path directions: {path_directions}')
logger.info(f'path directions length: {len(path_directions)}')
logger.info(f'path directions to refill length: {len(path_directions_to_refill)}')
logger.info(f'available steps length: {len(available_steps)}')
# exit()
from pymsgbox import confirm
if confirm('Continue?') == 'OK':
    if path_directions:
        for direction in path_directions:
            execute_action(direction)
