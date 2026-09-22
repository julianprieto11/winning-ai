from curl_cffi import requests
import json
import glob
from collections import Counter
import time

archivos = glob.glob("datos/partidos/*.json")

categorias = Counter()

total = len(archivos)

print(f"PARTIDOS ENCONTRADOS: {total}")
print("Analizando missingPlayers...\n")

for i, f in enumerate(archivos, 1):

    try:
        with open(f, encoding="utf-8") as archivo:
            d = json.load(archivo)

        event_id = d["event"]["event"]["id"]

        url = f"https://www.sofascore.com/api/v1/event/{event_id}/lineups"

        try:
            respuesta = requests.get(
                url,
                impersonate="chrome",
                timeout=15
            )

            if respuesta.status_code != 200:
                print(f"[{i}/{total}] Evento {event_id}: HTTP {respuesta.status_code}")
                continue

            data = respuesta.json()

        except Exception as e:
            print(f"[{i}/{total}] Evento {event_id}: ERROR request -> {type(e).__name__}")
            continue

        encontrados = 0

        for lado in ["home", "away"]:

            missing_players = data.get(lado, {}).get("missingPlayers") or []

            for missing in missing_players:

                reason = missing.get("reason")
                description = missing.get("description")
                external_type = missing.get("externalType")

                categorias[(reason, description, external_type)] += 1
                encontrados += 1

        if encontrados:
            print(f"[{i}/{total}] Evento {event_id}: {encontrados} ausencias")

        if i % 25 == 0:
            print(f"--- PROGRESO: {i}/{total} ---")

        time.sleep(0.1)

    except Exception as e:
        print(f"[{i}/{total}] ERROR archivo -> {type(e).__name__}")
        continue


print("\n========================================")
print("CATEGORIAS ENCONTRADAS")
print("========================================")

for (reason, description, external_type), cantidad in categorias.most_common():
    print(
        f"{cantidad:3} | "
        f"reason={reason} | "
        f"externalType={external_type} | "
        f"{description}"
    )

print("\nTOTAL DE REGISTROS DE AUSENCIA:", sum(categorias.values()))