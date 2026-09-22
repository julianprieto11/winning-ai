from curl_cffi import requests
import json
import glob

archivos = glob.glob("datos/partidos/*.json")[:20]

total = 0
encontrados = 0

for f in archivos:
    try:
        with open(f, encoding="utf-8") as archivo:
            d = json.load(archivo)

        event_id = d["event"]["event"]["id"]

        r = requests.get(
            f"https://www.sofascore.com/api/v1/event/{event_id}/lineups",
            impersonate="chrome"
        )

        data = r.json()
        total += 1

        home_missing = data.get("home", {}).get("missingPlayers")
        away_missing = data.get("away", {}).get("missingPlayers")

        if home_missing or away_missing:
            encontrados += 1
            print(f"{event_id} -> missingPlayers ENCONTRADO")
            print("HOME:", home_missing)
            print("AWAY:", away_missing)

    except Exception as e:
        print("ERROR:", f, e)

print()
print("TOTAL CONSULTADOS:", total)
print("CON missingPlayers:", encontrados)
