import json
import glob
import math
from collections import Counter

distancias = []

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
        y = coords.get("y")

        if x is None or y is None:
            continue

        distancia_x = min(x, 100 - x)

        distancia = math.sqrt(
            distancia_x ** 2 +
            (50 - y) ** 2
        )

        distancias.append(distancia)

rangos = Counter()

for distancia in distancias:
    if distancia < 5:
        rangos["0 a 5"] += 1
    elif distancia < 10:
        rangos["5 a 10"] += 1
    elif distancia < 15:
        rangos["10 a 15"] += 1
    elif distancia < 20:
        rangos["15 a 20"] += 1
    elif distancia < 30:
        rangos["20 a 30"] += 1
    elif distancia < 40:
        rangos["30 a 40"] += 1
    else:
        rangos["40 o más"] += 1

print("Total:", len(distancias))
print()

for rango in [
    "0 a 5",
    "5 a 10",
    "10 a 15",
    "15 a 20",
    "20 a 30",
    "30 a 40",
    "40 o más"
]:
    print(f"{rango}: {rangos[rango]}")