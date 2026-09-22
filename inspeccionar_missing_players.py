from curl_cffi import requests
import json
import glob

archivos = glob.glob("datos/partidos/*.json")

for f in archivos:
    try:
        with open(f, encoding="utf-8") as archivo:
            d = json.load(archivo)

        event_id = d["event"]["event"]["id"]

        data = requests.get(
            f"https://www.sofascore.com/api/v1/event/{event_id}/lineups",
            impersonate="chrome"
        ).json()

        home_missing = data.get("home", {}).get("missingPlayers")
        away_missing = data.get("away", {}).get("missingPlayers")

        if home_missing or away_missing:
            print("EVENTO:", event_id)
            print("HOME:")
            print(json.dumps(home_missing, indent=2, ensure_ascii=False))
            print("AWAY:")
            print(json.dumps(away_missing, indent=2, ensure_ascii=False))
            break

    except Exception as e:
        continue
