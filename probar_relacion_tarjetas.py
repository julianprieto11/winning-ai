import json
import glob
import pandas as pd

ARCHIVOS = glob.glob("datos/partidos/*.json")

df = pd.read_csv("datos/dataset_jugadores.csv")

# Tomamos algunos jugadores que recibieron tarjetas
encontrados = 0

for archivo in ARCHIVOS:
    with open(archivo, encoding="utf-8") as f:
        datos = json.load(f)

    evento = datos["event"]["event"]
    event_id = evento.get("id")

    for incidente in datos["incidents"]["incidents"]:

        if incidente.get("incidentType") != "card":
            continue

        if incidente.get("rescinded") is True:
            continue

        jugador = incidente.get("player")

        if not jugador:
            continue

        player_id = jugador.get("id")

        if player_id is None:
            continue

        coincidencias = df[
            (df["event_id"] == event_id) &
            (df["player_id"] == player_id)
        ]

        if len(coincidencias) > 0:

            print("-" * 60)
            print("Jugador:", jugador.get("name"))
            print("Player ID:", player_id)
            print("Partido:", event_id)
            print("Tarjeta:", incidente.get("incidentClass"))
            print("Registros encontrados en dataset:", len(coincidencias))

            encontrados += 1

            if encontrados >= 10:
                break

    if encontrados >= 10:
        break

print("-" * 60)
print("Coincidencias encontradas:", encontrados)