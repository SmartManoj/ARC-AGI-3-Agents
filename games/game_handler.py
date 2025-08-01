import requests

PORT= 8000

def execute_action(action: str, x: int = None, y: int = None) -> dict:
    print(f"{PORT} | Executing action: {action}, x: {x}, y: {y}")
    url = f"http://localhost:{PORT}/execute_action"
    response = requests.get(url, params={
        "action": action,
        "x": x,
        "y": y,
        })
    return response.json()

if __name__ == '__main__':
    coordinates = []
    for x, y in coordinates:
        execute_action('ACTION6', x=x, y=y)