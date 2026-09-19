import json
import glob
from collections import Counter

rangos = Counter()
situaciones = Counter()
cuerpos = Counter()

total = 0

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

        if distancia < 20:
            continue

        total += 1

        if distancia < 25:
            rango = "20-25"
        elif distancia < 30:
            rango = "25-30"
        elif distancia < 35:
            rango = "30-35"
        elif distancia < 40:
            rango = "35-40"
        else:
            rango = "40+"

        rangos[rango] += 1
        situaciones[gol.get("situation")] += 1
        cuerpos[gol.get("bodyPart")] += 1


print("=" * 50)
print("GOLES REGULARES A 20+ DEL ARCO")
print("=" * 50)

print()
print(f"Total: {total}")

print()
print("POR DISTANCIA")
print("-" * 30)

for rango in ["20-25", "25-30", "30-35", "35-40", "40+"]:
    print(f"{rango}: {rangos[rango]}")

print()
print("POR SITUACIÓN")
print("-" * 30)

for situacion, cantidad in situaciones.most_common():
    print(f"{situacion}: {cantidad}")

print()
print("POR PARTE DEL CUERPO")
print("-" * 30)

for cuerpo, cantidad in cuerpos.most_common():
    print(f"{cuerpo}: {cantidad}")