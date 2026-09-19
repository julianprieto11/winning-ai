import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("SPORTMONKS_API_TOKEN")

BASE_URL = "https://api.sportmonks.com/v3/football"


def api_get(endpoint, params=None):
    if not API_TOKEN:
        raise RuntimeError(
            "No se encontró SPORTMONKS_API_TOKEN en el archivo .env"
        )

    url = f"{BASE_URL}{endpoint}"

    headers = {
        "Authorization": API_TOKEN,
        "Accept": "application/json",
    }

    response = requests.get(
        url,
        headers=headers,
        params=params or {},
        timeout=30,
    )

    if response.status_code != 200:
        print(f"ERROR HTTP: {response.status_code}")
        print(response.text)
        response.raise_for_status()

    return response.json()