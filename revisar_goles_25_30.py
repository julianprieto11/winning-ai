import json
import glob

goles = []

for archivo in glob.glob("datos/partidos/*.json"):

    datos = json.load(open(archivo, encoding="utf-8"))

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

        if 25 <= distancia < 30:

            goles.append({
                "jugador": gol.get("player", {}).get("name"),
                "minuto": incidente.get("time"),
                "x": x,
                "y": coords.get("y"),
                "distancia": distancia,
                "situacion": gol.get("situation"),
                "cuerpo": gol.get("bodyPart")
            })

goles.sort(key=lambda g: g["distancia"], reverse=True)

print(f"Total: {len(goles)}")
print()

for i, gol in enumerate(goles, 1):

    print(f"{i}. {gol['jugador']}")
    print(f"   Minuto: {gol['minuto']}")
    print(f"   Coordenadas: x={gol['x']}, y={gol['y']}")
    print(f"   Distancia al arco: {gol['distancia']:.2f}")
    print(f"   Situación: {gol['situacion']}")
    print(f"   Parte del cuerpo: {gol['cuerpo']}")
    print()