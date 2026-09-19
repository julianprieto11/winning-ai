import json
import glob
import math

goles_lejanos = []

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

        if distancia >= 30:
            goles_lejanos.append({
                "jugador": gol.get("player", {}).get("name"),
                "minuto": incidente.get("time"),
                "x": x,
                "y": y,
                "distancia": distancia,
                "situacion": gol.get("situation"),
                "cuerpo": gol.get("bodyPart"),
                "asistencia": gol.get("assist1", {}).get("player", {}).get("name")
            })

goles_lejanos.sort(key=lambda x: x["distancia"], reverse=True)

print(f"Total de goles lejanos encontrados: {len(goles_lejanos)}")
print()

for i, gol in enumerate(goles_lejanos, 1):
    print(f"{i}. {gol['jugador']}")
    print(f"   Minuto: {gol['minuto']}")
    print(f"   Coordenadas: x={gol['x']}, y={gol['y']}")
    print(f"   Distancia calculada: {gol['distancia']:.2f}")
    print(f"   Situación: {gol['situacion']}")
    print(f"   Parte del cuerpo: {gol['cuerpo']}")
    print(f"   Asistencia: {gol['asistencia']}")
    print()