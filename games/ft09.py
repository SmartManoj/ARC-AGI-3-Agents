import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('../ARC Tools')

from agents.structs import FrameColor
from game_handler import execute_action
from glob import glob

fp = glob(r'C:\Users\smart\Desktop\GD\ARC-AGI-3-Agents\recordings\ft09*')[-1]
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

from arc_tools.grid import Grid, detect_objects, GridRegion, GridPoint
from arc_tools.plot import plot_grids, plot_grid
from arc_tools.grid import Square

grid = Grid(grid_data)
print(grid.width, grid.height)
# grid = grid.crop(GridRegion([GridPoint(1, 1), GridPoint(grid.width-2, grid.height-2)]))
# crop corner
objs = detect_objects(grid,ignore_corners=1, required_object=Square(),ignore_color=FrameColor(4))
print(f'Number of objects: {len(objs)}')
obj_point_map = {(obj.points[0]): obj for obj in objs}
key_objs = [obj for obj in objs if not obj.color]
gap = objs[1].region.x1 - objs[0].region.x2 - 1
print(gap, 'gap')
# plot_grids([grid,*objs], show=1)
final_answers = []
for key_obj in key_objs:
    sub_cells = key_obj.shrink().flatten_list()
    print(sub_cells)
    # plot_grids([grid,key_obj], show=1)
    # plot_grids([grid,obj], show=1)
    point1_x = key_obj.region.x1 - gap - key_obj.width
    point1_y = key_obj.region.y1 - gap - key_obj.height
    surrounding_objs = []
    # generate 3*3 regions with gap
    for row in range(3):
        for col in range(3):
            point_x = point1_x + col * (key_obj.width + gap)
            point_y = point1_y + row * (key_obj.height + gap)
            surrounding_objs.append(obj_point_map[(point_x, point_y)])
    centre_color = FrameColor(sub_cells[4])
    for sub_cell_id, sub_cell_color in enumerate(sub_cells, start=1):
        if sub_cell_id == 5:
            continue
        sub_cell_color = FrameColor(sub_cell_color)
        obj = surrounding_objs[sub_cell_id-1]
        obj_idx = objs.index(obj) + 1
        obj_color = FrameColor(obj.color)
        is_white_key = sub_cell_color is FrameColor.WHITE
        correct_obj = obj_color is centre_color
        if (is_white_key and not correct_obj) or (not is_white_key and correct_obj):
            print(sub_cell_id, obj_idx, obj.region)
            if obj_idx not in final_answers:
                final_answers.append(obj_idx)
print(final_answers)
from pymsgbox import confirm
if not confirm('Continue?') == 'OK':
    exit()
else:
    for obj_idx in final_answers:
        obj = objs[obj_idx-1]
        x1, y1 = obj.region.x1, obj.region.y1
        x2, y2 = obj.region.x2, obj.region.y2
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        res = execute_action('ACTION6', x=center_x, y=center_y)
        print(res['success'])

# plot_grid(objs[5], show=1)
# plot_grids(objs[:], show=1)
