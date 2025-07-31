import requests

def execute_action(action: str, x: int = None, y: int = None, object_number: int = None) -> dict:
    print(f"Executing action: {action}, x: {x}, y: {y}, object_number: {object_number}")
    url = "http://localhost:8000/execute_action"
    response = requests.get(url, params={
        "action": action,
        "x": x,
        "y": y,
        "object_number": object_number})
    return response.json()

if __name__ == '__main__':
    coordinates = []
    for x, y in coordinates:
        execute_action('ACTION6', x=x, y=y)