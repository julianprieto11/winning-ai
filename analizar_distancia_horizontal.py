import json
import glob
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

        if x is None:
            continue

        distancia = min(x, 100 - x)

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
    elif distancia < 25:
        rangos["20 a 25"] += 1
    elif distancia < 30:
        rangos["25 a 30"] += 1
    elif distancia < 35:
        rangos["30 a 35"] += 1
    elif distancia < 40:
        rangos["35 a 40"] += 1
    else:
        rangos["40 o más"] += 1

print("Total:", len(distancias))
print()

for rango in [
    "0 a 5",
    "5 a 10",
    "10 a 15",
    "15 a 20",
    "20 a 25",
    "25 a 30",
    "30 a 35",
    "35 a 40",
    "40 o más"
]:

    print(f"{rango}: {rangos[rango]}")