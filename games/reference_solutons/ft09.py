import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from arc_tools.grid import Grid, detect_objects, GridRegion, GridPoint
from arc_tools.plot import plot_grids, plot_grid
from arc_tools.grid import Square
from arc_tools.logger import logger



from agents.structs import FrameColor

from glob import glob
fp = glob(r'../recordings/ft09-*.restagent.*')[-1]
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
print(grid.width, grid.height)
grid.background_color = FrameColor.CHARCOAL.value
centre_frame = detect_objects(grid,ignore_corners=1)[0]
plot_grid(Grid(centre_frame), show=1)
objs = detect_objects(Grid(centre_frame),ignore_corners=1, ignore_color=FrameColor.CHARCOAL)
square_objs = []
color_map = []
for obj in objs:
    if obj.width == obj.height:
        square_objs.append(obj)
    else:
        color_map = [FrameColor(color) for color in obj.shrink().flatten_list()]
objs = square_objs
# plot_grids(objs[:5], show=1)
# plot_grids(objs[5:10], show=1)
logger.info(f'Number of objects: {len(objs)}')
obj_point_map = {(obj.points[0]): obj for obj in objs}
key_objs = [obj for obj in objs if not obj.color]
gap = objs[1].region.x1 - objs[0].region.x2 - 1
print(gap, 'gap')
key_objs_color = [FrameColor(obj.shrink().flatten_list()[4]) for obj in key_objs]
print('Color map', color_map)
print('key_objs_color', key_objs_color)
if len(color_map) == 3:
    odd_color = FrameColor((set(color_map) - set(key_objs_color)).pop())
else:
    odd_color = None

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
            obj = obj_point_map.get((point_x, point_y))
            surrounding_objs.append(obj)
    centre_color = FrameColor(sub_cells[4])
    for sub_cell_id, sub_cell_color in enumerate(sub_cells, start=1):
        if sub_cell_id == 5:
            continue
        sub_cell_color = FrameColor(sub_cell_color)
        obj = surrounding_objs[sub_cell_id-1]
        if not obj: continue
        obj_idx = objs.index(obj) + 1
        logger.info(f'{sub_cell_id = }, {sub_cell_color = }, {obj_idx = }')
        if obj.color is None:
            # another key
            continue
        obj_color = FrameColor(obj.color)
        is_white_key = sub_cell_color is FrameColor.WHITE
        if len(color_map) == 2 or not color_map:
            correct_obj = obj_color is centre_color
            if (is_white_key and not correct_obj) or (not is_white_key and correct_obj):
                print(sub_cell_id, obj_idx, obj.region)
                if obj_idx not in final_answers:
                    final_answers.append(obj_idx)
        else:
            times = 0
            is_centre_color = obj_color is centre_color
            is_odd_color = obj_color is odd_color
            print(sub_cell_id, obj_idx, obj_color, centre_color, odd_color)
            print(f'{is_white_key = }, {is_centre_color = }, {is_odd_color = }')
            if is_white_key and not is_centre_color:
                times = color_map.index(centre_color) - color_map.index(obj_color)
                print('times A', times)
            elif not is_white_key and not is_odd_color:
                times = color_map.index(odd_color) - color_map.index(obj_color)
                print(color_map.index(odd_color) , color_map.index(obj_color))
                print('times B', times)

            if obj_idx not in final_answers:
                print('Adding', obj_idx, times)
                final_answers.extend([obj_idx]*times)
            else:
                print('Already in', obj_idx)

print('final_answers', final_answers)
# final_answers = [2, 8,14]
from pymsgbox import confirm
if confirm('Continue?') == 'OK':
    coordinates = []
    for obj_idx in final_answers:
        obj = objs[obj_idx-1]
        x1, y1 = obj.region.x1, obj.region.y1
        x2, y2 = obj.region.x2, obj.region.y2
        center_x = (x1 + x2) // 2 + centre_frame.region.x1
        center_y = (y1 + y2) // 2 + centre_frame.region.y1
        print(f"execute_action('ACTION6', x={center_x}, y={center_y})")
        coordinates.append((center_x, center_y))
    print('coordinates', coordinates)

# plot_grid(objs[5], show=1)
# plot_grids(objs[:], show=1)
