import json
import csv
from pathlib import Path
from collections import defaultdict


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATOS_DIR = BASE_DIR / "datos"
PITCHAPI_DIR = DATOS_DIR / "pitchapi"

OUTPUT_FILE = DATOS_DIR / "dataset_winning_pitchapi.csv"
POSICIONES_FILE = DATOS_DIR / "posiciones_finales_jugadores.csv"


# ============================================================
# UTILIDADES
# ============================================================

def cargar_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def cargar_csv(path):
    try:
        with open(
            path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def normalizar_numero(valor):
    if valor is None:
        return 0.0

    try:
        return float(valor)
    except (ValueError, TypeError):
        return 0.0


def archivos_por_sufijo(sufijo):
    return sorted(
        PITCHAPI_DIR.glob(f"*{sufijo}")
    )


# ============================================================
# POSICIONES FINALES
# ============================================================

print()
print("=" * 100)
print("CARGANDO POSICIONES FINALES")
print("=" * 100)
print()

posiciones_por_jugador = {}

filas_posiciones = cargar_csv(
    POSICIONES_FILE
)

for fila in filas_posiciones:

    player_id = fila.get(
        "player_id"
    )

    posicion = fila.get(
        "posicion_final"
    )

    if player_id and posicion:

        posiciones_por_jugador[player_id] = posicion


print(
    f"Jugadores con posición: "
    f"{len(posiciones_por_jugador)}"
)


# ============================================================
# STATS DE PLAYERS
# ============================================================

def construir_stats_index(player):

    resultado = {}

    for grupo in player.get("stats", []):

        if not isinstance(grupo, dict):
            continue

        stats = grupo.get("stats", {})

        if not isinstance(stats, dict):
            continue

        for titulo, contenido in stats.items():

            if not isinstance(contenido, dict):
                continue

            key = contenido.get("key")

            if key:
                resultado[str(key).lower()] = contenido

            if titulo:
                resultado[str(titulo).lower()] = contenido

    return resultado


def obtener_stat(player, *nombres):

    indice = construir_stats_index(player)

    for nombre in nombres:

        if nombre is None:
            continue

        clave = str(nombre).lower()

        if clave in indice:
            return indice[clave]

    return None


def stat_value(player, *nombres):

    stat = obtener_stat(
        player,
        *nombres
    )

    if not stat:
        return None

    contenido = stat.get("stat")

    if not isinstance(contenido, dict):
        return None

    return contenido.get("value")


def stat_total_value(player, *nombres):

    stat = obtener_stat(
        player,
        *nombres
    )

    if not stat:
        return None

    contenido = stat.get("stat")

    if not isinstance(contenido, dict):
        return None

    return contenido.get("total")


# ============================================================
# CARGAR PARTIDOS
# ============================================================

print()
print("=" * 100)
print("CARGANDO PARTIDOS")
print("=" * 100)
print()

partidos = {}

MATCHES_DIR = PITCHAPI_DIR / "matches"

if MATCHES_DIR.exists():

    archivos_matches = sorted(
        MATCHES_DIR.glob("*.json")
    )

else:

    archivos_matches = []

    for archivo in PITCHAPI_DIR.glob("*.json"):

        nombre = archivo.name

        if (
            not nombre.endswith("_players.json")
            and not nombre.endswith("_advanced_players.json")
            and not nombre.endswith("_events.json")
        ):
            archivos_matches.append(archivo)


for archivo in archivos_matches:

    data = cargar_json(archivo)

    if not data:
        continue

    partido = data.get("data")

    if not isinstance(partido, dict):
        continue

    match_id = partido.get("id")

    if match_id:
        partidos[match_id] = partido


print(
    f"Partidos cargados: {len(partidos)}"
)


# ============================================================
# CARGAR PLAYERS
# ============================================================

print()
print("=" * 100)
print("CARGANDO PLAYERS")
print("=" * 100)
print()

players_por_partido = {}

archivos_players = archivos_por_sufijo(
    "_players.json"
)

for archivo in archivos_players:

    data = cargar_json(archivo)

    if not data:
        continue

    match_id = archivo.name.replace(
        "_players.json",
        ""
    )

    players = data.get(
        "data",
        []
    )

    if not isinstance(players, list):
        players = []

    players_por_partido[match_id] = players


print(
    f"Archivos players: "
    f"{len(players_por_partido)}"
)


# ============================================================
# CARGAR ADVANCED PLAYERS
# ============================================================

print()
print("=" * 100)
print("CARGANDO ADVANCED PLAYERS")
print("=" * 100)
print()

advanced_por_partido = {}

archivos_advanced = archivos_por_sufijo(
    "_advanced_players.json"
)

for archivo in archivos_advanced:

    data = cargar_json(archivo)

    if not data:
        continue

    match_id = archivo.name.replace(
        "_advanced_players.json",
        ""
    )

    contenido = data.get(
        "data",
        {}
    )

    if not isinstance(contenido, dict):
        continue

    jugadores = contenido.get(
        "players",
        []
    )

    if not isinstance(jugadores, list):
        jugadores = []

    advanced_por_partido[match_id] = jugadores


print(
    f"Archivos advanced: "
    f"{len(advanced_por_partido)}"
)


# ============================================================
# CARGAR EVENTS
# ============================================================

print()
print("=" * 100)
print("CARGANDO EVENTS")
print("=" * 100)
print()

events_por_partido = {}

archivos_events = archivos_por_sufijo(
    "_events.json"
)

for archivo in archivos_events:

    data = cargar_json(archivo)

    if not data:
        continue

    match_id = archivo.name.replace(
        "_events.json",
        ""
    )

    contenido = data.get(
        "data",
        {}
    )

    if not isinstance(contenido, dict):
        continue

    eventos = contenido.get(
        "events",
        []
    )

    if not isinstance(eventos, list):
        eventos = []

    events_por_partido[match_id] = eventos


print(
    f"Archivos events: "
    f"{len(events_por_partido)}"
)


# ============================================================
# INDEXAR ADVANCED
# ============================================================

def indexar_advanced(jugadores):

    resultado = {}

    for jugador in jugadores:

        player_info = jugador.get(
            "player",
            {}
        )

        player_id = player_info.get(
            "id"
        )

        if player_id:
            resultado[player_id] = jugador

    return resultado


# ============================================================
# INFORMACIÓN DE EVENTS
# ============================================================

def minuto_evento(evento):

    minuto = normalizar_numero(
        evento.get("minute")
    )

    agregado = normalizar_numero(
        evento.get("minute_added")
    )

    return minuto + (
        agregado / 100.0
    )


def ordenar_eventos(eventos):

    return sorted(
        eventos,
        key=minuto_evento
    )


def construir_info_eventos(
    eventos,
    partido,
    players
):

    eventos_ordenados = ordenar_eventos(
        eventos
    )

    # --------------------------------------------------------
    # Equipos
    # --------------------------------------------------------

    home_team = partido.get(
        "home_team",
        {}
    )

    away_team = partido.get(
        "away_team",
        {}
    )

    home_id = home_team.get("id")
    away_id = away_team.get("id")

    # --------------------------------------------------------
    # Jugadores por equipo
    # --------------------------------------------------------

    jugadores_por_equipo = defaultdict(set)

    for player in players:

        player_id = (
            player.get("player", {})
            .get("id")
        )

        team_id = player.get(
            "team_id"
        )

        if player_id and team_id:

            jugadores_por_equipo[
                team_id
            ].add(player_id)

    # --------------------------------------------------------
    # Sustituciones
    # --------------------------------------------------------

    sustituciones_entrada = {}

    sustituciones_salida = {}

    for evento in eventos_ordenados:

        if evento.get(
            "event_type"
        ) != "substitution":

            continue

        sale = evento.get(
            "player",
            {}
        )

        entra = evento.get(
            "sub_in_player",
            {}
        )

        sale_id = sale.get("id")
        entra_id = entra.get("id")

        minuto = minuto_evento(
            evento
        )

        if sale_id:

            sustituciones_salida.setdefault(
                sale_id,
                []
            ).append(
                minuto
            )

        if entra_id:

            sustituciones_entrada.setdefault(
                entra_id,
                []
            ).append(
                minuto
            )

    # --------------------------------------------------------
    # Amarillas / rojas
    # --------------------------------------------------------

    amarillas_por_jugador = defaultdict(int)

    rojas_por_jugador = defaultdict(int)

    rojas_directas_por_jugador = defaultdict(int)

    segunda_amarilla_por_jugador = defaultdict(int)

    for evento in eventos_ordenados:

        tipo = evento.get(
            "event_type"
        )

        jugador = evento.get(
            "player",
            {}
        )

        player_id = jugador.get(
            "id"
        )

        if not player_id:
            continue

        if tipo == "yellowcard":

            amarillas_por_jugador[
                player_id
            ] += 1

        elif tipo == "redcard":

            rojas_por_jugador[
                player_id
            ] += 1

    # --------------------------------------------------------
    # Determinar segunda amarilla
    #
    # Si un jugador recibe roja y previamente recibió
    # amarilla, tratamos la expulsión como segunda amarilla.
    # --------------------------------------------------------

    amarillas_acumuladas = defaultdict(int)

    for evento in eventos_ordenados:

        tipo = evento.get(
            "event_type"
        )

        jugador = evento.get(
            "player",
            {}
        )

        player_id = jugador.get(
            "id"
        )

        if not player_id:
            continue

        if tipo == "yellowcard":

            amarillas_acumuladas[
                player_id
            ] += 1

        elif tipo == "redcard":

            if amarillas_acumuladas[
                player_id
            ] >= 1:

                segunda_amarilla_por_jugador[
                    player_id
                ] += 1

            else:

                rojas_directas_por_jugador[
                    player_id
                ] += 1

    # --------------------------------------------------------
    # Goles
    #
    # PitchAPI PLAYERS es la fuente principal para la cantidad
    # total de goles del jugador.
    #
    # EVENTS se utiliza como complemento para identificar
    # autogoles y goles de penal cuando esa información existe.
    #
    # Esto evita perder goles cuando EVENTS no contiene todos
    # los eventos de gol del partido.
    # --------------------------------------------------------

    goles_por_jugador = defaultdict(int)
    autogoles_por_jugador = defaultdict(int)
    goles_penal_por_jugador = defaultdict(int)

    # --------------------------------------------------------
    # 1. Goles desde PLAYERS
    # --------------------------------------------------------

    for player in players:

        player_id = player.get(
            "player",
            {}
        ).get(
            "id"
        )

        if not player_id:
            continue

        goals = stat_value(
            player,
            "goals",
            "Goals"
        )

        if goals is None:
            goals = 0

        goals = int(
            normalizar_numero(
                goals
            )
        )

        if goals > 0:

            goles_por_jugador[
                player_id
            ] += goals

    # --------------------------------------------------------
    # 2. Información adicional desde EVENTS
    #
    # Si EVENTS informa que un gol fue penal o autogol,
    # guardamos esa clasificación.
    #
    # NO usamos EVENTS para determinar cuántos goles hizo
    # el jugador, porque puede estar incompleto.
    # --------------------------------------------------------

    for evento in eventos_ordenados:

        if evento.get(
            "event_type"
        ) != "goal":

            continue

        jugador = evento.get(
            "player",
            {}
        )

        player_id = jugador.get(
            "id"
        )

        if not player_id:
            continue

        if evento.get(
            "is_own_goal",
            False
        ):

            autogoles_por_jugador[
                player_id
            ] += 1

        elif evento.get(
            "is_penalty",
            False
        ):

            goles_penal_por_jugador[
                player_id
            ] += 1

    # --------------------------------------------------------
    # 3. Evitar que las clasificaciones de EVENTS superen
    #    la cantidad real de goles registrada por PLAYERS.
    # --------------------------------------------------------

    for player_id in list(
        goles_penal_por_jugador.keys()
    ):

        goles_penal_por_jugador[
            player_id
        ] = min(
            goles_penal_por_jugador[
                player_id
            ],
            goles_por_jugador.get(
                player_id,
                0
            )
        )

    # --------------------------------------------------------
    # GOLES DEL PARTIDO
    #
    # Los usamos para determinar el resultado del equipo
    # mientras cada jugador estaba en cancha.
    # --------------------------------------------------------

    goles_equipo_en_cancha = defaultdict(
        float
    )

    # --------------------------------------------------------
    # Jugadores activos al comienzo
    #
    # Un jugador que tiene minutos > 0 y no aparece como
    # entrada de sustitución se considera titular.
    # --------------------------------------------------------

    activos = defaultdict(set)

    for player in players:

        player_info = player.get(
            "player",
            {}
        )

        player_id = player_info.get(
            "id"
        )

        team_id = player.get(
            "team_id"
        )

        if not player_id or not team_id:
            continue

        minutos = stat_value(
            player,
            "minutes_played",
            "Minutes played"
        )

        minutos = normalizar_numero(
            minutos
        )

        if minutos <= 0:
            continue

        if player_id not in sustituciones_entrada:

            activos[
                team_id
            ].add(
                player_id
            )

    # --------------------------------------------------------
    # Bonus de resultado por jugador
    #
    # +1 por gol de su equipo mientras está en cancha
    # -0.5 por gol recibido mientras está en cancha
    # máximo ±3
    # --------------------------------------------------------

    bonus_resultado_jugador = defaultdict(
        float
    )

    for evento in eventos_ordenados:

        tipo = evento.get(
            "event_type"
        )

        team_id = evento.get(
            "team_id"
        )

        # ----------------------------------------------------
        # Sustitución
        # ----------------------------------------------------

        if tipo == "substitution":

            sale = evento.get(
                "player",
                {}
            )

            entra = evento.get(
                "sub_in_player",
                {}
            )

            sale_id = sale.get("id")
            entra_id = entra.get("id")

            if sale_id:

                activos[
                    team_id
                ].discard(
                    sale_id
                )

            if entra_id:

                activos[
                    team_id
                ].add(
                    entra_id
                )

            continue

        # ----------------------------------------------------
        # Gol
        # ----------------------------------------------------

        if tipo != "goal":
            continue

        if team_id not in (
            home_id,
            away_id
        ):
            continue

        # Para un autogol, el team_id representa el equipo
        # beneficiado por el gol. Por eso, para el bonus de
        # resultado usamos el equipo que figura en el evento.
        equipo_goleador = team_id

        if equipo_goleador == home_id:

            equipo_recibe = away_id

        else:

            equipo_recibe = home_id

        # ----------------------------------------------------
        # Gol a favor
        # ----------------------------------------------------

        for player_id in list(
            activos[equipo_goleador]
        ):

            bonus_resultado_jugador[
                player_id
            ] += 1.0

        # ----------------------------------------------------
        # Gol en contra
        # ----------------------------------------------------

        for player_id in list(
            activos[equipo_recibe]
        ):

            bonus_resultado_jugador[
                player_id
            ] -= 0.5

    # --------------------------------------------------------
    # Limitar bonus ±3
    # --------------------------------------------------------

    for player_id in list(
        bonus_resultado_jugador.keys()
    ):

        bonus_resultado_jugador[
            player_id
        ] = max(
            -3.0,
            min(
                3.0,
                bonus_resultado_jugador[
                    player_id
                ]
            )
        )

    # --------------------------------------------------------
    # Puntos por goles
    # --------------------------------------------------------

    goles_asistencias_por_jugador = defaultdict(
        float
    )

    for player_id, cantidad in goles_por_jugador.items():

        penales = goles_penal_por_jugador.get(
            player_id,
            0
        )

        goles_normales = (
            cantidad
            - penales
        )

        puntos = (
            goles_normales * 6.0
            + penales * 4.5
        )

        goles_asistencias_por_jugador[
            player_id
        ] += puntos

    # --------------------------------------------------------
    # Autogoles
    # --------------------------------------------------------

    for player_id, cantidad in autogoles_por_jugador.items():

        goles_asistencias_por_jugador[
            player_id
        ] -= (
            cantidad * 6.0
        )

    return {
        "goles": goles_por_jugador,
        "autogoles": autogoles_por_jugador,
        "goles_penal": goles_penal_por_jugador,

        "goles_asistencias":
            goles_asistencias_por_jugador,

        "amarillas":
            amarillas_por_jugador,

        "rojas":
            rojas_por_jugador,

        "rojas_directas":
            rojas_directas_por_jugador,

        "segunda_amarilla":
            segunda_amarilla_por_jugador,

        "bonus_resultado":
            bonus_resultado_jugador,

        "sustituciones_entrada":
            sustituciones_entrada,

        "sustituciones_salida":
            sustituciones_salida
    }


# ============================================================
# RESULTADO DEL PARTIDO
# ============================================================

def obtener_resultado(
    partido,
    team_id
):

    score_home = partido.get(
        "score_home"
    )

    score_away = partido.get(
        "score_away"
    )

    if (
        score_home is None
        or score_away is None
    ):
        return 0, 0, False

    home_team = partido.get(
        "home_team",
        {}
    )

    away_team = partido.get(
        "away_team",
        {}
    )

    home_id = home_team.get(
        "id"
    )

    away_id = away_team.get(
        "id"
    )

    try:

        score_home = float(
            score_home
        )

        score_away = float(
            score_away
        )

    except (
        ValueError,
        TypeError
    ):

        return 0, 0, False

    if team_id == home_id:

        goles_favor = score_home
        goles_contra = score_away

    elif team_id == away_id:

        goles_favor = score_away
        goles_contra = score_home

    else:

        return 0, 0, False

    if goles_favor > goles_contra:

        resultado = 3

    elif goles_favor == goles_contra:

        resultado = 1

    else:

        resultado = 0

    return (
        resultado,
        goles_contra,
        True
    )


# ============================================================
# CALCULAR WINNING
# ============================================================

print()
print("=" * 100)
print("CALCULANDO WINNING CON PITCHAPI")
print("=" * 100)
print()

registros = []

partidos_procesados = 0


for match_id, partido in partidos.items():

    players = players_por_partido.get(
        match_id,
        []
    )

    if not players:
        continue

    advanced_players = advanced_por_partido.get(
        match_id,
        []
    )

    advanced_index = indexar_advanced(
        advanced_players
    )

    eventos = events_por_partido.get(
        match_id,
        []
    )

    info_eventos = construir_info_eventos(
        eventos,
        partido,
        players
    )

    for player in players:

        player_info = player.get(
            "player",
            {}
        )

        player_id = player_info.get(
            "id"
        )

        if not player_id:
            continue

        player_name = player_info.get(
            "name",
            "Desconocido"
        )

        team_id = player.get(
            "team_id"
        )

        # ====================================================
        # MINUTOS
        # ====================================================

        minutes = stat_value(
            player,
            "minutes_played",
            "Minutes played"
        )

        if minutes is None:
            minutes = 0

        minutes = normalizar_numero(
            minutes
        )

        # ====================================================
        # NO PROCESAR JUGADORES QUE NO ENTRARON
        # ====================================================

        if minutes <= 0:
            continue

        # ====================================================
        # POSICIÓN FINAL
        # ====================================================

        position = posiciones_por_jugador.get(
            player_id
        )

        if position is None:
            position = "REVISAR"

        # ====================================================
        # ADVANCED
        # ====================================================

        advanced = advanced_index.get(
            player_id,
            {}
        )

        passing = advanced.get(
            "passing",
            {}
        ) or {}

        carrying = advanced.get(
            "carrying",
            {}
        ) or {}

        creation = advanced.get(
            "creation",
            {}
        ) or {}

        defending = advanced.get(
            "defending",
            {}
        ) or {}

        # ====================================================
        # PARTICIPACIÓN
        # ====================================================

        participacion = (
            minutes * 0.03
        )

        # ====================================================
        # ÁREA RIVAL
        # ====================================================

        touches_opp_box = stat_value(
            player,
            "touches_opp_box",
            "Touches in opposition box"
        )

        if touches_opp_box is None:
            touches_opp_box = 0

        puntos_area = (
            normalizar_numero(
                touches_opp_box
            ) * 0.12
        )

        # ====================================================
        # ÚLTIMO TERCIO
        # ====================================================

        touches_final_third = stat_value(
            player,
            "touches_final_third",
            "Touches in final third",
            "Touches in attacking third"
        )

        if touches_final_third is None:
            touches_final_third = 0

        puntos_ultimo_tercio = (
            normalizar_numero(
                touches_final_third
            ) * 0.02
        )

        # ====================================================
        # CARRERAS PROGRESIVAS
        # ====================================================

        progressive_carries = (
            normalizar_numero(
                carrying.get(
                    "progressive_carries"
                )
            )
        )

        puntos_carreras = (
            progressive_carries * 0.05
        )

        # ====================================================
        # DUELOS
        # ====================================================

        duels_won = (
            normalizar_numero(
                defending.get(
                    "duels_won"
                )
            )
        )

        duels_lost = stat_value(
            player,
            "duels_lost",
            "Duels lost"
        )

        if duels_lost is None:
            duels_lost = 0

        duels_lost = normalizar_numero(
            duels_lost
        )

        puntos_duelos = (
            duels_won * 0.20
            - duels_lost * 0.20
        )

        # ====================================================
        # MAL CONTROL / DISPOSSESSION
        # ====================================================

        miscontrols = (
            normalizar_numero(
                carrying.get(
                    "miscontrols"
                )
            )
        )

        dispossessed = (
            normalizar_numero(
                carrying.get(
                    "dispossessed"
                )
            )
        )

        puntos_perdidas = (
            -miscontrols * 0.20
            -dispossessed * 0.20
        )

        # ====================================================
        # REGATES FALLIDOS
        # ====================================================

        take_ons = (
            normalizar_numero(
                carrying.get(
                    "take_ons"
                )
            )
        )

        take_ons_won = (
            normalizar_numero(
                carrying.get(
                    "take_ons_won"
                )
            )
        )

        failed_dribbles = max(
            0,
            take_ons - take_ons_won
        )

        puntos_regates_fallidos = (
            -failed_dribbles * 0.30
        )

        # ====================================================
        # EXCESO DE PÉRDIDAS
        #
        # Se aplica sobre pérdidas de posesión:
        # DEL >12
        # VOL >8
        # DEF >11
        # ARQ sin penalización
        # ====================================================

        if position == "DEL":

            limite_perdidas = 12

        elif position == "VOL":

            limite_perdidas = 8

        elif position == "DEF":

            limite_perdidas = 11

        else:

            limite_perdidas = None

        if limite_perdidas is None:

            puntos_exceso_perdidas = 0.0

            exceso_perdidas = 0

        else:

            perdidas_totales = (
                miscontrols
                + dispossessed
            )

            exceso_perdidas = max(
                0,
                perdidas_totales
                - limite_perdidas
            )

            puntos_exceso_perdidas = (
                exceso_perdidas
                * -0.15
            )

        # ====================================================
        # PASES
        # ====================================================

        accurate_passes = stat_value(
            player,
            "accurate_passes",
            "Accurate passes"
        )

        if accurate_passes is None:
            accurate_passes = 0

        accurate_passes = normalizar_numero(
            accurate_passes
        )

        passes = normalizar_numero(
            passing.get(
                "passes"
            )
        )

        progressive_passes = (
            normalizar_numero(
                passing.get(
                    "progressive_passes"
                )
            )
        )

        if passes > 0:

            precision = (
                accurate_passes
                / passes
            )

        else:

            precision = 0.0

        puntos_pases = (
            accurate_passes
            * 0.02
            * precision
        )

        puntos_pases += (
            progressive_passes
            * 0.02
            * precision
        )

        # ----------------------------------------------------
        # Pases al último tercio
        # ----------------------------------------------------

        passes_into_final_third = stat_value(
            player,
            "passes_into_final_third",
            "Passes into final third"
        )

        if passes_into_final_third is None:
            passes_into_final_third = 0

        passes_into_final_third = (
            normalizar_numero(
                passes_into_final_third
            )
        )

        puntos_pases += (
            passes_into_final_third
            * 0.05
        )

        # ----------------------------------------------------
        # Pases largos precisos
        # ----------------------------------------------------

        long_balls_accurate = (
            stat_total_value(
                player,
                "long_balls_accurate",
                "Accurate long balls"
            )
        )

        if long_balls_accurate is None:
            long_balls_accurate = 0

        long_balls_accurate = (
            normalizar_numero(
                long_balls_accurate
            )
        )

        # ----------------------------------------------------
        # Centros precisos
        # ----------------------------------------------------

        accurate_crosses = (
            stat_total_value(
                player,
                "accurate_crosses",
                "Accurate crosses"
            )
        )

        if accurate_crosses is None:
            accurate_crosses = 0

        accurate_crosses = (
            normalizar_numero(
                accurate_crosses
            )
        )

        if position == "ARQ":

            puntos_pases += (
                long_balls_accurate
                * 0.10
            )

        else:

            puntos_pases += (
                long_balls_accurate
                * 0.05
            )

        puntos_pases += (
            accurate_crosses
            * 0.20
        )

        puntos_pases = min(
            puntos_pases,
            4.0
        )

        # ====================================================
        # PELIGRO CREADO
        # ====================================================

        shots_on_target = stat_value(
            player,
            "ShotsOnTarget",
            "shots_on_target",
            "Shots on target"
        )

        if shots_on_target is None:
            shots_on_target = 0

        goals = stat_value(
            player,
            "goals",
            "Goals"
        )

        if goals is None:
            goals = 0

        shots_on_target = normalizar_numero(
            shots_on_target
        )

        goals = normalizar_numero(
            goals
        )

        remates_arco_sin_gol = max(
            0,
            shots_on_target - goals
        )

        puntos_peligro = (
            remates_arco_sin_gol
            * 0.60
        )

        chances_created = (
            normalizar_numero(
                creation.get(
                    "chances_created"
                )
            )
        )

        # ----------------------------------------------------
        # ASISTENCIAS
        #
        # PitchAPI PLAYERS:
        # assists = asistencias
        #
        # Winning:
        # +3 puntos por asistencia.
        #
        # No diferenciamos entre asistencia intencional
        # y no intencional.
        # ----------------------------------------------------

        assists = stat_value(
            player,
            "assists",
            "Assists"
        )

        if assists is None:
            assists = 0

        assists = normalizar_numero(
            assists
        )

        # ----------------------------------------------------
        # PRE-ASISTENCIAS
        #
        # PitchAPI ADVANCED:
        # creation.second_assists
        #
        # Criterio confirmado para WINNING AI:
        # second_assists = pre-asistencia
        #
        # Winning:
        # +2 puntos por pre-asistencia.
        # ----------------------------------------------------

        second_assists = normalizar_numero(
            creation.get(
                "second_assists"
            )
        )

        # ----------------------------------------------------
        # PASES CLAVE SIN ASISTENCIA
        #
        # Las asistencias no vuelven a contar como pase clave.
        # second_assists NO se resta de chances_created porque
        # no es una asistencia normal.
        # ----------------------------------------------------

        pases_clave_sin_asistencia = max(
            0,
            chances_created - assists
        )

        puntos_peligro += (
            pases_clave_sin_asistencia
            * 0.50
        )

        big_chance_created = stat_value(
            player,
            "big_chance_created_team_title",
            "big_chance_created",
            "Big chances created"
        )

        if big_chance_created is None:
            big_chance_created = 0

        puntos_peligro += (
            normalizar_numero(
                big_chance_created
            )
            * 1.50
        )

        big_chance_missed = stat_value(
            player,
            "big_chance_missed_title",
            "big_chance_missed",
            "Big chances missed"
        )

        if big_chance_missed is None:
            big_chance_missed = 0

        puntos_peligro += (
            normalizar_numero(
                big_chance_missed
            )
            * -1.00
        )

        shots_woodwork = stat_value(
            player,
            "shots_woodwork",
            "Hit woodwork"
        )

        if shots_woodwork is None:
            shots_woodwork = 0

        puntos_peligro += (
            normalizar_numero(
                shots_woodwork
            )
            * 0.60
        )

        puntos_peligro += (
            take_ons_won
            * 0.60
        )

        missed_penalty = stat_value(
            player,
            "missed_penalty",
            "Missed penalty"
        )

        if missed_penalty is None:
            missed_penalty = 0

        puntos_peligro += (
            normalizar_numero(
                missed_penalty
            )
            * -4.00
        )

        offsides = stat_value(
            player,
            "offsides",
            "Offsides"
        )

        if offsides is None:
            offsides = 0

        puntos_peligro += (
            normalizar_numero(
                offsides
            )
            * -0.20
        )

        puntos_peligro = min(
            puntos_peligro,
            7.0
        )

        # ====================================================
        # DEFENSA
        # ====================================================

        tackles = (
            normalizar_numero(
                defending.get(
                    "tackles"
                )
            )
        )

        interceptions = (
            normalizar_numero(
                defending.get(
                    "interceptions"
                )
            )
        )

        clearances = (
            normalizar_numero(
                defending.get(
                    "clearances"
                )
            )
        )

        blocks = (
            normalizar_numero(
                defending.get(
                    "blocks"
                )
            )
        )

        recoveries = stat_value(
            player,
            "recoveries",
            "Recoveries"
        )

        if recoveries is None:
            recoveries = 0

        recoveries = normalizar_numero(
            recoveries
        )

        dribbled_past = stat_value(
            player,
            "dribbled_past",
            "Dribbled past"
        )

        if dribbled_past is None:
            dribbled_past = 0

        dribbled_past = normalizar_numero(
            dribbled_past
        )

        puntos_defensa = 0.0

        puntos_defensa += (
            tackles * 0.50
        )

        puntos_defensa += (
            interceptions * 0.40
        )

        puntos_defensa += (
            recoveries * 0.20
        )

        puntos_defensa += (
            clearances * 0.12
        )

        puntos_defensa += (
            blocks * 0.50
        )

        puntos_defensa -= (
            dribbled_past * 0.30
        )

        puntos_defensa = min(
            puntos_defensa,
            8.0
        )

        # ====================================================
        # ARQUERO
        # ====================================================

        saves = stat_value(
            player,
            "saves",
            "Saves"
        )

        if saves is None:
            saves = 0

        saved_penalties = stat_value(
            player,
            "saved_penalties",
            "Saved penalties"
        )

        if saved_penalties is None:
            saved_penalties = 0

        puntos_arquero = (
            normalizar_numero(
                saves
            )
            * 0.20
        )

        puntos_arquero += (
            normalizar_numero(
                saved_penalties
            )
            * 4.00
        )

        # ====================================================
        # GOLES / ASISTENCIAS
        #
        # Goles:
        #   normal        +6.0
        #   penal         +4.5
        #   autogol       -6.0
        #
        # Asistencias:
        #   asistencia    +3.0
        #
        # Pre-asistencias:
        #   second_assists +2.0
        #
        # Las asistencias y pre-asistencias se calculan aquí
        # porque tenemos acceso tanto a PLAYERS como a ADVANCED.
        # ====================================================

        goles_asistencias = (
            info_eventos[
                "goles_asistencias"
            ].get(
                player_id,
                0.0
            )
        )

        puntos_asistencias = (
            assists * 3.0
        )

        puntos_pre_asistencias = (
            second_assists * 2.0
        )

        goles_asistencias += (
            puntos_asistencias
            + puntos_pre_asistencias
        )

        # ====================================================
        # DISCIPLINA
        # ====================================================

        amarillas = (
            info_eventos[
                "amarillas"
            ].get(
                player_id,
                0
            )
        )

        segunda_amarilla = (
            info_eventos[
                "segunda_amarilla"
            ].get(
                player_id,
                0
            )
        )

        rojas_directas = (
            info_eventos[
                "rojas_directas"
            ].get(
                player_id,
                0
            )
        )

        puntos_disciplina = (
            amarillas * -1.0
        )

        puntos_disciplina += (
            segunda_amarilla * -2.0
        )

        puntos_disciplina += (
            rojas_directas * -3.0
        )

        # La segunda amarilla ya recibió -1 por la amarilla
        # y agrega -2 para completar -3.

        # ====================================================
        # RESULTADO
        # ====================================================

        (
            resultado_puntos,
            goles_contra,
            partido_finalizado
        ) = obtener_resultado(
            partido,
            team_id
        )

        # ====================================================
        # BONUS DE RESULTADO DEL JUGADOR
        # ====================================================

        bonus_resultado_jugador = (
            info_eventos[
                "bonus_resultado"
            ].get(
                player_id,
                0.0
            )
        )

        # ====================================================
        # VALLA INVICTA
        # ====================================================

        puntos_valla = 0.0

        if (
            partido_finalizado
            and minutes > 0
        ):

            factor_minutos = (
                minutes / 90.0
            )

            if position == "DEF":

                if goles_contra == 0:

                    puntos_valla += (
                        factor_minutos
                    )

                puntos_valla -= (
                    goles_contra
                    * 0.5
                )

            elif position == "ARQ":

                if goles_contra == 0:

                    puntos_valla += (
                        factor_minutos
                        * 2.0
                    )

                puntos_valla -= (
                    goles_contra
                )

        # ====================================================
        # TOTAL
        # ====================================================

        winning_total = (
            participacion
            + puntos_area
            + puntos_ultimo_tercio
            + puntos_carreras
            + puntos_duelos
            + puntos_perdidas
            + puntos_regates_fallidos
            + puntos_exceso_perdidas
            + puntos_pases
            + puntos_peligro
            + puntos_defensa
            + puntos_arquero
            + goles_asistencias
            + puntos_disciplina
            + resultado_puntos
            + bonus_resultado_jugador
            + puntos_valla
        )

        # ====================================================
        # EQUIPO
        # ====================================================

        home_team = partido.get(
            "home_team",
            {}
        )

        away_team = partido.get(
            "away_team",
            {}
        )

        if team_id == home_team.get("id"):

            team_name = home_team.get(
                "name",
                "Desconocido"
            )

        elif team_id == away_team.get("id"):

            team_name = away_team.get(
                "name",
                "Desconocido"
            )

        else:

            team_name = "Desconocido"

        # ====================================================
        # GUARDAR REGISTRO
        # ====================================================

        registros.append({

            "match_id": match_id,
            "date": partido.get("date"),
            "round_name": partido.get("round_name"),

            "player_id": player_id,
            "player_name": player_name,

            "team_id": team_id,
            "team_name": team_name,

            "position": position,
            "minutes_played": minutes,

            # PUNTOS
            "participacion": round(
                participacion,
                4
            ),

            "area_rival": round(
                puntos_area,
                4
            ),

            "ultimo_tercio": round(
                puntos_ultimo_tercio,
                4
            ),

            "carreras_progresivas": round(
                puntos_carreras,
                4
            ),

            "duelos": round(
                puntos_duelos,
                4
            ),

            "perdidas": round(
                puntos_perdidas,
                4
            ),

            "regates_fallidos": round(
                puntos_regates_fallidos,
                4
            ),

            "exceso_perdidas": round(
                puntos_exceso_perdidas,
                4
            ),

            "pases": round(
                puntos_pases,
                4
            ),

            "peligro_creado": round(
                puntos_peligro,
                4
            ),

            "defensa": round(
                puntos_defensa,
                4
            ),

            "arquero": round(
                puntos_arquero,
                4
            ),

            "goles_asistencias": round(
                goles_asistencias,
                4
            ),

            "disciplina": round(
                puntos_disciplina,
                4
            ),

            "resultado_puntos": round(
                resultado_puntos,
                4
            ),

            "bonus_resultado_jugador": round(
                bonus_resultado_jugador,
                4
            ),

            "valla_invicta": round(
                puntos_valla,
                4
            ),

            "winning_total": round(
                winning_total,
                4
            ),

            # DATOS CRUDOS
            "accurate_passes": accurate_passes,
            "passes": passes,
            "progressive_passes": progressive_passes,
            "precision_pases": round(
                precision,
                4
            ),

            "passes_into_final_third":
                passes_into_final_third,

            "long_balls_accurate":
                long_balls_accurate,

            "accurate_crosses":
                accurate_crosses,

            "progressive_carries":
                progressive_carries,

            "take_ons": take_ons,
            "take_ons_won": take_ons_won,
            "failed_dribbles": failed_dribbles,

            "miscontrols": miscontrols,
            "dispossessed": dispossessed,

            "duels_won": duels_won,
            "duels_lost": duels_lost,

            "tackles": tackles,
            "interceptions": interceptions,
            "recoveries": recoveries,
            "clearances": clearances,
            "blocks": blocks,
            "dribbled_past": dribbled_past,

            "shots_on_target": shots_on_target,
            "goals": goals,
            "assists": assists,
            "second_assists": second_assists,
            "chances_created": chances_created,

            "saves": saves,
            "saved_penalties": saved_penalties,

            "goals_conceded": goles_contra,

            "yellow_cards": amarillas,
            "second_yellow": segunda_amarilla,
            "red_cards_direct": rojas_directas,

            "match_finished":
                partido_finalizado
        })

    partidos_procesados += 1

    if partidos_procesados % 50 == 0:

        print(
            f"Procesados: "
            f"{partidos_procesados} partidos"
        )


# ============================================================
# RESULTADO
# ============================================================

print()
print("=" * 100)
print("RESULTADO")
print("=" * 100)
print()

print(
    f"Registros: {len(registros)}"
)

print(
    f"Jugadores únicos: "
    f"{len(set(r['player_id'] for r in registros))}"
)

print(
    f"Partidos: "
    f"{len(set(r['match_id'] for r in registros))}"
)


# ============================================================
# PROMEDIO
# ============================================================

if registros:

    promedio = (
        sum(
            r["winning_total"]
            for r in registros
        )
        / len(registros)
    )

else:

    promedio = 0.0


print()
print("PROMEDIO WINNING:")
print(
    f"{promedio:.4f}"
)


# ============================================================
# TOP 20
# ============================================================

print()
print("TOP 20 ACTUACIONES:")

ordenados = sorted(
    registros,
    key=lambda x: x["winning_total"],
    reverse=True
)


for r in ordenados[:20]:

    print(
        f"{r['player_name']:<30} "
        f"{r['team_name']:<28} "
        f"{r['position']:<6} "
        f"min={r['minutes_played']:>5.0f} "
        f"pases={r['pases']:>6.2f} "
        f"peligro={r['peligro_creado']:>6.2f} "
        f"defensa={r['defensa']:>6.2f} "
        f"g/a={r['goles_asistencias']:>5.2f} "
        f"disc={r['disciplina']:>5.2f} "
        f"res={r['resultado_puntos']:>4.1f} "
        f"bonus={r['bonus_resultado_jugador']:>4.1f} "
        f"TOTAL={r['winning_total']:>6.2f}"
    )


# ============================================================
# GUARDAR CSV
# ============================================================

DATOS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

if registros:

    campos = list(
        registros[0].keys()
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=campos
        )

        writer.writeheader()
        writer.writerows(registros)


print()
print(
    f"Archivo generado: {OUTPUT_FILE}"
)