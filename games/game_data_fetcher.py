import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append('../../ARC Tools')
sys.path.append('..')

os.environ['DISABLE_SHOW'] = '1'
from arc_tools.grid import Grid
from arc_tools.plot import plot_grid
from glob import glob
os.chdir(os.path.dirname(__file__))
recording_path = r'C:\Users\smart\Desktop\GD\ARC-AGI-3-Agents\recordings'
fp = glob(os.path.join(recording_path, '*.apiagent.*'))[-1]
frame_number = None
def load_grid_data(frame_number):
    """Load grid data from jsonl"""
    with open(fp, 'r') as f:
        lines = f.readlines()
        if frame_number is None:
            frame_number = len(lines) 
        data = json.loads(lines[frame_number-1])['data']
        grid = Grid(data['frame'][-1])
        grid.save(f'grid_{frame_number}.json')
        plot_grid(grid, name=f'grid_{frame_number}.png')
        with open('available_actions.json', 'w') as f:
            json.dump(data['available_actions'], f)
        with open('current_step.txt', 'w') as f:
            f.write(str(frame_number))
        return grid, data['available_actions']

grid, available_actions = load_grid_data(frame_number)
# print(available_actions)
