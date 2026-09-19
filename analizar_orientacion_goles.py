import json
import glob

mostrados = 0

for archivo in glob.glob("datos/partidos/*.json"):

    datos = json.load(open(archivo, encoding="utf-8"))

    evento = datos["event"]["event"]

    home_team_id = evento["homeTeam"]["id"]
    away_team_id = evento["awayTeam"]["id"]

    home_name = evento["homeTeam"]["name"]
    away_name = evento["awayTeam"]["name"]

    goles_partido = []

    for incidente in datos["incidents"]["incidents"]:

        if incidente.get("incidentType") != "goal":
            continue

        acciones = incidente.get("footballPassingNetworkAction", [])

        if not acciones:
            continue

        gol = acciones[-1]

        if gol.get("goalType") != "regular":
            continue

        player = gol.get("player", {})
        player_id = player.get("id")
        player_name = player.get("name")

        coords = gol.get("playerCoordinates")

        if not coords:
            continue

        x = coords.get("x")
        y = coords.get("y")

        if x is None or y is None:
            continue

        equipo = "DESCONOCIDO"

        if player_id is not None:

            if player_id == home_team_id:
                equipo = home_name

            elif player_id == away_team_id:
                equipo = away_name

        goles_partido.append({
            "minuto": incidente.get("time"),
            "jugador": player_name,
            "equipo": equipo,
            "x": x,
            "y": y,
            "situacion": gol.get("situation")
        })

    if len(goles_partido) < 2:
        continue

    mostrados += 1

    print("=" * 70)
    print(f"PARTIDO {mostrados}")
    print(f"{home_name} vs {away_name}")
    print()

    for gol in goles_partido:

        print(
            f"{gol['minuto']:>3}' | "
            f"{gol['equipo']:<30} | "
            f"{gol['jugador']:<25} | "
            f"x={gol['x']:>5} y={gol['y']:>5} | "
            f"{gol['situacion']}"
        )

    print()

    if mostrados >= 15:
        break