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
game_handler.PORT = 8000

fp = glob(r'C:\Users\smart\Desktop\GD\ARC-AGI-3-Agents\recordings\vc33-*.apiagent.*')[-1]
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
grid.background_color = FrameColor.GRAY.value
objs = detect_objects(grid,  single_color_only=0)
main_obj = [obj for obj in objs if obj.height != 1][0]
objs = detect_objects((main_obj), single_color_only=1)
print('number of objs',len(objs))
red_handles = [obj for obj in objs if obj.color == FrameColor.RED.value]
blue_handles = [obj for obj in objs if obj.color == FrameColor.BLUE.value]
for obj in objs:
    if obj.color not in [FrameColor.BLUE.value, FrameColor.RED.value]:
        if obj.height == 4 and obj.width == 4:
            indicator_obj = obj
        if obj.height == 8 and obj.width == 8:
            floating_obj = obj

water_bodies = [obj for obj in objs if obj.color == FrameColor.WHITE.value]
# plot_grids(objs)
for red_handle in red_handles:
    print('red handle', red_handle.region.x1, red_handle.region.y1)
for blue_handle in blue_handles:
    print('blue handle', blue_handle.region.x1, blue_handle.region.y1)
print('indicator obj', indicator_obj.region.x1, indicator_obj.region.y1)
print('floating obj', floating_obj.region.x1, floating_obj.region.y1)
for wb_idx,wb in enumerate(water_bodies):
    # find target water body
    if wb.region.x1 < floating_obj.region.x1 < wb.region.x2:
        target_water_body = wb
        target_water_body_idx = wb_idx
        break

times = (indicator_obj.region.y1 - target_water_body.region.y1 )//4
print(times)
if times > 0:
    handle = blue_handles[target_water_body_idx-1]
else:
    handle = red_handles[target_water_body_idx-1]
from pymsgbox import confirm
if confirm('Continue?') == 'OK':
    for _ in range(abs(times)):
        x, y = handle.region.x1, handle.region.y1
        execute_action('ACTION6', x=x, y=y)






