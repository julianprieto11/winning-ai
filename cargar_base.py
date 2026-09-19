import sqlite3
import json
import os

# ==========================================
# CONFIGURACIÓN
# ==========================================

CARPETA_PARTIDOS = "datos/partidos"
BASE_DATOS = "datos/winning_ai.db"

# ==========================================
# CONECTAR CON SQLITE
# ==========================================

conexion = sqlite3.connect(BASE_DATOS)

cursor = conexion.cursor()

# ==========================================
# BUSCAR ARCHIVOS
# ==========================================

archivos = [
    archivo
    for archivo in os.listdir(CARPETA_PARTIDOS)
    if archivo.endswith(".json")
]

archivos.sort()

total = len(archivos)

print("================================")
print("CARGADOR DE BASE DE DATOS")
print("================================")
print("ARCHIVOS ENCONTRADOS:", total)
print()

partidos_cargados = 0
jugadores_cargados = set()
participaciones_cargadas = 0
estadisticas_cargadas = 0
incidentes_cargados = 0
estadisticas_partido_cargadas = 0
errores = 0

# ==========================================
# PROCESAR PARTIDOS
# ==========================================

for numero, nombre_archivo in enumerate(archivos, start=1):

    ruta = os.path.join(
        CARPETA_PARTIDOS,
        nombre_archivo
    )

    try:

        with open(
            ruta,
            "r",
            encoding="utf-8"
        ) as archivo:

            datos = json.load(archivo)

        event = datos["event"]["event"]
        lineups = datos["lineups"]
        incidents = datos["incidents"]
        statistics = datos["statistics"]

        event_id = event["id"]

        # ==================================
        # INFORMACIÓN DEL PARTIDO
        # ==================================

        fecha = event.get("startTimestamp")

        temporada_id = (
            event.get("season", {}).get("id")
        )

        torneo_id = (
            event.get("tournament", {}).get("uniqueTournament", {}).get("id")
        )

        ronda = (
            event.get("roundInfo", {}).get("round")
        )

        estado = (
            event.get("status", {}).get("type")
        )

        local = event["homeTeam"]
        visitante = event["awayTeam"]

        local_id = local["id"]
        local_nombre = local["name"]

        visitante_id = visitante["id"]
        visitante_nombre = visitante["name"]

        goles_local = event.get("homeScore", {}).get("current")
        goles_visitante = event.get("awayScore", {}).get("current")

        # ==================================
        # ÁRBITRO
        # ==================================

        arbitro = event.get("referee")

        if arbitro:

            arbitro_id = arbitro.get("id")
            arbitro_nombre = arbitro.get("name")

        else:

            arbitro_id = None
            arbitro_nombre = None

        # ==================================
        # GUARDAR PARTIDO
        # ==================================

        cursor.execute("""
        INSERT OR REPLACE INTO partidos (

            event_id,
            fecha,
            temporada_id,
            torneo_id,
            ronda,
            estado,
            local_id,
            local_nombre,
            visitante_id,
            visitante_nombre,
            goles_local,
            goles_visitante,
            arbitro_id,
            arbitro_nombre

        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            event_id,
            fecha,
            temporada_id,
            torneo_id,
            ronda,
            estado,
            local_id,
            local_nombre,
            visitante_id,
            visitante_nombre,
            goles_local,
            goles_visitante,
            arbitro_id,
            arbitro_nombre

        ))

        # ==================================
        # JUGADORES
        # ==================================

        todos_los_jugadores = []

        todos_los_jugadores.extend(
            [
                (jugador, local_id, local_nombre)
                for jugador in
                lineups.get("home", {}).get("players", [])
            ]
        )

        todos_los_jugadores.extend(
            [
                (jugador, visitante_id, visitante_nombre)
                for jugador in
                lineups.get("away", {}).get("players", [])
            ]
        )

        for jugador_data, equipo_id, equipo_nombre in todos_los_jugadores:

            jugador = jugador_data.get("player", {})

            jugador_id = jugador.get("id")

            if jugador_id is None:
                continue

            nombre = jugador.get("name")
            nombre_corto = jugador.get("shortName")
            slug = jugador.get("slug")

            # ==============================
            # TABLA JUGADORES
            # ==============================

            cursor.execute("""
            INSERT OR REPLACE INTO jugadores (

                jugador_id,
                nombre,
                nombre_corto,
                slug

            )
            VALUES (?, ?, ?, ?)
            """, (

                jugador_id,
                nombre,
                nombre_corto,
                slug

            ))

            jugadores_cargados.add(jugador_id)

            # ==============================
            # PARTICIPACIÓN
            # ==============================

            titular = jugador_data.get("starter")

            if titular is None:
                titular = 0
            else:
                titular = 1 if titular else 0

            posicion = jugador_data.get("position")

            cursor.execute("""
            INSERT INTO jugador_partido (

                event_id,
                jugador_id,
                equipo_id,
                equipo_nombre,
                titular,
                posicion

            )
            VALUES (?, ?, ?, ?, ?, ?)
            """, (

                event_id,
                jugador_id,
                equipo_id,
                equipo_nombre,
                titular,
                posicion

            ))

            participaciones_cargadas += 1

            # ==============================
            # ESTADÍSTICAS DEL JUGADOR
            # ==============================

            estadisticas = jugador_data.get("statistics")

            if estadisticas:

                cursor.execute("""
                INSERT INTO estadisticas_jugador (

                    event_id,
                    jugador_id,
                    estadisticas_json

                )
                VALUES (?, ?, ?)
                """, (

                    event_id,
                    jugador_id,
                    json.dumps(
                        estadisticas,
                        ensure_ascii=False
                    )

                ))

                estadisticas_cargadas += 1

        # ==================================
        # INCIDENTES
        # ==================================

        lista_incidentes = incidents.get(
            "incidents",
            []
        )

        for incidente in lista_incidentes:

            cursor.execute("""
            INSERT INTO incidentes (

                event_id,
                incidente_json

            )
            VALUES (?, ?)
            """, (

                event_id,
                json.dumps(
                    incidente,
                    ensure_ascii=False
                )

            ))

            incidentes_cargados += 1

        # ==================================
        # ESTADÍSTICAS GENERALES
        # ==================================

        lista_estadisticas = statistics.get(
            "statistics",
            []
        )

        for periodo in lista_estadisticas:

            nombre_periodo = periodo.get(
                "period",
                "UNKNOWN"
            )

            estadisticas_periodo = periodo.get(
                "groups",
                []
            )

            cursor.execute("""
            INSERT INTO estadisticas_partido (

                event_id,
                periodo,
                estadisticas_json

            )
            VALUES (?, ?, ?)
            """, (

                event_id,
                nombre_periodo,
                json.dumps(
                    estadisticas_periodo,
                    ensure_ascii=False
                )

            ))

            estadisticas_partido_cargadas += 1

        partidos_cargados += 1

        print(
            f"[{numero}/{total}] OK → "
            f"{local_nombre} vs {visitante_nombre}"
        )

    except Exception as error:

        errores += 1

        print(
            f"[{numero}/{total}] ERROR → "
            f"{nombre_archivo}"
        )

        print(
            "   ",
            error
        )

# ==========================================
# GUARDAR TODO
# ==========================================

conexion.commit()

conexion.close()

# ==========================================
# RESULTADO
# ==========================================

print()
print("================================")
print("CARGA TERMINADA")
print("================================")

print(
    "PARTIDOS CARGADOS:",
    partidos_cargados
)

print(
    "JUGADORES DISTINTOS:",
    len(jugadores_cargados)
)

print(
    "PARTICIPACIONES:",
    participaciones_cargadas
)

print(
    "ESTADÍSTICAS DE JUGADORES:",
    estadisticas_cargadas
)

print(
    "INCIDENTES:",
    incidentes_cargados
)

print(
    "ESTADÍSTICAS DE PARTIDOS:",
    estadisticas_partido_cargadas
)

print(
    "ERRORES:",
    errores
)

print("================================")