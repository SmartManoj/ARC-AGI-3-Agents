import json
import matplotlib.pyplot as plt
import numpy as np

def load_grid_data():
    """Load grid data from grid.json"""
    with open('grid.json', 'r') as f:
        return json.load(f)

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
    """Plot the grid data with proper colors"""
    # Convert to numpy array
    grid = np.array(grid_data)
    
    # Create color map
    color_map = create_color_map()
    
    # Set dark mode style
    plt.style.use('dark_background')
    
    # Create figure
    fig, ax = plt.subplots(figsize=(16, 12))
    
    # Create custom colormap
    unique_values = np.unique(grid)
    colors = [color_map.get(val, '#888888') for val in unique_values]
    
    # Plot the grid
    im = ax.imshow(grid, cmap='tab20', interpolation='nearest')
    
    # Set custom colors
    for i, val in enumerate(unique_values):
        mask = grid == val
        if val in color_map:
            ax.imshow(np.ma.masked_where(~mask, grid), 
                     cmap=plt.cm.colors.ListedColormap([color_map[val]]), 
                     alpha=1, interpolation='nearest')
    
    # Add grid lines
    ax.set_xticks(np.arange(-0.5, grid.shape[1], 1), minor=True)
    ax.set_yticks(np.arange(-0.5, grid.shape[0], 1), minor=True)
    ax.grid(which="minor", color="#4b4b4b", linestyle='-', linewidth=0.1)
    
    # Remove ticks
    ax.set_xticks([])
    ax.set_yticks([])
    
    # Add legend
    legend_elements = []
    for val, color in color_map.items():
        if val in unique_values:
            legend_elements.append(plt.Rectangle((0,0),1,1, facecolor=color, 
                                               label=f'Value {val}'))
    
    ax.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), 
              loc='upper left', title='Grid Values')
    
    plt.title('Grid Visualization', fontsize=16, pad=20, color='white')
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
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

if __name__ == "__main__":
    main() 