import requests
import json

API_KEY = "pk_test_v-4YtMJL4MXC2Ydz6DhG2PgIKGNlVYF_v--vjjnZqig"

match_id = "m_0MqdAY"

headers = {
    "X-API-KEY": API_KEY
}

endpoints = {
    "players": f"https://api.pitchapi.dev/v1/matches/{match_id}/players",
    "advanced_players": f"https://api.pitchapi.dev/v1/matches/{match_id}/advanced/players",
}

for nombre, url in endpoints.items():

    print("=" * 70)
    print(nombre.upper())
    print("=" * 70)

    response = requests.get(url, headers=headers)

    print("STATUS:", response.status_code)

    if response.status_code == 200:
        data = response.json()

        archivo = f"pitchapi_{nombre}.json"

        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print("GUARDADO:", archivo)

        if nombre == "players":
            jugadores = data.get("data", [])
            print("JUGADORES:", len(jugadores))

        elif nombre == "advanced_players":
            jugadores = data.get("data", {}).get("players", [])
            print("JUGADORES:", len(jugadores))

    else:
        print(response.text)

    print()