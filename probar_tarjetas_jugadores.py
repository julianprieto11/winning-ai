import json
import glob

ARCHIVOS = glob.glob("datos/partidos/*.json")

mostrados = 0

for archivo in ARCHIVOS:
    with open(archivo, encoding="utf-8") as f:
        datos = json.load(f)

    evento = datos["event"]["event"]
    event_id = evento.get("id")

    for incidente in datos["incidents"]["incidents"]:
        if incidente.get("incidentType") != "card":
            continue

        if incidente.get("incidentClass") != "yellowRed":
            continue

        jugador = incidente.get("player")

        if not jugador:
            continue

        print("-" * 60)
        print("Partido:", event_id)
        print("Jugador:", jugador.get("name"))
        print("Player ID:", jugador.get("id"))
        print("Clase:", incidente.get("incidentClass"))
        print("Tiempo:", incidente.get("time"))
        print("Motivo:", incidente.get("reason"))
        print("Rescindida:", incidente.get("rescinded"))

        mostrados += 1

        if mostrados >= 10:
            break

    if mostrados >= 10:
        break

print("-" * 60)
print("Segundas amarillas mostradas:", mostrados)