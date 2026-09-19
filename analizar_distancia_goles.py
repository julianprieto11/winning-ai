import json
import glob
import math

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

        # Distancia horizontal al arco más cercano
        distancia_x = min(x, 100 - x)

        # Distancia aproximada usando ambas coordenadas
        distancia = math.sqrt(
            distancia_x ** 2 +
            (50 - y) ** 2
        )

        distancias.append({
            "jugador": incidente["player"]["name"],
            "x": x,
            "y": y,
            "distancia": distancia,
            "bodyPart": gol.get("bodyPart"),
            "situation": gol.get("situation")
        })

print("Cantidad de goles analizados:", len(distancias))
print()

print("10 goles MÁS CERCANOS:")
for dato in sorted(distancias, key=lambda x: x["distancia"])[:10]:
    print(
        f'{dato["jugador"]} | '
        f'dist={dato["distancia"]:.2f} | '
        f'x={dato["x"]} | y={dato["y"]} | '
        f'body={dato["bodyPart"]} | '
        f'situacion={dato["situation"]}'
    )

print()
print("10 goles MÁS LEJANOS:")
for dato in sorted(distancias, key=lambda x: x["distancia"], reverse=True)[:10]:
    print(
        f'{dato["jugador"]} | '
        f'dist={dato["distancia"]:.2f} | '
        f'x={dato["x"]} | y={dato["y"]} | '
        f'body={dato["bodyPart"]} | '
        f'situacion={dato["situation"]}'
    )