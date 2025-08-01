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
indicator_objs = []
floating_objs = []
gates = []
for obj in objs:
    if obj.color not in [FrameColor.BLUE.value, FrameColor.RED.value]:
        if obj.height == 4 and obj.width == 4:
            indicator_objs.append(obj)
        elif obj.height == 16 and obj.width == 4 and obj.color == FrameColor.LIGHT_GRAY.value:
            gates.append(obj)
        elif obj.height == 8 and obj.width == 8:
            floating_objs.append(obj)


water_bodies = [obj for obj in objs if obj.color == FrameColor.WHITE.value and obj.width !=1]
# plot_grids(objs)
for red_handle in red_handles:
    print('red handle', red_handle.region.x1, red_handle.region.y1)
for blue_handle in blue_handles:
    print('blue handle', blue_handle.region.x1, blue_handle.region.y1)
for indicator_obj in indicator_objs:
    print('indicator obj', indicator_obj.region.x1, indicator_obj.region.y1)
for floating_obj in floating_objs:
    print('floating obj', floating_obj.region.x1, floating_obj.region.y1)
for gate in gates:
    print('gate', gate.region.x1, gate.region.y1)

# arrange water bodies from left to right
water_bodies.sort(key=lambda x: x.region.x1)
for wb_idx,wb in enumerate(water_bodies):
    print('wb', wb.region.x1, wb.region.y1)
for wb_idx,wb in enumerate(water_bodies):
    # find target water body
    if wb.region.x1 < floating_objs[0].region.x1 < wb.region.x2:
        target_water_body = wb
        target_water_body_idx = wb_idx
        print('target_water_body_idx', target_water_body_idx)
        break
if 0:
    # same_level
    times = (water_bodies[1].region.y1 - water_bodies[0].region.y1) // (4*2) 
# plot_grids(indicator_objs)
for indicator_obj in indicator_objs:
    times = (indicator_obj.region.y1 - target_water_body.region.y1 )//4
print(times)
if times > 0 and target_water_body_idx != 1:
    # blue handle increases in L5
    if target_water_body_idx in [1,2]:
        handle = blue_handles[-1]
else:
    if target_water_body_idx in [1,2]:
        handle = red_handles[-1]
x, y = handle.region.x1, handle.region.y1
print('x, y', x, y)
from pymsgbox import confirm
if confirm('Continue?') == 'OK':
    for _ in range(abs(times)):
        execute_action('ACTION6', x=x, y=y)






