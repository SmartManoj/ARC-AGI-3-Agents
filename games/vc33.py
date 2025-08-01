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
red_handle = [obj for obj in objs if obj.color == FrameColor.RED.value][0]
blue_handle = [obj for obj in objs if obj.color == FrameColor.BLUE.value][0]
for obj in objs:
    if obj.color not in [FrameColor.BLUE.value, FrameColor.RED.value] and obj.height == 4 and obj.width == 4:
        indicator_obj = obj
        break

water_bodies = [obj for obj in objs if obj.color == FrameColor.WHITE.value]
objs = [red_handle, blue_handle, indicator_obj, *water_bodies, main_obj]
# plot_grids(objs)
print('red handle', red_handle.region.x1, red_handle.region.y1)
print('blue handle', blue_handle.region.x1, blue_handle.region.y1)
print('indicator obj', indicator_obj.region.x1, indicator_obj.region.y1)
for wb in water_bodies:
    print(wb.region.x1, wb.region.x2, wb.region.y1, wb.region.y2)
    if wb.region.x2 == blue_handle.region.x2:
        blue_water_body = wb
    elif wb.region.x1 == red_handle.region.x1:
        red_water_body = wb
print(red_water_body.region.y1, indicator_obj.region.y1)
times = (indicator_obj.region.y1 - red_water_body.region.y1 )//4
print(times)
if times > 0:
    handle = blue_handle
else:
    handle = red_handle
for _ in range(abs(times)):
    x, y = handle.region.x1, handle.region.y1
    execute_action('ACTION6', x=x, y=y)






