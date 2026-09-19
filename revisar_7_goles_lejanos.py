import json
import glob

print("=" * 100)
print("GOLES REGULARES A 20+ DEL ARCO")
print("=" * 100)

for archivo in glob.glob("datos/partidos/*.json"):

    datos = json.load(open(archivo, encoding="utf-8"))

    evento = datos["event"]["event"]

    for incidente in datos["incidents"]["incidents"]:

        if incidente.get("incidentType") != "goal":
            continue

        acciones = incidente.get("footballPassingNetworkAction", [])

        if not acciones:
            continue

        gol = acciones[-1]

        if gol.get("goalType") != "regular":
            continue

        coords = gol.get("playerCoordinates")

        if not coords:
            continue

        x = coords.get("x")

        if x is None:
            continue

        distancia = min(x, 100 - x)

        if distancia < 20:
            continue

        if gol.get("situation") != "regular":
            continue

        print()
        print("-" * 100)

        print("Jugador:", incidente.get("player", {}).get("name"))
        print("Partido:", evento.get("homeTeam", {}).get("name"),
              "vs",
              evento.get("awayTeam", {}).get("name"))

        print("Minuto:", incidente.get("time"))
        print("Distancia horizontal:", round(distancia, 2))
        print("Player coordinates:", coords)
        print("Goal shot coordinates:", gol.get("goalShotCoordinates"))
        print("Goal mouth coordinates:", gol.get("goalMouthCoordinates"))
        print("Situación:", gol.get("situation"))
        print("Parte del cuerpo:", gol.get("bodyPart"))
        print("Acción completa:")
        print(gol)