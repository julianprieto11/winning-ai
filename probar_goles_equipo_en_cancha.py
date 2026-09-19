import json
import glob

print()
print("=" * 100)
print("PRUEBA: GOLES DEL EQUIPO MIENTRAS EL JUGADOR ESTABA EN CANCHA")
print("=" * 100)

archivos = glob.glob("datos/partidos/*.json")

total_goles = 0
total_asignaciones = 0

for archivo in archivos:

    with open(archivo, "r", encoding="utf-8") as f:
        datos = json.load(f)

    event = datos["event"]["event"]
    lineups = datos["lineups"]
    incidentes = datos["incidents"]["incidents"]

    # Construimos los jugadores participantes
    jugadores = {}

    for lado in ["home", "away"]:

        for jugador in lineups[lado]["players"]:

            player_id = jugador["player"]["id"]
            stats = jugador.get("statistics", {})

            if "minutesPlayed" not in stats:
                continue

            jugadores[player_id] = {
                "nombre": jugador["player"].get("name", "SIN NOMBRE"),
                "equipo": jugador.get("teamId"),
                "minutos": stats.get("minutesPlayed", 0),
            }

    for incidente in incidentes:

        if incidente.get("incidentType") != "goal":
            continue

        if incidente.get("incidentClass") in [
            "missed",
            "ownGoal"
        ]:
            continue

        minuto = incidente.get("time")

        if minuto is None:
            continue

        jugador_gol = incidente.get("player")

        if not jugador_gol:
            continue

        goleador_id = jugador_gol.get("id")

        if goleador_id not in jugadores:
            continue

        equipo_goleador = jugadores[goleador_id]["equipo"]

        # Mostramos solamente algunos casos
        total_goles += 1

        participantes = []

        for player_id, jugador in jugadores.items():

            if jugador["equipo"] != equipo_goleador:
                continue

            minutos = jugador["minutos"]

            # Prueba simple:
            # si jugó el partido y el gol ocurrió antes
            # de su minuto de salida.
            #
            # La lógica definitiva de entradas/salidas la
            # incorporaremos después desde los incidentes.

            if minutos >= 90:
                activo = True
            else:
                activo = minuto <= minutos

            if activo:
                participantes.append(jugador["nombre"])

        total_asignaciones += len(participantes)

        if total_goles <= 20:

            print()
            print(
                f"Partido: {event.get('id')} | "
                f"Minuto: {minuto} | "
                f"Gol: {jugadores[goleador_id]['nombre']}"
            )

            print(
                "Equipo:",
                jugadores[goleador_id]["equipo"]
            )

            print(
                "Jugadores detectados como en cancha:",
                ", ".join(participantes)
            )

print()
print("=" * 100)
print("RESUMEN")
print("=" * 100)

print("Goles analizados:", total_goles)
print("Asignaciones jugador-gol:", total_asignaciones)