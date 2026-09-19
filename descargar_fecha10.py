from curl_cffi import requests
import json
import time
import os

with open("datos/fecha10_proxima.json", encoding="utf-8") as f:
    partidos = json.load(f)

os.makedirs("datos/partidos", exist_ok=True)

base = "https://www.sofascore.com/api/v1/event/"

print("DESCARGANDO", len(partidos), "PARTIDOS")
print()

for i, partido in enumerate(partidos, 1):

    event_id = partido["id"]
    local = partido["homeTeam"]["name"]
    visitante = partido["awayTeam"]["name"]

    print(
        f"{i}/15 | {event_id} | {local} - {visitante}"
    )

    datos = {
        "event": {
            "event": partido
        },
        "lineups": requests.get(
            base + str(event_id) + "/lineups",
            impersonate="chrome"
        ).json(),
        "incidents": requests.get(
            base + str(event_id) + "/incidents",
            impersonate="chrome"
        ).json(),
        "statistics": requests.get(
            base + str(event_id) + "/statistics",
            impersonate="chrome"
        ).json()
    }

    archivo = f"datos/partidos/{event_id}.json"

    with open(
        archivo,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            datos,
            f,
            ensure_ascii=False,
            indent=2
        )

    time.sleep(0.5)

print()
print("LISTO")