import json
import glob
import csv
import os


ARCHIVOS = glob.glob("datos/partidos/*.json")
SALIDA = "datos/dataset_jugadores.csv"


def obtener_resultado(evento, es_local):

    winner_code = evento.get("winnerCode")

    if winner_code == 3:
        return "W" if es_local else "L"

    if winner_code == 1:
        return "D"

    if winner_code == 2:
        return "L" if es_local else "W"

    return None


def obtener_valor(stats, campo):

    valor = stats.get(campo)

    if valor is None:
        return None

    return valor


def obtener_tarjetas(incidentes, player_id):

    yellow = 0
    red = 0
    yellow_red = 0

    for incidente in incidentes:

        if incidente.get("incidentType") != "card":
            continue

        if incidente.get("rescinded"):
            continue

        jugador = incidente.get("player") or {}

        if jugador.get("id") != player_id:
            continue

        clase = incidente.get("incidentClass")

        if clase == "yellow":
            yellow += 1

        elif clase == "red":
            red += 1

        elif clase == "yellowRed":
            yellow_red += 1

    if yellow_red > 0:

        yellow_normales = max(0, yellow - yellow_red)

        discipline_points = (
            yellow_normales * -1
            + yellow_red * -3
            + red * -3
        )

    else:

        discipline_points = (
            yellow * -1
            + red * -3
        )

    return yellow, red, yellow_red, discipline_points


def obtener_goles_mientras_jugaba(incidentes, lineups):

    participacion = {}

    # =========================================================
    # 1. TITULARES
    # =========================================================

    for lado in ["home", "away"]:

        es_local = lado == "home"

        jugadores = lineups.get(lado, {}).get("players", [])

        for registro in jugadores:

            if registro.get("substitute"):
                continue

            jugador = registro.get("player") or {}
            player_id = jugador.get("id")

            if not player_id:
                continue

            participacion[player_id] = {
                "es_local": es_local,
                "entrada": 0,
                "entrada_indice": -1,
                "salida": None,
                "salida_indice": None,
            }

    # =========================================================
    # 2. SUSTITUCIONES
    # =========================================================

    for indice, incidente in enumerate(incidentes):

        if incidente.get("incidentType") != "substitution":
            continue

        player_in = incidente.get("playerIn") or {}
        player_out = incidente.get("playerOut") or {}

        id_in = player_in.get("id")
        id_out = player_out.get("id")

        minuto = incidente.get("time")
        es_local = incidente.get("isHome")

        if id_out:

            if id_out not in participacion:

                participacion[id_out] = {
                    "es_local": es_local,
                    "entrada": 0,
                    "entrada_indice": -1,
                    "salida": minuto,
                    "salida_indice": indice,
                }

            else:

                participacion[id_out]["salida"] = minuto
                participacion[id_out]["salida_indice"] = indice

        if id_in:

            participacion[id_in] = {
                "es_local": es_local,
                "entrada": minuto,
                "entrada_indice": indice,
                "salida": None,
                "salida_indice": None,
            }

    # =========================================================
    # 3. GOLES RECIBIDOS MIENTRAS ESTABA EN CANCHA
    # =========================================================

    goles_por_jugador = {
        player_id: 0
        for player_id in participacion
    }

    for indice, incidente in enumerate(incidentes):

        if incidente.get("incidentType") != "goal":
            continue

        es_local = incidente.get("isHome")
        minuto = incidente.get("time")

        equipo_que_recibe = not es_local

        for player_id, jugador in participacion.items():

            if jugador["es_local"] != equipo_que_recibe:
                continue

            entrada = jugador["entrada"]
            entrada_indice = jugador["entrada_indice"]

            salida = jugador["salida"]
            salida_indice = jugador["salida_indice"]

            estaba_jugando = True

            if minuto < entrada:

                estaba_jugando = False

            elif minuto == entrada and entrada_indice >= 0:

                if indice < entrada_indice:
                    estaba_jugando = False

            if salida is not None:

                if minuto > salida:

                    estaba_jugando = False

                elif minuto == salida:

                    if indice > salida_indice:
                        estaba_jugando = False

            if estaba_jugando:

                goles_por_jugador[player_id] += 1

    # =========================================================
    # 4. CLEAN SHEET
    # =========================================================

    resultado = {}

    for player_id in participacion:

        goles_recibidos = goles_por_jugador[player_id]

        resultado[player_id] = {
            "goals_conceded": goles_recibidos,
            "clean_sheet": goles_recibidos == 0,
        }

    return resultado


def construir_participacion(lineups, incidentes):

    participacion = {}

    # =========================================================
    # TITULARES
    # =========================================================

    for lado in ["home", "away"]:

        es_local = lado == "home"

        jugadores = lineups.get(lado, {}).get("players", [])

        for registro in jugadores:

            if registro.get("substitute"):
                continue

            jugador = registro.get("player") or {}
            player_id = jugador.get("id")

            if not player_id:
                continue

            participacion[player_id] = {
                "es_local": es_local,
                "entrada": 0,
                "entrada_indice": -1,
                "salida": None,
                "salida_indice": None,
            }

    # =========================================================
    # SUSTITUCIONES
    # =========================================================

    for indice, incidente in enumerate(incidentes):

        if incidente.get("incidentType") != "substitution":
            continue

        player_in = incidente.get("playerIn") or {}
        player_out = incidente.get("playerOut") or {}

        id_in = player_in.get("id")
        id_out = player_out.get("id")

        minuto = incidente.get("time")
        es_local = incidente.get("isHome")

        if id_out:

            if id_out not in participacion:

                participacion[id_out] = {
                    "es_local": es_local,
                    "entrada": 0,
                    "entrada_indice": -1,
                    "salida": minuto,
                    "salida_indice": indice,
                }

            else:

                participacion[id_out]["salida"] = minuto
                participacion[id_out]["salida_indice"] = indice

        if id_in:

            participacion[id_in] = {
                "es_local": es_local,
                "entrada": minuto,
                "entrada_indice": indice,
                "salida": None,
                "salida_indice": None,
            }

    return participacion


def estaba_en_cancha(info, minuto, indice_incidente):

    entrada = info["entrada"]
    entrada_indice = info["entrada_indice"]

    salida = info["salida"]
    salida_indice = info["salida_indice"]

    if minuto < entrada:
        return False

    if minuto == entrada and entrada_indice >= 0:

        if indice_incidente >= 0 and indice_incidente < entrada_indice:
            return False

    if salida is not None:

        if minuto > salida:
            return False

        if minuto == salida:

            if (
                indice_incidente >= 0
                and indice_incidente > salida_indice
            ):
                return False

    return True


def recorrer_acciones(objeto):

    """
    Recorre recursivamente el JSON buscando
    objetos footballPassingNetworkAction.
    """

    if isinstance(objeto, dict):

        for clave, valor in objeto.items():

            if clave == "footballPassingNetworkAction":

                if isinstance(valor, list):

                    for accion in valor:
                        yield accion

                elif isinstance(valor, dict):

                    yield valor

            yield from recorrer_acciones(valor)

    elif isinstance(objeto, list):

        for elemento in objeto:

            yield from recorrer_acciones(elemento)


def obtener_atajas(datos, lineups, incidentes):

    """
    Busca eventos save de SofaScore y determina
    qué arquero realizó cada atajada.

    SofaScore identifica al jugador que realizó el remate
    en el evento save. El arquero se determina como el
    arquero del equipo contrario que estaba en cancha.
    """

    participacion = construir_participacion(
        lineups,
        incidentes
    )

    # =========================================================
    # ARQUEROS
    # =========================================================

    arqueros = {}

    for lado in ["home", "away"]:

        es_local = lado == "home"

        jugadores = lineups.get(lado, {}).get("players", [])

        for registro in jugadores:

            jugador = registro.get("player") or {}

            player_id = jugador.get("id")

            if not player_id:
                continue

            posicion = registro.get("position")

            if posicion != "G":
                continue

            arqueros[player_id] = {
                "es_local": es_local,
                "player_id": player_id,
            }

    # =========================================================
    # CONTADORES
    # =========================================================

    saves = {
        player_id: 0
        for player_id in arqueros
    }

    saves_procesados = set()

    # =========================================================
    # BUSCAR SAVE
    # =========================================================

    for accion in recorrer_acciones(datos):

        if not isinstance(accion, dict):
            continue

        if accion.get("eventType") != "save":
            continue

        minuto = accion.get("time")

        es_local_rematador = accion.get("isHome")

        jugador_rematador = accion.get("player") or {}

        rematador_id = jugador_rematador.get("id")

        if minuto is None:
            continue

        # El arquero pertenece al equipo contrario
        # al jugador que realizó el remate.

        equipo_arquero = not es_local_rematador

        arquero_en_cancha = None

        for player_id, info_arquero in arqueros.items():

            if info_arquero["es_local"] != equipo_arquero:
                continue

            info_participacion = participacion.get(player_id)

            if not info_participacion:
                continue

            if estaba_en_cancha(
                info_participacion,
                minuto,
                -1
            ):
                arquero_en_cancha = player_id
                break

        if arquero_en_cancha is None:
            continue

        # =====================================================
        # EVITAR DUPLICADOS
        # =====================================================

        clave = (
            arquero_en_cancha,
            rematador_id,
            minuto
        )

        if clave in saves_procesados:
            continue

        saves_procesados.add(clave)

        saves[arquero_en_cancha] += 1

    return saves


def obtener_goles_penal(incidentes):

    """
    Detecta cuántos goles de penal convirtió cada jugador.

    SofaScore identifica estos goles mediante:

        incidentClass == "penalty"
        from == "penalty"

    y en footballPassingNetworkAction:

        goalType == "penalty"
        situation == "penalty"
    """

    penalty_goals = {}

    for incidente in incidentes:

        if incidente.get("incidentType") != "goal":
            continue

        jugador = incidente.get("player") or {}
        player_id = jugador.get("id")

        if not player_id:
            continue

        es_penal = False

        # -----------------------------------------------------
        # Método principal: incidente
        # -----------------------------------------------------

        if incidente.get("incidentClass") == "penalty":
            es_penal = True

        if incidente.get("from") == "penalty":
            es_penal = True

        # -----------------------------------------------------
        # Método adicional: footballPassingNetworkAction
        # -----------------------------------------------------

        acciones = incidente.get(
            "footballPassingNetworkAction",
            []
        )

        if isinstance(acciones, dict):
            acciones = [acciones]

        for accion in acciones:

            if not isinstance(accion, dict):
                continue

            if accion.get("eventType") != "goal":
                continue

            if accion.get("goalType") == "penalty":
                es_penal = True

            if accion.get("situation") == "penalty":
                es_penal = True

        if es_penal:

            penalty_goals[player_id] = (
                penalty_goals.get(player_id, 0) + 1
            )

    return penalty_goals


# =============================================================
# CREAR DATASET
# =============================================================

filas = []


for archivo in ARCHIVOS:

    with open(
        archivo,
        "r",
        encoding="utf-8"
    ) as f:

        datos = json.load(f)

    evento = datos["event"]["event"]

    lineups = datos.get(
        "lineups",
        {}
    )

    incidentes = datos.get(
        "incidents",
        {}
    ).get(
        "incidents",
        []
    )

    # =========================================================
    # GOLES RECIBIDOS / CLEAN SHEET
    # =========================================================

    goles_mientras_jugaba = obtener_goles_mientras_jugaba(
        incidentes,
        lineups
    )

    # =========================================================
    # ATAJADAS
    # =========================================================

    saves_por_jugador = obtener_atajas(
        datos,
        lineups,
        incidentes
    )

    # =========================================================
    # GOLES DE PENAL
    # =========================================================

    penalty_goals_por_jugador = obtener_goles_penal(
        incidentes
    )

    partido_id = evento.get("id")

    home_team = evento.get(
        "homeTeam",
        {}
    )

    away_team = evento.get(
        "awayTeam",
        {}
    )

    home_team_id = home_team.get("id")
    away_team_id = away_team.get("id")

    home_team_name = home_team.get("name")
    away_team_name = away_team.get("name")

    home_score = evento.get(
        "homeScore",
        {}
    ).get("current")

    away_score = evento.get(
        "awayScore",
        {}
    ).get("current")

    status = evento.get(
        "status",
        {}
    )

    status_type = status.get("type")

    # =========================================================
    # JUGADORES
    # =========================================================

    for lado in ["home", "away"]:

        es_local = lado == "home"

        equipo = lineups.get(
            lado,
            {}
        )

        jugadores = equipo.get(
            "players",
            []
        )

        team_id = (
            home_team_id
            if es_local
            else away_team_id
        )

        team_name = (
            home_team_name
            if es_local
            else away_team_name
        )

        resultado = obtener_resultado(
            evento,
            es_local
        )

        for registro in jugadores:

            jugador = registro.get(
                "player"
            ) or {}

            stats = registro.get(
                "statistics"
            ) or {}

            player_id = jugador.get("id")

            yellow, red, yellow_red, discipline_points = obtener_tarjetas(
                incidentes,
                player_id
            )

            datos_goles = goles_mientras_jugaba.get(
                player_id,
                {
                    "goals_conceded": 0,
                    "clean_sheet": False,
                }
            )

            goles_recibidos = datos_goles.get(
                "goals_conceded",
                0
            )

            clean_sheet = datos_goles.get(
                "clean_sheet",
                False
            )

            saves = saves_por_jugador.get(
                player_id,
                0
            )

            penalty_goals = penalty_goals_por_jugador.get(
                player_id,
                0
            )

            fila = {

                # =================================================
                # PARTIDO
                # =================================================

                "match_id": partido_id,

                "status_type": status_type,

                # =================================================
                # EQUIPO
                # =================================================

                "team_id": team_id,

                "team_name": team_name,

                "is_home": es_local,

                # =================================================
                # RESULTADO
                # =================================================

                "result": resultado,

                "home_score": home_score,

                "away_score": away_score,

                # =================================================
                # JUGADOR
                # =================================================

                "player_id": player_id,

                "player_name": jugador.get("name"),

                "position": registro.get("position"),

                "substitute": registro.get("substitute"),

                # =================================================
                # PARTICIPACION
                # =================================================

                "minutesPlayed": obtener_valor(
                    stats,
                    "minutesPlayed"
                ),

                # =================================================
                # RATING
                # =================================================

                "rating": obtener_valor(
                    stats,
                    "rating"
                ),

                # =================================================
                # ATAQUE
                # =================================================

                "goals": obtener_valor(
                    stats,
                    "goals"
                ),

                "penalty_goals": penalty_goals,

                "goalAssist": obtener_valor(
                    stats,
                    "goalAssist"
                ),

                "expectedGoals": obtener_valor(
                    stats,
                    "expectedGoals"
                ),

                "expectedAssists": obtener_valor(
                    stats,
                    "expectedAssists"
                ),

                "totalShots": obtener_valor(
                    stats,
                    "totalShots"
                ),

                "onTargetScoringAttempt": obtener_valor(
                    stats,
                    "onTargetScoringAttempt"
                ),

                "bigChanceCreated": obtener_valor(
                    stats,
                    "bigChanceCreated"
                ),

                "bigChanceMissed": obtener_valor(
                    stats,
                    "bigChanceMissed"
                ),

                "keyPass": obtener_valor(
                    stats,
                    "keyPass"
                ),

                "hitWoodwork": obtener_valor(
                    stats,
                    "hitWoodwork"
                ),

                # =================================================
                # REGATES / DUELOS
                # =================================================

                "duelWon": obtener_valor(
                    stats,
                    "duelWon"
                ),

                "duelLost": obtener_valor(
                    stats,
                    "duelLost"
                ),

                "unsuccessfulTouch": obtener_valor(
                    stats,
                    "unsuccessfulTouch"
                ),

                "dispossessed": obtener_valor(
                    stats,
                    "dispossessed"
                ),

                "progressiveBallCarriesCount": obtener_valor(
                    stats,
                    "progressiveBallCarriesCount"
                ),

                "ballCarriesCount": obtener_valor(
                    stats,
                    "ballCarriesCount"
                ),

                # =================================================
                # ERRORES
                # =================================================

                "errorLeadToAShot": obtener_valor(
                    stats,
                    "errorLeadToAShot"
                ),

                "errorLeadToAGoal": obtener_valor(
                    stats,
                    "errorLeadToAGoal"
                ),

                # =================================================
                # DEFENSA
                # =================================================

                "wonTackle": obtener_valor(
                    stats,
                    "wonTackle"
                ),

                "interceptionWon": obtener_valor(
                    stats,
                    "interceptionWon"
                ),

                "ballRecovery": obtener_valor(
                    stats,
                    "ballRecovery"
                ),

                "totalClearance": obtener_valor(
                    stats,
                    "totalClearance"
                ),

                "blockedScoringAttempt": obtener_valor(
                    stats,
                    "blockedScoringAttempt"
                ),

                # =================================================
                # PASES
                # =================================================

                "accuratePass": obtener_valor(
                    stats,
                    "accuratePass"
                ),

                "totalPass": obtener_valor(
                    stats,
                    "totalPass"
                ),

                "accurateLongBalls": obtener_valor(
                    stats,
                    "accurateLongBalls"
                ),

                "totalLongBalls": obtener_valor(
                    stats,
                    "totalLongBalls"
                ),

                "accurateCross": obtener_valor(
                    stats,
                    "accurateCross"
                ),

                "totalCross": obtener_valor(
                    stats,
                    "totalCross"
                ),

                "accurateOppositionHalfPasses": obtener_valor(
                    stats,
                    "accurateOppositionHalfPasses"
                ),

                # =================================================
                # DISCIPLINA
                # =================================================

                "yellow_card": yellow,

                "red_card": red,

                "yellow_red": yellow_red,

                "discipline_points": discipline_points,

                "fouls": obtener_valor(
                    stats,
                    "fouls"
                ),

                "wasFouled": obtener_valor(
                    stats,
                    "wasFouled"
                ),

                "penaltyWon": obtener_valor(
                    stats,
                    "penaltyWon"
                ),

                "penaltyConceded": obtener_valor(
                    stats,
                    "penaltyConceded"
                ),

                "penaltyMiss": obtener_valor(
                    stats,
                    "penaltyMiss"
                ),

                # =================================================
                # OTROS
                # =================================================

                "possessionLostCtrl": obtener_valor(
                    stats,
                    "possessionLostCtrl"
                ),

                "aerialWon": obtener_valor(
                    stats,
                    "aerialWon"
                ),

                "aerialLost": obtener_valor(
                    stats,
                    "aerialLost"
                ),

                "challengeLost": obtener_valor(
                    stats,
                    "challengeLost"
                ),

                "outfielderBlock": obtener_valor(
                    stats,
                    "outfielderBlock"
                ),

                "clearanceOffLine": obtener_valor(
                    stats,
                    "clearanceOffLine"
                ),

                "ownGoals": obtener_valor(
                    stats,
                    "ownGoals"
                ),

                "totalOffside": obtener_valor(
                    stats,
                    "totalOffside"
                ),

                # =================================================
                # ARQUERO
                # =================================================

                "saves": saves,

                # =================================================
                # DEFENSA CALCULADA
                # =================================================

                "team_clean_sheet": clean_sheet,

                "goals_conceded_while_playing": goles_recibidos,
            }

            filas.append(fila)


# =============================================================
# GUARDAR CSV
# =============================================================

os.makedirs(
    os.path.dirname(SALIDA),
    exist_ok=True
)


if filas:

    columnas = list(
        filas[0].keys()
    )

    with open(
        SALIDA,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=columnas
        )

        writer.writeheader()

        writer.writerows(filas)


print()
print("DATASET CREADO")
print(
    "Partidos procesados:",
    len(ARCHIVOS)
)
print(
    "Registros de jugadores:",
    len(filas)
)
print(
    "Archivo:",
    SALIDA
)
print(
    "Columnas:",
    len(filas[0]) if filas else 0
)

print()

total_saves = sum(
    fila.get("saves", 0)
    for fila in filas
)

arqueros_con_saves = sum(
    1
    for fila in filas
    if fila.get("saves", 0) > 0
)

total_penalty_goals = sum(
    fila.get("penalty_goals", 0)
    for fila in filas
)

jugadores_con_penalty_goals = sum(
    1
    for fila in filas
    if fila.get("penalty_goals", 0) > 0
)

print(
    "Atajadas detectadas:",
    total_saves
)

print(
    "Arqueros con al menos una atajada:",
    arqueros_con_saves
)

print(
    "Goles de penal detectados:",
    total_penalty_goals
)

print(
    "Jugadores con al menos un gol de penal:",
    jugadores_con_penalty_goals
)