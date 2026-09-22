from curl_cffi import requests
import json
import glob
import time
import os

archivos = glob.glob("datos/partidos/*.json")

salida = "datos/ausencias_sofascore.json"

ausencias = []

total = len(archivos)

print(f"PARTIDOS: {total}")
print("Generando base de ausencias...\n")

for i, f in enumerate(archivos, 1):

    try:
        with open(f, encoding="utf-8") as archivo:
            d = json.load(archivo)

        evento = d["event"]["event"]
        event_id = evento["id"]

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
            print(
                f"[{i}/{total}] Evento {event_id}: "
                f"ERROR request -> {type(e).__name__}"
            )
            continue

        equipos = {
            "home": evento.get("homeTeam"),
            "away": evento.get("awayTeam")
        }

        for lado in ["home", "away"]:

            equipo = equipos.get(lado)

            if not equipo:
                continue

            team_id = equipo.get("id")
            team_name = equipo.get("name")

            missing_players = (
                data.get(lado, {}).get("missingPlayers") or []
            )

            for missing in missing_players:

                player = missing.get("player") or {}

                registro = {
                    "event_id": event_id,
                    "team_id": team_id,
                    "team_name": team_name,
                    "player_id": player.get("id"),
                    "player_name": player.get("name"),
                    "reason": missing.get("reason"),
                    "external_type": missing.get("externalType"),
                    "description": missing.get("description"),
                    "expected_end_date": missing.get("expectedEndDate")
                }

                ausencias.append(registro)

        if i % 25 == 0:
            print(
                f"[{i}/{total}] "
                f"Ausencias acumuladas: {len(ausencias)}"
            )

        time.sleep(0.1)

    except Exception as e:
        print(
            f"[{i}/{total}] ERROR archivo "
            f"{type(e).__name__}"
        )
        continue


os.makedirs("datos", exist_ok=True)

with open(salida, "w", encoding="utf-8") as archivo:
    json.dump(
        ausencias,
        archivo,
        ensure_ascii=False,
        indent=2
    )

print("\n========================================")
print("PROCESO TERMINADO")
print("========================================")
print(f"Registros guardados: {len(ausencias)}")
print(f"Archivo: {salida}")