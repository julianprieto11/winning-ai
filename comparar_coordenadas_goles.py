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

        player_coords = gol.get("playerCoordinates")
        shot_coords = gol.get("goalShotCoordinates")

        if not player_coords:
            continue

        x = player_coords.get("x")
        y = player_coords.get("y")

        if x is None or y is None:
            continue

        distancia_x = min(x, 100 - x)

        distancia = math.sqrt(
            distancia_x ** 2 +
            (50 - y) ** 2
        )

        if distancia < 30:
            continue

        goles_lejanos.append({
            "jugador": gol.get("player", {}).get("name"),
            "minuto": incidente.get("time"),
            "player_coords": player_coords,
            "shot_coords": shot_coords,
            "distancia": distancia,
            "situacion": gol.get("situation"),
            "cuerpo": gol.get("bodyPart")
        })

goles_lejanos.sort(key=lambda x: x["distancia"], reverse=True)

print(f"Total encontrados: {len(goles_lejanos)}")
print()

for i, gol in enumerate(goles_lejanos, 1):
    print(f"{i}. {gol['jugador']}")
    print(f"   Minuto: {gol['minuto']}")
    print(f"   Player coordinates: {gol['player_coords']}")
    print(f"   Shot coordinates:   {gol['shot_coords']}")
    print(f"   Distancia anterior: {gol['distancia']:.2f}")
    print(f"   Situación: {gol['situacion']}")
    print(f"   Parte del cuerpo: {gol['cuerpo']}")
    print()