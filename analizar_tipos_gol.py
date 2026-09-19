import json
import glob
import collections

goal_types = collections.Counter()
situations = collections.Counter()
body_parts = collections.Counter()

archivos = glob.glob("datos/partidos/*.json")

total_goles = 0

for archivo in archivos:
    with open(archivo, encoding="utf-8") as f:
        datos = json.load(f)

    incidentes = datos["incidents"].get("incidents", [])

    for incidente in incidentes:

        if incidente.get("incidentType") != "goal":
            continue

        total_goles += 1

        acciones = incidente.get("footballPassingNetworkAction", [])

        for accion in acciones:

            if accion.get("eventType") == "goal":

                goal_types[accion.get("goalType")] += 1
                situations[accion.get("situation")] += 1
                body_parts[accion.get("bodyPart")] += 1


print("=" * 60)
print("TOTAL DE GOLES")
print("=" * 60)
print(total_goles)

print()
print("=" * 60)
print("GOAL TYPES")
print("=" * 60)

for valor, cantidad in sorted(goal_types.items(), key=lambda x: str(x[0])):
    print(f"{valor}: {cantidad}")

print()
print("=" * 60)
print("SITUATIONS")
print("=" * 60)

for valor, cantidad in sorted(situations.items(), key=lambda x: str(x[0])):
    print(f"{valor}: {cantidad}")

print()
print("=" * 60)
print("BODY PARTS")
print("=" * 60)

for valor, cantidad in sorted(body_parts.items(), key=lambda x: str(x[0])):
    print(f"{valor}: {cantidad}")