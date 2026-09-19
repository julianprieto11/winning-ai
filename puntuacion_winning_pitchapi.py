import json
import csv
from pathlib import Path


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATOS_DIR = BASE_DIR / "datos"
PITCHAPI_DIR = DATOS_DIR / "pitchapi"

OUTPUT_FILE = DATOS_DIR / "dataset_winning_pitchapi.csv"


# ============================================================
# UTILIDADES
# ============================================================

def cargar_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


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
    f"Archivos players: {len(players_por_partido)}"
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
    f"Archivos advanced: {len(advanced_por_partido)}"
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

    eventos = data.get(
        "data",
        []
    )

    if isinstance(eventos, dict):

        eventos = eventos.get(
            "events",
            []
        )

    if not isinstance(eventos, list):
        eventos = []

    events_por_partido[match_id] = eventos


print(
    f"Archivos events: {len(events_por_partido)}"
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
        #
        # IMPORTANTE:
        # Los minutos NO están en:
        #
        # player["minutes_played"]
        #
        # Están en:
        #
        # stats -> Minutes played -> stat -> value
        #

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
        # POSICIÓN
        # ====================================================
        #
        # Se incorporará desde SofaScore.
        #

        position = None

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

        puntos_ultimo_tercio = 0.0

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
        # ====================================================

        puntos_exceso_perdidas = 0.0

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

        if position == "G":

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

        puntos_arquero = 0.0

        # ====================================================
        # GOLES / ASISTENCIAS
        # ====================================================

        goles_asistencias = 0.0

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

            if position == "D":

                if goles_contra == 0:

                    puntos_valla += (
                        factor_minutos
                    )

                puntos_valla -= (
                    goles_contra
                    * 0.5
                )

            elif position == "G":

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
            + resultado_puntos
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

            "resultado_puntos": round(
                resultado_puntos,
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
            "chances_created": chances_created,

            "saves": saves,
            "saved_penalties": saved_penalties,

            "goals_conceded": goles_contra,

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
        f"min={r['minutes_played']:>5.0f} "
        f"pases={r['pases']:>6.2f} "
        f"peligro={r['peligro_creado']:>6.2f} "
        f"defensa={r['defensa']:>6.2f} "
        f"resultado={r['resultado_puntos']:>4.1f} "
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