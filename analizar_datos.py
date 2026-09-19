import json
import os

# ==========================================
# CONFIGURACIÓN
# ==========================================

CARPETA = "datos/partidos"

# ==========================================
# CONTENEDORES
# ==========================================

jugadores = {}
equipos = set()
campos_estadisticas = set()

partidos_ok = 0
partidos_error = 0

jugadores_con_estadisticas = 0
jugadores_sin_estadisticas = 0

# ==========================================
# RECORRER LOS 390 PARTIDOS
# ==========================================

archivos = [
    f for f in os.listdir(CARPETA)
    if f.endswith(".json")
]

archivos.sort()

print("================================")
print("ANÁLISIS DE DATOS")
print("================================")
print("ARCHIVOS ENCONTRADOS:", len(archivos))
print()

for numero, nombre_archivo in enumerate(archivos, start=1):

    ruta = os.path.join(
        CARPETA,
        nombre_archivo
    )

    try:

        with open(
            ruta,
            "r",
            encoding="utf-8"
        ) as archivo:

            partido = json.load(archivo)

        event = partido["event"]["event"]
        lineups = partido["lineups"]

        # ----------------------------------
        # EQUIPOS
        # ----------------------------------

        home_team = event["homeTeam"]
        away_team = event["awayTeam"]

        equipos.add(home_team["id"])
        equipos.add(away_team["id"])

        # ----------------------------------
        # JUGADORES
        # ----------------------------------

        todos_los_jugadores = (
            lineups.get("home", {}).get("players", [])
            +
            lineups.get("away", {}).get("players", [])
        )

        for jugador_data in todos_los_jugadores:

            jugador = jugador_data.get("player", {})

            jugador_id = jugador.get("id")

            if jugador_id is None:
                continue

            jugadores[jugador_id] = {
                "id": jugador_id,
                "name": jugador.get("name"),
                "slug": jugador.get("slug"),
                "shortName": jugador.get("shortName")
            }

            # ------------------------------
            # ESTADÍSTICAS
            # ------------------------------

            estadisticas = jugador_data.get(
                "statistics"
            )

            if estadisticas:

                jugadores_con_estadisticas += 1

                for campo in estadisticas.keys():
                    campos_estadisticas.add(campo)

            else:

                jugadores_sin_estadisticas += 1

        partidos_ok += 1

    except Exception as error:

        partidos_error += 1

        print(
            f"ERROR en {nombre_archivo}: {error}"
        )


# ==========================================
# RESULTADOS
# ==========================================

print()
print("================================")
print("RESULTADO DEL ANÁLISIS")
print("================================")

print("PARTIDOS CORRECTOS:", partidos_ok)
print("PARTIDOS CON ERROR:", partidos_error)

print()
print("EQUIPOS DISTINTOS:", len(equipos))
print("JUGADORES DISTINTOS:", len(jugadores))

print()
print(
    "JUGADORES CON ESTADÍSTICAS:",
    jugadores_con_estadisticas
)

print(
    "JUGADORES SIN ESTADÍSTICAS:",
    jugadores_sin_estadisticas
)

print()
print(
    "CAMPOS ESTADÍSTICOS DISTINTOS:",
    len(campos_estadisticas)
)

print()
print("================================")
print("CAMPOS ESTADÍSTICOS")
print("================================")

for campo in sorted(campos_estadisticas):
    print(campo)

print()
print("================================")
print("FIN DEL ANÁLISIS")
print("================================")