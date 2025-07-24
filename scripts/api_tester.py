import os
import requests
from dotenv import load_dotenv
load_dotenv()

ARC_API_KEY = os.getenv('ARC_API_KEY') 

s = requests.Session()

headers = {
    'x-api-key': ARC_API_KEY,
    'Accept': 'application/json',
}

def open_scorecard():
    response = s.post(
        f'https://three.arcprize.org/api/scorecard/open',
        headers=headers,
        json={}
    )
    print(response.json())
    return response.json()['card_id']

def close_scorecard(card_id):
    response = s.post(
        f'https://three.arcprize.org/api/scorecard/close',
        json={'card_id': card_id},
        headers=headers,
    )
    print(response.json())

def get_scorecard(card_id):
    response = s.get(
        f'https://three.arcprize.org/api/scorecard/{card_id}',
        headers=headers,
    )
    print(response.json())

def do_reset_action(card_id):
    data = {
        "game_id": "ft09-16726c5b26ff",
        "guid": None,
        "card_id": card_id,
    }
    response = requests.post(
        f'https://three.arcprize.org/api/cmd/RESET',
        headers=headers,
        json=data
    )
    guid = (response.json())['guid']
    print(response.ok)
    return guid


if __name__ == "__main__":
    card_id = '361d01b9-ac37-495c-b361-bd4a58713d82'
    print('Opening scorecard')
    card_id = open_scorecard()
    print('Resetting game')
    do_reset_action(card_id)
    print('Getting scorecard')
    get_scorecard(card_id)
    print('Closing scorecard')
    close_scorecard(card_id)
    print('Opening URL')
    # open URL
    import webbrowser
    scorecard_url = f'https://three.arcprize.org/scorecards/{card_id}'
    print(scorecard_url)
    webbrowser.open(scorecard_url)
