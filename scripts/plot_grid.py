import json
import matplotlib.pyplot as plt
import numpy as np
fp = r'recordings\ft09-a14010482fbd.reasoningagent.gemini-2.5-pro.with-observe.high.20250726083833..recording.jsonl'
frame_number = 5
def load_grid_data():
    # fp=r'C:\Users\smart\Desktop\GD\ARC-AGI-3-Engine\backend\game_data\ft09-16726c5b26ff\level_1\final.json'
    """Load grid data from jsonl"""
    with open(fp, 'r') as f:
        if fp.endswith('.json'):
            data = json.load(f)
            return data['grid']
        else:
            data = json.loads(f.readlines()[(frame_number-1)*2])
            return data['data']['frame'][-1]

from enum import Enum
class MyEnum(Enum):
    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"
    
class FrameColor(MyEnum):
    WHITE = 0
    LIGHT_GRAY = 1
    GRAY = 2
    DARK_GRAY = 3
    CHARCOAL = 4
    BLACK = 5
    MAGENTA = 6
    PINK = 7
    RED = 8
    BLUE = 9
    SKY_BLUE = 10
    YELLOW = 11
    ORANGE = 12
    MAROON = 13
    GREEN = 14
    PURPLE = 15

def create_color_map():
    """Create color mapping for grid values"""
    return {
        0: "#FFFFFF",
        1: "#CCCCCC",
        2: "#999999",
        3: "#666666",
        4: "#333333",
        5: "#000000",
        6: "#E53AA3",
        7: "#FF7BCC",
        8: "#F93C31",
        9: "#1E93FF",
        10: "#88D8F1",
        11: "#FFDC00",
        12: "#FF851B",
        13: "#921231",
        14: "#4FCC30",
        15: "#A356D6"
    }

def plot_grid(grid_data, save_path='grid_visualization.png'):
    """Plot the grid data with proper colors and detect objects"""
    # Convert to numpy array
    grid = np.array(grid_data)
    
    # Import and use detect_objects
    import sys
    sys.path.append('../ARC Tools')
    from arc_tools.grid import Grid, detect_objects, Color
    
    # Create Grid object and detect objects
    grid_obj = Grid(grid_data)
    
    # Look for 12x12 square objects specifically
    from arc_tools.grid import Square
    square_12 = Square(12)
    detected_objects = detect_objects(grid_obj, required_object=square_12, ignore_corners=True)
    
    # If we don't find exactly 9 objects, try a more general approach
    if len(detected_objects) != 9:
        # Look for objects of size around 12x12
        detected_objects = detect_objects(grid_obj, ignore_corners=True, max_count=20)
        filtered_objects = []
        for obj in detected_objects:
            # Look for objects that are approximately 12x12 (the main grid boxes)
            if (10 <= obj.width <= 14 and 10 <= obj.height <= 14 and 
                obj.width < grid.shape[1] * 0.3 and obj.height < grid.shape[0] * 0.3):
                filtered_objects.append(obj)
        detected_objects = filtered_objects[:9]  # Take only the first 9
    
    print(f"Detected {len(detected_objects)} objects:")
    for i, obj in enumerate(detected_objects):
        print(f"  Object {i+1}: Region {obj.region}, Color: {obj.color}, Size: {obj.width}x{obj.height}")
    
    # Create color map
    color_map = create_color_map()
    
    # Set dark mode style
    plt.style.use('dark_background')
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    fig.patch.set_facecolor('black')  # Set figure background to black
    
    def format_coord(x, y):
        if x >= -0.5 and y >= -0.5:
            col = int(x + 0.5)
            row = int(y + 0.5)
            value = grid[row, col]
            return f'(row,col) = ({row},{col})\t(x,y) = ({col},{row})\t\t\n[{value}]  | {FrameColor(value).name}\t\t|'
        return ''

    ax1.format_coord = format_coord
    ax2.format_coord = format_coord
    # Plot 1: Original grid
    unique_values = np.unique(grid)
    
    # Plot the original grid
    im1 = ax1.imshow(grid, cmap='tab20', interpolation='nearest')
    ax1.set_facecolor('black')  # Set axes background to black
    
    # Set custom colors for original grid
    for i, val in enumerate(unique_values):
        mask = grid == val
        if val in color_map:
            ax1.imshow(np.ma.masked_where(~mask, grid), 
                      cmap=plt.cm.colors.ListedColormap([color_map[val]]), 
                      alpha=1, interpolation='nearest')
    
    # Add grid lines for original
    ax1.set_xticks(np.arange(-0.5, grid.shape[1], 1), minor=True)
    ax1.set_yticks(np.arange(-0.5, grid.shape[0], 1), minor=True)
    ax1.grid(which="minor", color="#4b4b4b", linestyle='-', linewidth=0.1)
    ax1.set_xticks([])
    ax1.set_yticks([])
    ax1.set_title('Original Grid', fontsize=16, pad=20, color='white')
    
    # Plot 2: Objects highlighted
    ax2.imshow(grid, cmap='tab20', interpolation='nearest')
    ax2.set_facecolor('black')  # Set axes background to black
    
    # Set custom colors for detected objects panel (same as original)
    for i, val in enumerate(unique_values):
        mask = grid == val
        if val in color_map:
            ax2.imshow(np.ma.masked_where(~mask, grid), 
                      cmap=plt.cm.colors.ListedColormap([color_map[val]]), 
                      alpha=1, interpolation='nearest')

    # Draw black boxes around detected objects and add labels
    for i, obj in enumerate(detected_objects):
        # Get object boundaries from GridRegion
        x1, y1 = obj.region.x1, obj.region.y1
        x2, y2 = obj.region.x2, obj.region.y2
        
        # Draw black rectangle around object
        rect = plt.Rectangle((x1, y1), x2-x1, y2-y1, 
                           linewidth=2, edgecolor='black', facecolor='none')
        ax2.add_patch(rect)
        
        # Add label at center of object
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        ax2.text(center_x, center_y, str(i+1), 
                ha='center', va='center', fontsize=12, 
                color='black', weight='bold',
                bbox=dict(boxstyle="circle,pad=0.3", facecolor='white', alpha=0.8))

    # Add grid lines for objects
    ax2.set_xticks(np.arange(-0.5, grid.shape[1], 1), minor=True)
    ax2.set_yticks(np.arange(-0.5, grid.shape[0], 1), minor=True)
    ax2.grid(which="minor", color="#4b4b4b", linestyle='-', linewidth=0.1)
    ax2.set_xticks([])
    ax2.set_yticks([])
    ax2.set_title('Detected Objects', fontsize=16, pad=20, color='white')
    
    # Add legend for original grid values
    legend_elements = []
    for val, color in color_map.items():
        if val in unique_values:
            legend_elements.append(plt.Rectangle((0,0),1,1, facecolor=color, 
                                               label=f'Value {val}'))
    
    # Add legend for objects
    for i, obj in enumerate(detected_objects):
        # Use a neutral color for object rectangles in legend
        legend_elements.append(plt.Rectangle((0,0),1,1, facecolor='gray', 
                                           label=f'Object {i+1} ({obj.width}x{obj.height})'))
    
    fig.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), 
              loc='upper left', title='Grid Values & Objects')
    
    plt.tight_layout()
    
    # Save the plot
    # plt.savefig(save_path,  bbox_inches='tight')
    print(f"Grid visualization saved to {save_path}")
    
    # Show the plot
    plt.show()

def main():
    """Main function to load and plot grid data"""
    try:
        grid_data = load_grid_data()
        print(f"Loaded grid with shape: {len(grid_data)}x{len(grid_data[0])}")
        plot_grid(grid_data)
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main() 