import os
import requests
from dotenv import load_dotenv
load_dotenv()

ARC_API_KEY = os.getenv('ARC_API_KEY') 

headers = {
    'x-api-key': ARC_API_KEY,
}

def close_scorecard(card_id):
    response = requests.post(
        f'https://three.arcprize.org/api/scorecard/close',
        json={'card_id': card_id},
        headers=headers,
    )
    print(response.json())

def get_scorecard(card_id):
    response = requests.get(
        f'https://three.arcprize.org/api/scorecard/{card_id}',
        headers=headers,
    )
    print(response.json())

if __name__ == "__main__":
    card_id = '7ac1181c-d87f-45e4-a701-57483c20d53c'
    close_scorecard(card_id)
    get_scorecard(card_id)
