import json

PARTIDOS = ["15270135", "16431117"]

for match_id in PARTIDOS:

    archivo = f"datos/partidos/{match_id}.json"

    with open(archivo, "r", encoding="utf-8") as f:
        datos = json.load(f)

    incidentes = datos.get("incidents", {}).get("incidents", [])

    print()
    print("=" * 120)
    print("PARTIDO:", match_id)
    print("=" * 120)

    for incidente in incidentes:

        if incidente.get("incidentType") != "goal":
            continue

        jugador = incidente.get("player") or {}

        print()
        print("MINUTO:", incidente.get("time"))
        print("JUGADOR:", jugador.get("name"))
        print("PLAYER ID:", jugador.get("id"))
        print("EQUIPO:", incidente.get("isHome"))
        print("CLASE:", incidente.get("incidentClass"))
        print("FROM:", incidente.get("from"))
        print("ASISTENTE:", incidente.get("assist1"))
        print("ASISTENTE 2:", incidente.get("assist2"))
        print("GOAL ASSIST:", incidente.get("goalAssist"))
        print("INCIDENTO COMPLETO:")
        print(incidente)