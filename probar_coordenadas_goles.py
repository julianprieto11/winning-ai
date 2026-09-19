import json
import glob

contador = 0

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

        jugador = incidente["player"]["name"]
        situacion = gol.get("situation")
        body = gol.get("bodyPart")

        coordenadas = gol.get("playerCoordinates", {})
        x = coordenadas.get("x")
        y = coordenadas.get("y")

        print(
            f"{jugador} | "
            f"situacion={situacion} | "
            f"body={body} | "
            f"x={x} | "
            f"y={y}"
        )

        contador += 1

        if contador >= 10:
            raise SystemExit