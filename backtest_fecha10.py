import json
import glob
import os
import random
import numpy as np
import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================

FECHA_OBJETIVO = 10
COMPETENCIA_OBJETIVO = "Clausura"

# Último partido histórico disponible antes de Fecha 10:
# 15/09/2026
CORTE_HISTORICO = pd.Timestamp("2026-09-16")

HISTORICO_FILE = "datos/dataset_winning_pitchapi.csv"

CONTEXTO_EQUIPOS_FILE = "datos/contexto_equipos.csv"
FORMA_RECIENTE_FILE = "datos/forma_reciente_equipos.csv"
FORMA_LOCAL_VISITANTE_FILE = "datos/forma_local_visitante_equipos.csv"
RENDIMIENTO_RECIENTE_FILE = "datos/rendimiento_reciente_equipos.csv"

LINEUPS_DIR = "datos/pitchapi/lineups"
PARTIDOS_DIR = "datos/partidos"

SALIDA_CANDIDATOS = "datos/candidatos_fecha10_final.csv"
SALIDA_EQUIPOS = "datos/fecha10_equipos_predichos.csv"
SALIDA_EQUIPOS_EXCEL = "datos/fecha10_equipos_predichos_excel.csv"
SALIDA_SIMULACIONES = "datos/fecha10_simulaciones.csv"

N_SIMULACIONES = 10000

# ============================================================
# DIVERSIDAD ENTRE LOS 3 EQUIPOS
# ============================================================

PENALIZACION_REPETICION = {
    "SEGURO": 0.00,
    "INTERMEDIO": 0.18,
    "ARRIESGADO": 0.28,
}

# ============================================================
# FLEX
# ============================================================

# Si un jugador ya fue utilizado como FLEX en un equipo,
# NO puede volver a aparecer como FLEX en otro equipo.

# Si ya fue titular del MISMO equipo que estamos armando FLEX,
# no se bloquea: recibe una penalización fuerte.
PENALIZACION_FLEX_TITULAR_MISMO = 0.70

# Si fue titular de otro de los equipos, recibe una
# penalización dependiendo del perfil.
PENALIZACION_FLEX_TITULAR_OTRO = {
    "SEGURO": 0.00,
    "INTERMEDIO": 0.18,
    "ARRIESGADO": 0.30,
}

# ============================================================
# UTILIDADES
# ============================================================

def normalizar_texto(valor):

    if pd.isna(valor):
        return ""

    return str(valor).strip().lower()


def convertir_fecha(valor):

    try:
        return pd.to_datetime(valor)
    except Exception:
        return pd.NaT


def safe_float(valor, default=0.0):

    try:

        if pd.isna(valor):
            return default

        return float(valor)

    except Exception:

        return default


# ============================================================
# CARGAR PARTIDOS FECHA 10 DESDE SOFASCORE
# ============================================================

def cargar_partidos_fecha10():

    partidos = []

    archivos = glob.glob(
        os.path.join(
            PARTIDOS_DIR,
            "*.json"
        )
    )

    for archivo in archivos:

        try:

            with open(
                archivo,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

        except Exception:

            continue

        event = data.get(
            "event",
            {}
        ).get(
            "event",
            data
        )

        round_info = event.get(
            "roundInfo",
            {}
        ) or {}

        round_num = round_info.get(
            "round"
        )

        if round_num != FECHA_OBJETIVO:
            continue

        torneo = event.get(
            "tournament",
            {}
        ) or {}

        temporada = event.get(
            "season",
            {}
        ) or {}

        texto_competencia = (
            str(
                torneo.get(
                    "name",
                    ""
                )
            )
            + " "
            +
            str(
                temporada.get(
                    "name",
                    ""
                )
            )
        ).lower()

        if (
            COMPETENCIA_OBJETIVO.lower()
            not in texto_competencia
        ):

            continue

        partidos.append(
            {
                "sofascore_id": str(
                    event.get("id")
                ),

                "fecha": pd.to_datetime(
                    event.get(
                        "startTimestamp"
                    ),
                    unit="s",
                    errors="coerce",
                ),

                "home_team_id": str(
                    (
                        event.get(
                            "homeTeam"
                        )
                        or {}
                    ).get(
                        "id",
                        ""
                    )
                ),

                "home_team_name": (
                    (
                        event.get(
                            "homeTeam"
                        )
                        or {}
                    ).get(
                        "name",
                        ""
                    )
                ),

                "away_team_id": str(
                    (
                        event.get(
                            "awayTeam"
                        )
                        or {}
                    ).get(
                        "id",
                        ""
                    )
                ),

                "away_team_name": (
                    (
                        event.get(
                            "awayTeam"
                        )
                        or {}
                    ).get(
                        "name",
                        ""
                    )
                ),
            }
        )

    df = pd.DataFrame(partidos)

    if df.empty:

        print(
            "ERROR: no se encontraron partidos de Fecha 10."
        )

        return df

    df = (
        df
        .sort_values("fecha")
        .reset_index(drop=True)
    )

    print()
    print("=" * 70)
    print(
        "PARTIDOS FECHA 10 ENCONTRADOS:",
        len(df)
    )
    print("=" * 70)

    for _, fila in df.iterrows():

        print(
            fila["fecha"].strftime("%d/%m/%Y")
            if not pd.isna(
                fila["fecha"]
            )
            else "SIN FECHA",

            "|",

            fila["home_team_name"],

            "-",

            fila["away_team_name"],

            "| SofaScore:",

            fila["sofascore_id"],
        )

    return df


# ============================================================
# MAPEO SOFASCORE -> PITCHAPI
# ============================================================

MAPEO_PITCHAPI = {

    "16667329": "m_2S2kkL",
    "16667338": "m_1ABSM7",
    "16667328": "m_1rGQaB",
    "16667336": "m_11PYwu",
    "16667325": "m_17fjdr",
    "16667327": "m_0Z63wJ",
    "16667333": "m_0BTFn7",
    "16667340": "m_0jdOYm",
    "16667330": "m_2EhjDn",
    "16667332": "m_0sbdux",
    "16667326": "m_0MCwqI",
    "16671623": "m_0el541",
    "16667335": "m_0bU15M",
    "16667331": "m_0MXtuT",
    "16667337": "m_0Feldm",
}


# ============================================================
# CARGAR LINEUPS PITCHAPI
# ============================================================

def cargar_lineups_fecha10():

    lineups = {}

    archivos = glob.glob(
        os.path.join(
            LINEUPS_DIR,
            "*_lineups.json"
        )
    )

    ids_objetivo = set(
        MAPEO_PITCHAPI.values()
    )

    for archivo in archivos:

        nombre = os.path.basename(
            archivo
        )

        match_id = nombre.replace(
            "_lineups.json",
            ""
        )

        if match_id not in ids_objetivo:
            continue

        try:

            with open(
                archivo,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

        except Exception:

            continue

        data = data.get(
            "data",
            {}
        )

        if not data:
            continue

        lineups[match_id] = data

    print()
    print("=" * 70)
    print(
        "LINEUPS FECHA 10:",
        len(lineups)
    )
    print("=" * 70)

    for match_id in sorted(lineups):

        data = lineups[match_id]

        print(
            match_id,
            "|",
            data.get(
                "home_team",
                {}
            ).get(
                "name",
                ""
            ),
            "-",
            data.get(
                "away_team",
                {}
            ).get(
                "name",
                ""
            ),
        )

    return lineups


# ============================================================
# CONSTRUIR MAPA DE JUGADORES FECHA 10
# ============================================================

def construir_jugadores_objetivo(
    lineups
):

    jugadores = {}

    for match_id, data in lineups.items():

        for lado in [
            "home",
            "away"
        ]:

            equipo = data.get(
                f"{lado}_team",
                {}
            ) or {}

            team_id = str(
                equipo.get(
                    "id",
                    ""
                )
            )

            team_name = equipo.get(
                "name",
                ""
            )

            bloque = data.get(
                lado,
                {}
            ) or {}

            starters = bloque.get(
                "starters",
                []
            ) or []

            subs = bloque.get(
                "subs",
                []
            ) or []

            for jugador in starters:

                player_id = str(
                    jugador.get(
                        "player_id",
                        ""
                    )
                )

                if not player_id:
                    continue

                jugadores[player_id] = {

                    "player_id": player_id,

                    "player_name": jugador.get(
                        "name",
                        ""
                    ),

                    "team_id": team_id,

                    "team_name": team_name,

                    "match_id_fecha10": match_id,

                    "starter_fecha10": True,
                }

            for jugador in subs:

                player_id = str(
                    jugador.get(
                        "player_id",
                        ""
                    )
                )

                if not player_id:
                    continue

                if player_id not in jugadores:

                    jugadores[player_id] = {

                        "player_id": player_id,

                        "player_name": jugador.get(
                            "name",
                            ""
                        ),

                        "team_id": team_id,

                        "team_name": team_name,

                        "match_id_fecha10": match_id,

                        "starter_fecha10": False,
                    }

    return jugadores


# ============================================================
# MAPA DE TITULARIDADES HISTÓRICAS
# ============================================================

def construir_mapa_lineups_historicos():

    mapa = {}

    archivos = glob.glob(
        os.path.join(
            LINEUPS_DIR,
            "*_lineups.json"
        )
    )

    for archivo in archivos:

        nombre = os.path.basename(
            archivo
        )

        match_id = nombre.replace(
            "_lineups.json",
            ""
        )

        try:

            with open(
                archivo,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f).get(
                    "data",
                    {}
                )

        except Exception:

            continue

        if not data:
            continue

        for lado in [
            "home",
            "away"
        ]:

            equipo = data.get(
                f"{lado}_team",
                {}
            ) or {}

            team_id = str(
                equipo.get(
                    "id",
                    ""
                )
            )

            team_name = equipo.get(
                "name",
                ""
            )

            bloque = data.get(
                lado,
                {}
            ) or {}

            starters = bloque.get(
                "starters",
                []
            ) or []

            subs = bloque.get(
                "subs",
                []
            ) or []

            for jugador in starters:

                player_id = str(
                    jugador.get(
                        "player_id",
                        ""
                    )
                )

                if not player_id:
                    continue

                mapa[
                    (
                        match_id,
                        player_id
                    )
                ] = {

                    "starter": True,

                    "team_id": team_id,

                    "team_name": team_name,
                }

            for jugador in subs:

                player_id = str(
                    jugador.get(
                        "player_id",
                        ""
                    )
                )

                if not player_id:
                    continue

                if (
                    match_id,
                    player_id
                ) not in mapa:

                    mapa[
                        (
                            match_id,
                            player_id
                        )
                    ] = {

                        "starter": False,

                        "team_id": team_id,

                        "team_name": team_name,
                    }

    return mapa


# ============================================================
# CARGAR CONTEXTOS
# ============================================================

def cargar_contextos():

    contexto = pd.read_csv(
        CONTEXTO_EQUIPOS_FILE
    )

    forma = pd.read_csv(
        FORMA_RECIENTE_FILE
    )

    local_visitante = pd.read_csv(
        FORMA_LOCAL_VISITANTE_FILE
    )

    rendimiento = pd.read_csv(
        RENDIMIENTO_RECIENTE_FILE
    )

    for df in [
        contexto,
        forma,
        local_visitante,
        rendimiento
    ]:

        if "date" in df.columns:

            df["date"] = pd.to_datetime(
                df["date"],
                errors="coerce"
            )

    return (
        contexto,
        forma,
        local_visitante,
        rendimiento
    )


# ============================================================
# HISTORIAL CLUB
# ============================================================

def obtener_partidos_club(
    historico,
    team_name,
    corte
):

    df = historico[
        (
            historico["team_name"]
            == team_name
        )
        &
        (
            historico["date"]
            < corte
        )
    ].copy()

    if df.empty:
        return pd.DataFrame()

    partidos = (
        df[
            [
                "match_id",
                "date",
                "team_name",
            ]
        ]
        .drop_duplicates()
        .sort_values("date")
    )

    return partidos


# ============================================================
# ACTIVIDAD EN LOS ÚLTIMOS 3 PARTIDOS
#
# IMPORTANTE:
#
# Los últimos 3 NO se utilizan para decidir la calidad
# histórica del jugador.
#
# Su función es detectar actividad reciente.
#
# ============================================================

def evaluar_titularidad_ultimos_3(
    historico,
    mapa_lineups,
    player_id,
    team_name,
    corte
):

    club_partidos = obtener_partidos_club(
        historico,
        team_name,
        corte
    )

    if club_partidos.empty:

        return {

            "titulares_ultimos_3": 0,

            "partidos_club_ultimos_3": 0,

            "participaciones_ultimos_3": 0,

            "activo_ultimos_3": False,

            "titular_2_de_3": False,
        }

    ultimos_3 = (
        club_partidos
        .sort_values(
            "date",
            ascending=False
        )
        .head(3)
    )

    titulares = 0
    participaciones = 0

    for _, partido in ultimos_3.iterrows():

        match_id = str(
            partido["match_id"]
        )

        dato = mapa_lineups.get(
            (
                match_id,
                str(player_id)
            )
        )

        if dato:

            participaciones += 1

            if dato.get(
                "starter"
            ) is True:

                titulares += 1

    return {

        "titulares_ultimos_3": titulares,

        "partidos_club_ultimos_3": len(
            ultimos_3
        ),

        "participaciones_ultimos_3": participaciones,

        "activo_ultimos_3": (
            participaciones > 0
        ),

        "titular_2_de_3": (
            len(ultimos_3) == 3
            and titulares >= 2
        ),
    }


# ============================================================
# PERFIL INDIVIDUAL
#
# USA TODO EL HISTORIAL DISPONIBLE DEL JUGADOR
# EN SU CLUB ACTUAL.
#
# Los últimos 5 tienen un peso creciente dentro del
# weighted_recent, pero NO reemplazan al historial completo.
#
# ============================================================

def calcular_perfil(
    grupo
):

    grupo = (
        grupo
        .sort_values("date")
        .copy()
    )

    valores = pd.to_numeric(
        grupo["winning_total"],
        errors="coerce"
    ).fillna(0)

    n = len(valores)

    if n == 0:
        return None

    # --------------------------------------------------------
    # TODO EL HISTORIAL
    # --------------------------------------------------------

    promedio = float(
        valores.mean()
    )

    p90 = float(
        np.percentile(
            valores,
            90
        )
    )

    std = (
        float(
            valores.std()
        )
        if n > 1
        else 0.0
    )

    minimo = float(
        valores.min()
    )

    maximo = float(
        valores.max()
    )

    # --------------------------------------------------------
    # FORMA RECIENTE
    #
    # Solamente complementa al historial.
    # --------------------------------------------------------

    ultimos = valores.tail(
        min(5, n)
    )

    pesos = np.arange(
        1,
        len(ultimos) + 1
    )

    weighted = (
        float(
            np.average(
                ultimos,
                weights=pesos
            )
        )
        if len(ultimos)
        else 0
    )

    estabilidad = 1 / (
        1 + std
    )

    confianza = min(
        1.0,
        0.5
        + min(n, 15) / 30
        + estabilidad * 0.2
    )

    return {

        "partidos_historicos": n,

        "promedio": promedio,

        "weighted_recent": weighted,

        "p90": p90,

        "std": std,

        "minimo": minimo,

        "maximo": maximo,

        "confianza": confianza,

        "estabilidad": estabilidad,
    }


# ============================================================
# CONTEXTO DEL EQUIPO
# ============================================================

def calcular_factor_contexto(
    team_name,
    fecha_objetivo,
    es_local,
    contexto,
    forma,
    local_visitante,
    rendimiento
):

    factor = 1.0

    # --------------------------------------------------------
    # CONTEXTO GENERAL DEL EQUIPO
    # --------------------------------------------------------

    datos_contexto = contexto[
        (
            contexto["team_name"]
            == team_name
        )
        &
        (
            contexto["date"]
            < fecha_objetivo
        )
    ].sort_values("date")

    if not datos_contexto.empty:

        ultimo = datos_contexto.iloc[-1]

        # ----------------------------------------------------
        # Intentamos aprovechar columnas disponibles
        # relacionadas con puntos, goles y rendimiento.
        #
        # Si una columna no existe, simplemente no modifica
        # el factor.
        # ----------------------------------------------------

        posibles_puntos = [
            "puntos",
            "points",
            "forma_puntos",
            "ultimos_5_puntos",
            "puntos_ultimos_5",
        ]

        puntos_contexto = None

        for columna in posibles_puntos:

            if columna in ultimo.index:

                valor = ultimo.get(
                    columna
                )

                if pd.notna(valor):

                    puntos_contexto = safe_float(
                        valor,
                        None
                    )

                    break

        if puntos_contexto is not None:

            factor += np.clip(
                (
                    puntos_contexto - 7
                ) * 0.01,
                -0.05,
                0.05
            )

    # --------------------------------------------------------
    # FORMA RECIENTE
    # --------------------------------------------------------

    datos_forma = forma[
        (
            forma["team_name"]
            == team_name
        )
        &
        (
            forma["date"]
            < fecha_objetivo
        )
    ].sort_values("date")

    if not datos_forma.empty:

        ultimo = datos_forma.iloc[-1]

        puntos = safe_float(
            ultimo.get(
                "forma_ultimos_5_puntos",
                0
            )
        )

        goles_favor = safe_float(
            ultimo.get(
                "forma_ultimos_5_prom_goles_favor",
                0
            )
        )

        goles_contra = safe_float(
            ultimo.get(
                "forma_ultimos_5_prom_goles_contra",
                0
            )
        )

        factor += np.clip(
            (
                puntos - 7
            ) * 0.015,
            -0.08,
            0.08
        )

        factor += np.clip(
            (
                goles_favor
                - goles_contra
            ) * 0.015,
            -0.05,
            0.05
        )

    # --------------------------------------------------------
    # LOCAL / VISITANTE
    # --------------------------------------------------------

    datos_lv = local_visitante[
        (
            local_visitante["team_name"]
            == team_name
        )
        &
        (
            local_visitante["date"]
            < fecha_objetivo
        )
    ].sort_values("date")

    if not datos_lv.empty:

        ultimo = datos_lv.iloc[-1]

        if es_local:

            puntos = safe_float(
                ultimo.get(
                    "local_ultimos_5_puntos",
                    0
                )
            )

        else:

            puntos = safe_float(
                ultimo.get(
                    "visitante_ultimos_5_puntos",
                    0
                )
            )

        factor += np.clip(
            (
                puntos - 7
            ) * 0.01,
            -0.05,
            0.05
        )

    # --------------------------------------------------------
    # RENDIMIENTO RECIENTE
    # --------------------------------------------------------

    datos_rend = rendimiento[
        (
            rendimiento["team_name"]
            == team_name
        )
        &
        (
            rendimiento["date"]
            < fecha_objetivo
        )
    ].sort_values("date")

    if not datos_rend.empty:

        ultimo = datos_rend.iloc[-1]

        shots = safe_float(
            ultimo.get(
                "prom_ultimos_5_shots_on_target",
                0
            )
        )

        chances = safe_float(
            ultimo.get(
                "prom_ultimos_5_chances_created",
                0
            )
        )

        factor += np.clip(
            (
                shots - 4
            ) * 0.01,
            -0.04,
            0.04
        )

        factor += np.clip(
            (
                chances - 5
            ) * 0.005,
            -0.03,
            0.03
        )

    return float(
        np.clip(
            factor,
            0.85,
            1.15
        )
    )


# ============================================================
# POSICIONES
# ============================================================

def cargar_posiciones():

    archivo = (
        "datos/"
        "posiciones_finales_jugadores.csv"
    )

    if not os.path.exists(
        archivo
    ):

        return {}

    df = pd.read_csv(
        archivo
    )

    resultado = {}

    for _, fila in df.iterrows():

        player_id = str(
            fila.get(
                "player_id",
                ""
            )
        )

        posicion = fila.get(
            "posicion_final",
            fila.get(
                "position",
                ""
            )
        )

        if player_id:

            resultado[
                player_id
            ] = posicion

    return resultado


# ============================================================
# CONSTRUIR CANDIDATOS
#
# TODOS LOS JUGADORES DE FECHA 10 COMPITEN.
#
# Ya NO existe:
#   6-7 partidos = FLEX
#   8+ partidos = PRINCIPAL
#
# ============================================================

def construir_candidatos(
    historico,
    jugadores_objetivo,
    mapa_lineups,
    contexto,
    forma,
    local_visitante,
    rendimiento,
    posiciones
):

    candidatos = []

    fecha_objetivo = CORTE_HISTORICO

    for player_id, objetivo in (
        jugadores_objetivo.items()
    ):

        player_id = str(
            player_id
        )

        grupo = historico[
            historico["player_id"]
            .astype(str)
            == player_id
        ].copy()

        if grupo.empty:
            continue

        club = objetivo[
            "team_name"
        ]

        # ----------------------------------------------------
        # HISTORIAL EN EL CLUB ACTUAL
        # ----------------------------------------------------

        grupo_club = grupo[
            grupo["team_name"]
            == club
        ].copy()

        if grupo_club.empty:
            continue

        grupo_club = grupo_club[
            grupo_club["date"]
            < fecha_objetivo
        ].copy()

        if grupo_club.empty:
            continue

        # ----------------------------------------------------
        # ACTIVIDAD ÚLTIMOS 3
        #
        # NO se utiliza como ranking de calidad.
        #
        # Solamente se comprueba si tuvo participación reciente.
        # ----------------------------------------------------

        titularidad = (
            evaluar_titularidad_ultimos_3(
                historico,
                mapa_lineups,
                player_id,
                club,
                fecha_objetivo
            )
        )

        if not titularidad[
            "activo_ultimos_3"
        ]:

            continue

        # ----------------------------------------------------
        # PERFIL COMPLETO
        # ----------------------------------------------------

        perfil = calcular_perfil(
            grupo_club
        )

        if perfil is None:
            continue

        # ----------------------------------------------------
        # POSICIÓN
        # ----------------------------------------------------

        posicion = posiciones.get(
            player_id,
            ""
        )

        if not posicion:

            if (
                "position"
                in grupo_club.columns
                and not grupo_club[
                    "position"
                ].dropna().empty
            ):

                posicion = (
                    grupo_club[
                        "position"
                    ]
                    .dropna()
                    .iloc[-1]
                )

            else:

                posicion = ""

        posicion = str(
            posicion
        ).upper()

        if posicion not in {
            "ARQ",
            "DEF",
            "VOL",
            "DEL"
        }:

            continue

        # ----------------------------------------------------
        # LOCALÍA + RIVAL
        # ----------------------------------------------------

        match_id_fecha10 = objetivo[
            "match_id_fecha10"
        ]

        lineup = None

        for mid, data in (
            LINEUPS_GLOBAL.items()
        ):

            if mid == match_id_fecha10:

                lineup = data
                break

        if lineup is None:
            continue

        home_team = (
            lineup.get(
                "home_team",
                {}
            )
            or {}
        )

        away_team = (
            lineup.get(
                "away_team",
                {}
            )
            or {}
        )

        home_id = str(
            home_team.get(
                "id",
                ""
            )
        )

        home_name = home_team.get(
            "name",
            ""
        )

        away_name = away_team.get(
            "name",
            ""
        )

        es_local = (
            str(
                objetivo[
                    "team_id"
                ]
            )
            == home_id
        )

        rival_name = (
            away_name
            if es_local
            else home_name
        )

        # ----------------------------------------------------
        # CONTEXTO DEL EQUIPO
        # ----------------------------------------------------

        factor_contexto = (
            calcular_factor_contexto(
                club,
                fecha_objetivo,
                es_local,
                contexto,
                forma,
                local_visitante,
                rendimiento
            )
        )

        # ----------------------------------------------------
        # SCORE BASE
        #
        # El historial completo es la base.
        #
        # weighted_recent = forma reciente complementaria
        # promedio        = rendimiento histórico completo
        # p90             = techo de rendimiento histórico
        # ----------------------------------------------------

        score_base = (
            perfil[
                "weighted_recent"
            ] * 0.35

            +

            perfil[
                "promedio"
            ] * 0.40

            +

            perfil[
                "p90"
            ] * 0.25
        )

        # ----------------------------------------------------
        # CONFIANZA
        #
        # No excluye jugadores.
        # Sirve para que el score valore la robustez del
        # historial sin convertir cantidad de partidos en
        # una clasificación principal/FLEX.
        # ----------------------------------------------------

        factor_confianza = (
            0.90
            + (
                perfil[
                    "confianza"
                ]
                * 0.10
            )
        )

        score_contextual = (
            score_base
            * factor_contexto
            * factor_confianza
        )

        candidatos.append(
            {

                "player_id": player_id,

                "player_name": objetivo[
                    "player_name"
                ],

                "team_id": objetivo[
                    "team_id"
                ],

                "team_name": club,

                "position": posicion,

                "rival": rival_name,

                "es_local": es_local,

                "partidos_historicos": perfil[
                    "partidos_historicos"
                ],

                "partidos_club_ultimos_3": titularidad[
                    "partidos_club_ultimos_3"
                ],

                "participaciones_ultimos_3": titularidad[
                    "participaciones_ultimos_3"
                ],

                "activo_ultimos_3": titularidad[
                    "activo_ultimos_3"
                ],

                "titulares_ultimos_3": titularidad[
                    "titulares_ultimos_3"
                ],

                "titular_2_de_3": titularidad[
                    "titular_2_de_3"
                ],

                "weighted_recent": perfil[
                    "weighted_recent"
                ],

                "promedio": perfil[
                    "promedio"
                ],

                "p90": perfil[
                    "p90"
                ],

                "std": perfil[
                    "std"
                ],

                "minimo": perfil[
                    "minimo"
                ],

                "maximo": perfil[
                    "maximo"
                ],

                "confianza": perfil[
                    "confianza"
                ],

                "estabilidad": perfil[
                    "estabilidad"
                ],

                "factor_confianza": factor_confianza,

                "factor_contexto": factor_contexto,

                "score_base": score_base,

                "score_contextual": score_contextual,

                "starter_fecha10": objetivo[
                    "starter_fecha10"
                ],
            }
        )

    return pd.DataFrame(
        candidatos
    )


# ============================================================
# TODOS LOS CANDIDATOS
#
# Ya NO se separan por cantidad de partidos.
#
# El mismo universo completo sirve para titulares y FLEX.
# ============================================================

def separar_principal_flex(
    candidatos
):

    principales = candidatos.copy()

    flex = candidatos.copy()

    return principales, flex


# ============================================================
# SCORE SEGÚN PERFIL
# ============================================================

def calcular_score_seleccion(
    df,
    perfil_equipo
):

    df = df.copy()

    if df.empty:
        return df

    if perfil_equipo == "SEGURO":

        df[
            "score_seleccion"
        ] = (

            df[
                "score_contextual"
            ] * 0.65

            +

            df[
                "promedio"
            ] * 0.20

            +

            df[
                "estabilidad"
            ] * 0.15
        )

    elif perfil_equipo == "ARRIESGADO":

        df[
            "score_seleccion"
        ] = (

            df[
                "p90"
            ] * 0.55

            +

            df[
                "score_contextual"
            ] * 0.25

            +

            df[
                "maximo"
            ] * 0.20
        )

    else:

        df[
            "score_seleccion"
        ] = (

            df[
                "score_contextual"
            ] * 0.45

            +

            df[
                "promedio"
            ] * 0.30

            +

            df[
                "p90"
            ] * 0.25
        )

    return df


# ============================================================
# SELECCIÓN EQUIPO
# ============================================================

def seleccionar_equipo(
    candidatos,
    perfil_equipo,
    jugadores_usados=None,
    seed=None
):

    rng = random.Random(
        seed
    )

    seleccion = []

    if jugadores_usados is None:
        jugadores_usados = set()

    posiciones_necesarias = [

        "ARQ",

        "DEF",
        "DEF",
        "DEF",

        "VOL",
        "VOL",
        "VOL",

        "DEL",
        "DEL",
        "DEL",
    ]

    df = candidatos.copy()

    if df.empty:
        return []

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    df = calcular_score_seleccion(
        df,
        perfil_equipo
    )

    # --------------------------------------------------------
    # PENALIZACIÓN POR REPETICIÓN ENTRE EQUIPOS
    #
    # NO bloquea. Solo genera diversidad.
    # --------------------------------------------------------

    penalizacion = (
        PENALIZACION_REPETICION.get(
            perfil_equipo,
            0.0
        )
    )

    df[
        "veces_usado"
    ] = (

        df[
            "player_id"
        ]
        .astype(str)
        .map(
            lambda x: (
                1
                if x in jugadores_usados
                else 0
            )
        )
    )

    df[
        "score_diversidad"
    ] = (

        df[
            "score_seleccion"
        ]

        *

        (
            1
            -
            (
                penalizacion
                *
                df[
                    "veces_usado"
                ]
            )
        )
    )

    # --------------------------------------------------------
    # ELECCIÓN POR POSICIÓN
    # --------------------------------------------------------

    for posicion in [
        "ARQ",
        "DEF",
        "VOL",
        "DEL"
    ]:

        cantidad = (
            posiciones_necesarias.count(
                posicion
            )
        )

        disponibles = df[
            df[
                "position"
            ]
            == posicion
        ].copy()

        if disponibles.empty:

            print()
            print(
                "ADVERTENCIA:",
                perfil_equipo,
                "| no hay candidatos para",
                posicion
            )

            continue

        disponibles = (
            disponibles
            .sort_values(
                [
                    "score_diversidad",
                    "score_seleccion",
                    "score_contextual",
                    "promedio",
                    "p90"
                ],
                ascending=False
            )
        )

        for _, jugador in (
            disponibles.iterrows()
        ):

            cantidad_posicion = len(
                [
                    x
                    for x in seleccion
                    if x[
                        "position"
                    ]
                    == posicion
                ]
            )

            if (
                cantidad_posicion
                >= cantidad
            ):

                break

            player_id = str(
                jugador[
                    "player_id"
                ]
            )

            if any(
                str(
                    x["player_id"]
                )
                == player_id
                for x in seleccion
            ):

                continue

            club = jugador[
                "team_name"
            ]

            cantidad_club = len(
                [
                    x
                    for x in seleccion
                    if x[
                        "team_name"
                    ]
                    == club
                ]
            )

            if cantidad_club >= 3:
                continue

            jugador_dict = (
                jugador.to_dict()
            )

            jugador_dict[
                "score_diversidad"
            ] = safe_float(
                jugador[
                    "score_diversidad"
                ]
            )

            jugador_dict[
                "veces_usado_otros_equipos"
            ] = int(
                jugador[
                    "veces_usado"
                ]
            )

            seleccion.append(
                jugador_dict
            )

    # --------------------------------------------------------
    # VALIDACIÓN
    # --------------------------------------------------------

    if len(seleccion) != 10:

        print()
        print(
            "ADVERTENCIA:",
            perfil_equipo,
            "quedó con",
            len(seleccion),
            "jugadores en lugar de 10."
        )

    return seleccion


# ============================================================
# FLEX POR EQUIPO
#
# IMPORTANTE:
#
# FLEX usa TODOS los candidatos, no solamente jugadores
# con 6-7 partidos.
#
# Si ya fue FLEX anteriormente, queda bloqueado.
#
# ============================================================

def construir_flex(
    candidatos_flex,
    perfil_equipo,
    jugadores_titulares_equipo,
    jugadores_titulares_otros,
    flex_usados_global=None
):

    if flex_usados_global is None:
        flex_usados_global = set()

    resultado = []

    posiciones_flex = {

        "DEF": 2,

        "VOL": 2,

        "DEL": 2,
    }

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    df = calcular_score_seleccion(
        candidatos_flex,
        perfil_equipo
    )

    if df.empty:
        return resultado

    # --------------------------------------------------------
    # BLOQUEO ABSOLUTO DE FLEX REPETIDOS
    # --------------------------------------------------------

    ids_flex_usados = {
        str(x)
        for x in flex_usados_global
    }

    if ids_flex_usados:

        df = df[
            ~df[
                "player_id"
            ]
            .astype(str)
            .isin(
                ids_flex_usados
            )
        ].copy()

    if df.empty:

        print()
        print(
            "ADVERTENCIA FLEX:",
            perfil_equipo,
            "| no quedaron candidatos después",
            "del bloqueo de FLEX repetidos."
        )

        return resultado

    # --------------------------------------------------------
    # CADA POSICIÓN
    # --------------------------------------------------------

    for posicion, cantidad in (
        posiciones_flex.items()
    ):

        disponibles = df[
            df[
                "position"
            ]
            == posicion
        ].copy()

        if disponibles.empty:

            print()
            print(
                "ADVERTENCIA FLEX:",
                perfil_equipo,
                "|",
                posicion,
                "| no hay candidatos disponibles."
            )

            continue

        penalizacion_titular_otro = (
            PENALIZACION_FLEX_TITULAR_OTRO.get(
                perfil_equipo,
                0.0
            )
        )

        # ----------------------------------------------------
        # TODOS LOS DISPONIBLES SON NUEVOS FLEX
        # ----------------------------------------------------

        disponibles[
            "veces_flex_usado"
        ] = 0

        # ----------------------------------------------------
        # TITULARIDADES
        # ----------------------------------------------------

        disponibles[
            "titular_mismo_equipo"
        ] = (

            disponibles[
                "player_id"
            ]
            .astype(str)
            .isin(
                jugadores_titulares_equipo
            )
        )

        disponibles[
            "titular_otro_equipo"
        ] = (

            disponibles[
                "player_id"
            ]
            .astype(str)
            .isin(
                jugadores_titulares_otros
            )
        )

        # ----------------------------------------------------
        # SCORE FLEX
        # ----------------------------------------------------

        disponibles[
            "score_flex"
        ] = disponibles[
            "score_seleccion"
        ].copy()

        # ----------------------------------------------------
        # PENALIZACIÓN POR SER TITULAR DEL MISMO EQUIPO
        #
        # Se mantiene la regla anterior.
        # ----------------------------------------------------

        disponibles.loc[
            disponibles[
                "titular_mismo_equipo"
            ],
            "score_flex"
        ] *= (
            1
            -
            PENALIZACION_FLEX_TITULAR_MISMO
        )

        # ----------------------------------------------------
        # PENALIZACIÓN POR SER TITULAR DE OTRO EQUIPO
        # ----------------------------------------------------

        disponibles.loc[
            disponibles[
                "titular_otro_equipo"
            ],
            "score_flex"
        ] *= (
            1
            -
            penalizacion_titular_otro
        )

        # ----------------------------------------------------
        # ORDEN
        # ----------------------------------------------------

        disponibles = (
            disponibles
            .sort_values(
                [
                    "score_flex",
                    "score_seleccion",
                    "score_contextual",
                    "promedio",
                    "p90"
                ],
                ascending=False
            )
        )

        seleccionados_posicion = 0

        for _, jugador in (
            disponibles.iterrows()
        ):

            if (
                seleccionados_posicion
                >= cantidad
            ):

                break

            player_id = str(
                jugador[
                    "player_id"
                ]
            )

            # Seguridad: nunca repetir dentro del mismo FLEX.
            if any(
                str(
                    x["player_id"]
                )
                == player_id
                for x in resultado
            ):

                continue

            # Seguridad absoluta contra repetición global.
            if player_id in ids_flex_usados:
                continue

            jugador_dict = (
                jugador.to_dict()
            )

            jugador_dict[
                "tipo"
            ] = posicion

            jugador_dict[
                "perfil_flex"
            ] = perfil_equipo

            jugador_dict[
                "score_flex"
            ] = safe_float(
                jugador[
                    "score_flex"
                ]
            )

            jugador_dict[
                "flex_repetido"
            ] = False

            jugador_dict[
                "veces_flex_usado"
            ] = 0

            jugador_dict[
                "titular_mismo_equipo"
            ] = bool(
                jugador[
                    "titular_mismo_equipo"
                ]
            )

            jugador_dict[
                "titular_otro_equipo"
            ] = bool(
                jugador[
                    "titular_otro_equipo"
                ]
            )

            resultado.append(
                jugador_dict
            )

            seleccionados_posicion += 1

        # ----------------------------------------------------
        # VALIDACIÓN
        # ----------------------------------------------------

        if (
            seleccionados_posicion
            < cantidad
        ):

            print()
            print(
                "ADVERTENCIA FLEX:",
                perfil_equipo,
                "|",
                posicion,
                "| se obtuvieron",
                seleccionados_posicion,
                "de",
                cantidad,
                "| no se repitieron jugadores."
            )

    return resultado


# ============================================================
# SIMULACIONES
# ============================================================

def simular_equipo(
    equipo,
    perfil,
    n=N_SIMULACIONES
):

    if not equipo:
        return []

    resultados = []

    for _ in range(n):

        total = 0.0

        for jugador in equipo:

            media = safe_float(
                jugador.get(
                    "score_contextual",
                    0
                )
            )

            std = safe_float(
                jugador.get(
                    "std",
                    1
                )
            )

            p90 = safe_float(
                jugador.get(
                    "p90",
                    media
                )
            )

            if perfil == "SEGURO":

                valor = np.random.normal(
                    media,
                    max(
                        std * 0.55,
                        0.5
                    )
                )

            elif perfil == "ARRIESGADO":

                valor = np.random.normal(
                    (
                        media
                        + p90
                    ) / 2,
                    max(
                        std * 1.10,
                        0.8
                    )
                )

            else:

                valor = np.random.normal(
                    media,
                    max(
                        std * 0.8,
                        0.6
                    )
                )

            total += max(
                0,
                valor
            )

        resultados.append(
            total
        )

    return resultados


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    global LINEUPS_GLOBAL

    print()
    print("=" * 70)
    print(
        "WINNING AI - BACKTEST FECHA 10"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # HISTÓRICO
    # --------------------------------------------------------

    historico = pd.read_csv(
        HISTORICO_FILE
    )

    historico["date"] = pd.to_datetime(
        historico["date"],
        errors="coerce"
    )

    historico["player_id"] = (
        historico["player_id"]
        .astype(str)
    )

    historico_hasta_corte = (
        historico[
            historico["date"]
            < CORTE_HISTORICO
        ]
        .copy()
    )

    print()
    print(
        "Histórico utilizado:",
        len(
            historico_hasta_corte
        ),
        "registros"
    )

    print(
        "Última fecha histórica:",
        historico_hasta_corte[
            "date"
        ].max()
    )

    # --------------------------------------------------------
    # FECHA 10
    # --------------------------------------------------------

    partidos_fecha10 = (
        cargar_partidos_fecha10()
    )

    if partidos_fecha10.empty:
        return

    # --------------------------------------------------------
    # LINEUPS
    # --------------------------------------------------------

    LINEUPS_GLOBAL = (
        cargar_lineups_fecha10()
    )

    if len(
        LINEUPS_GLOBAL
    ) != 15:

        print(
            "ADVERTENCIA: se esperaban 15 lineups."
        )

    # --------------------------------------------------------
    # JUGADORES
    # --------------------------------------------------------

    jugadores_objetivo = (
        construir_jugadores_objetivo(
            LINEUPS_GLOBAL
        )
    )

    print()
    print(
        "Jugadores únicos encontrados en Fecha 10:",
        len(
            jugadores_objetivo
        )
    )

    # --------------------------------------------------------
    # LINEUPS HISTÓRICOS
    # --------------------------------------------------------

    mapa_lineups = (
        construir_mapa_lineups_historicos()
    )

    print(
        "Registros de titularidad histórica:",
        len(
            mapa_lineups
        )
    )

    # --------------------------------------------------------
    # CONTEXTOS
    # --------------------------------------------------------

    (
        contexto,
        forma,
        local_visitante,
        rendimiento
    ) = cargar_contextos()

    posiciones = (
        cargar_posiciones()
    )

    # --------------------------------------------------------
    # CANDIDATOS
    # --------------------------------------------------------

    candidatos = construir_candidatos(
        historico_hasta_corte,
        jugadores_objetivo,
        mapa_lineups,
        contexto,
        forma,
        local_visitante,
        rendimiento,
        posiciones
    )

    if candidatos.empty:

        print()
        print(
            "ERROR: no se generaron candidatos."
        )

        return

    # --------------------------------------------------------
    # ESTABILIDAD
    # --------------------------------------------------------

    candidatos[
        "estabilidad"
    ] = (

        1
        /
        (
            1
            +
            candidatos[
                "std"
            ].clip(
                lower=0
            )
        )
    )

    # --------------------------------------------------------
    # UNIVERSO COMPLETO
    # --------------------------------------------------------

    (
        principales,
        flex
    ) = separar_principal_flex(
        candidatos
    )

    print()
    print("=" * 70)
    print(
        "CANDIDATOS"
    )
    print("=" * 70)

    print(
        "Candidatos totales:",
        len(candidatos)
    )

    print(
        "Universo para titulares:",
        len(principales)
    )

    print(
        "Universo para FLEX:",
        len(flex)
    )

    print()
    print(
        "IMPORTANTE: ya no existe la separación",
        "6-7 partidos / 8+ partidos."
    )

    print(
        "Todos los candidatos compiten por rendimiento."
    )

    # --------------------------------------------------------
    # GUARDAR CANDIDATOS
    # --------------------------------------------------------

    candidatos.to_csv(
        SALIDA_CANDIDATOS,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # EQUIPOS
    # --------------------------------------------------------

    equipos_salida = []

    simulaciones_salida = []

    perfiles = [

        (
            "SEGURO",
            principales
        ),

        (
            "INTERMEDIO",
            principales
        ),

        (
            "ARRIESGADO",
            principales
        ),
    ]

    # ========================================================
    # REGISTRO GLOBAL DE JUGADORES UTILIZADOS
    # ========================================================

    jugadores_usados_global = set()

    equipos_generados = {}

    # ========================================================
    # REGISTRO DE TODOS LOS TITULARES
    # ========================================================

    titulares_por_perfil = {}

    # ========================================================
    # REGISTRO GLOBAL DE FLEX
    #
    # SET = BLOQUEO ABSOLUTO DE REPETICIÓN.
    # ========================================================

    flex_usados_global = set()

    flex_por_perfil = {}

    # ========================================================
    # GENERAR LOS 3 EQUIPOS
    # ========================================================

    for nombre_perfil, base in perfiles:

        equipo = seleccionar_equipo(
            base,
            nombre_perfil,
            jugadores_usados=(
                jugadores_usados_global
            ),
            seed=42
        )

        equipos_generados[
            nombre_perfil
        ] = equipo

        # ----------------------------------------------------
        # Guardar titulares del equipo
        # ----------------------------------------------------

        titulares_equipo = set()

        for jugador in equipo:

            player_id = str(
                jugador[
                    "player_id"
                ]
            )

            jugadores_usados_global.add(
                player_id
            )

            titulares_equipo.add(
                player_id
            )

        titulares_por_perfil[
            nombre_perfil
        ] = titulares_equipo

        # ----------------------------------------------------
        # Todos los titulares de OTROS equipos
        # ----------------------------------------------------

        titulares_otros_equipos = set()

        for otro_perfil, ids in (
            titulares_por_perfil.items()
        ):

            if (
                otro_perfil
                != nombre_perfil
            ):

                titulares_otros_equipos.update(
                    ids
                )

        # ----------------------------------------------------
        # SIMULACIONES
        # ----------------------------------------------------

        simulaciones = simular_equipo(
            equipo,
            nombre_perfil,
            N_SIMULACIONES
        )

        if simulaciones:

            arr = np.array(
                simulaciones
            )

            promedio_sim = float(
                arr.mean()
            )

            p50 = float(
                np.percentile(
                    arr,
                    50
                )
            )

            p90 = float(
                np.percentile(
                    arr,
                    90
                )
            )

            minimo = float(
                arr.min()
            )

            maximo = float(
                arr.max()
            )

            prob_100 = float(
                (
                    arr >= 100
                ).mean()
            )

            prob_140 = float(
                (
                    arr >= 140
                ).mean()
            )

        else:

            promedio_sim = 0
            p50 = 0
            p90 = 0
            minimo = 0
            maximo = 0
            prob_100 = 0
            prob_140 = 0

        # ----------------------------------------------------
        # GUARDAR TITULARES
        # ----------------------------------------------------

        for orden, jugador in enumerate(
            equipo,
            start=1
        ):

            equipos_salida.append(
                {

                    "perfil": nombre_perfil,

                    "tipo_registro": "TITULAR",

                    "orden": orden,

                    "player_id": jugador[
                        "player_id"
                    ],

                    "player_name": jugador[
                        "player_name"
                    ],

                    "team_name": jugador[
                        "team_name"
                    ],

                    "position": jugador[
                        "position"
                    ],

                    "rival": jugador.get(
                        "rival",
                        ""
                    ),

                    "es_local": jugador.get(
                        "es_local",
                        ""
                    ),

                    "score_contextual": jugador[
                        "score_contextual"
                    ],

                    "score_seleccion": jugador.get(
                        "score_seleccion",
                        ""
                    ),

                    "partidos_historicos": jugador[
                        "partidos_historicos"
                    ],

                    "participaciones_ultimos_3": jugador.get(
                        "participaciones_ultimos_3",
                        0
                    ),

                    "titulares_ultimos_3": jugador[
                        "titulares_ultimos_3"
                    ],

                    "promedio": jugador[
                        "promedio"
                    ],

                    "p90": jugador[
                        "p90"
                    ],

                    "std": jugador[
                        "std"
                    ],

                    "factor_contexto": jugador[
                        "factor_contexto"
                    ],

                    "factor_confianza": jugador.get(
                        "factor_confianza",
                        ""
                    ),

                    "score_diversidad": jugador.get(
                        "score_diversidad",
                        ""
                    ),

                    "veces_usado_otros_equipos": jugador.get(
                        "veces_usado_otros_equipos",
                        0
                    ),

                    "score_flex": "",

                    "flex_repetido": "",

                    "titular_mismo_equipo": "",

                    "titular_otro_equipo": "",

                    "veces_flex_usado": "",

                    "perfil_flex": "",

                    "sim_promedio_equipo": promedio_sim,

                    "sim_p50_equipo": p50,

                    "sim_p90_equipo": p90,

                    "sim_min_equipo": minimo,

                    "sim_max_equipo": maximo,

                    "prob_100": prob_100,

                    "prob_140": prob_140,
                }
            )

        # ----------------------------------------------------
        # GUARDAR SIMULACIONES
        # ----------------------------------------------------

        for i, valor in enumerate(
            simulaciones
        ):

            simulaciones_salida.append(
                {

                    "perfil": nombre_perfil,

                    "simulacion": i + 1,

                    "puntos": valor,
                }
            )

        # ====================================================
        # FLEX PROPIO DE ESTE EQUIPO
        # ====================================================

        flex_equipo = construir_flex(

            flex,

            nombre_perfil,

            jugadores_titulares_equipo=(
                titulares_equipo
            ),

            jugadores_titulares_otros=(
                titulares_otros_equipos
            ),

            flex_usados_global=(
                flex_usados_global
            )
        )

        flex_por_perfil[
            nombre_perfil
        ] = flex_equipo

        # ----------------------------------------------------
        # Registrar FLEX global
        #
        # Una vez utilizado, queda bloqueado.
        # ----------------------------------------------------

        for jugador in flex_equipo:

            player_id = str(
                jugador[
                    "player_id"
                ]
            )

            flex_usados_global.add(
                player_id
            )

            equipos_salida.append(
                {

                    "perfil": nombre_perfil,

                    "tipo_registro": "FLEX",

                    "orden": 0,

                    "player_id": jugador[
                        "player_id"
                    ],

                    "player_name": jugador[
                        "player_name"
                    ],

                    "team_name": jugador[
                        "team_name"
                    ],

                    "position": jugador[
                        "position"
                    ],

                    "rival": jugador.get(
                        "rival",
                        ""
                    ),

                    "es_local": jugador.get(
                        "es_local",
                        ""
                    ),

                    "score_contextual": jugador[
                        "score_contextual"
                    ],

                    "score_seleccion": jugador.get(
                        "score_seleccion",
                        ""
                    ),

                    "partidos_historicos": jugador[
                        "partidos_historicos"
                    ],

                    "participaciones_ultimos_3": jugador.get(
                        "participaciones_ultimos_3",
                        0
                    ),

                    "titulares_ultimos_3": jugador[
                        "titulares_ultimos_3"
                    ],

                    "promedio": jugador[
                        "promedio"
                    ],

                    "p90": jugador[
                        "p90"
                    ],

                    "std": jugador[
                        "std"
                    ],

                    "factor_contexto": jugador[
                        "factor_contexto"
                    ],

                    "factor_confianza": jugador.get(
                        "factor_confianza",
                        ""
                    ),

                    "score_diversidad": "",

                    "veces_usado_otros_equipos": "",

                    "score_flex": jugador.get(
                        "score_flex",
                        ""
                    ),

                    "flex_repetido": False,

                    "titular_mismo_equipo": jugador.get(
                        "titular_mismo_equipo",
                        False
                    ),

                    "titular_otro_equipo": jugador.get(
                        "titular_otro_equipo",
                        False
                    ),

                    "veces_flex_usado": 0,

                    "perfil_flex": jugador.get(
                        "perfil_flex",
                        nombre_perfil
                    ),

                    "sim_promedio_equipo": "",

                    "sim_p50_equipo": "",

                    "sim_p90_equipo": "",

                    "sim_min_equipo": "",

                    "sim_max_equipo": "",

                    "prob_100": "",

                    "prob_140": "",
                }
            )

    # --------------------------------------------------------
    # GUARDAR CSV TÉCNICO
    # --------------------------------------------------------

    df_equipos = pd.DataFrame(
        equipos_salida
    )

    df_equipos.to_csv(
        SALIDA_EQUIPOS,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # EXPORTACIÓN LIMPIA PARA EXCEL
    # --------------------------------------------------------

    columnas_excel = {

        "perfil": "Perfil",

        "tipo_registro": "Tipo",

        "orden": "Orden",

        "position": "Posición",

        "player_name": "Jugador",

        "team_name": "Club",

        "rival": "Rival",

        "es_local": "Local",

        "score_contextual": "Score",

        "score_seleccion": "Score selección",

        "partidos_historicos": "Historial",

        "participaciones_ultimos_3": "Participaciones últimos 3",

        "titulares_ultimos_3": "Titulares últimos 3",

        "promedio": "Promedio",

        "p90": "P90",

        "factor_contexto": "Factor contexto",

        "factor_confianza": "Factor confianza",

        "score_diversidad": "Score diversidad",

        "veces_usado_otros_equipos": (
            "Usado en otros equipos"
        ),

        "score_flex": "Score FLEX",

        "flex_repetido": "FLEX repetido",

        "veces_flex_usado": "FLEX usado antes",

        "titular_mismo_equipo": (
            "Titular mismo equipo"
        ),

        "titular_otro_equipo": (
            "Titular otro equipo"
        ),

        "sim_promedio_equipo": "Sim promedio",

        "sim_p50_equipo": "Sim P50",

        "sim_p90_equipo": "Sim P90",

        "sim_min_equipo": "Sim mínimo",

        "sim_max_equipo": "Sim máximo",

        "prob_100": "Prob ≥100",

        "prob_140": "Prob ≥140",
    }

    # Crear columnas que eventualmente puedan faltar
    # para evitar errores de exportación.
    for columna in columnas_excel.keys():

        if columna not in df_equipos.columns:

            df_equipos[
                columna
            ] = ""

    df_excel = df_equipos[
        list(
            columnas_excel.keys()
        )
    ].rename(
        columns=columnas_excel
    )

    # --------------------------------------------------------
    # REDONDEO
    # --------------------------------------------------------

    for col in [

        "Score",

        "Score selección",

        "Promedio",

        "P90",

        "Factor contexto",

        "Factor confianza",

        "Score diversidad",

        "Score FLEX",

        "Sim promedio",

        "Sim P50",

        "Sim P90",

        "Sim mínimo",

        "Sim máximo",

    ]:

        df_excel[col] = pd.to_numeric(
            df_excel[col],
            errors="coerce"
        ).round(3)

    # --------------------------------------------------------
    # PROBABILIDADES
    # --------------------------------------------------------

    df_excel["Prob ≥100"] = (
        pd.to_numeric(
            df_excel["Prob ≥100"],
            errors="coerce"
        )
        * 100
    ).round(2)

    df_excel["Prob ≥140"] = (
        pd.to_numeric(
            df_excel["Prob ≥140"],
            errors="coerce"
        )
        * 100
    ).round(2)

    # --------------------------------------------------------
    # GUARDAR ARCHIVO PARA EXCEL
    # --------------------------------------------------------

    df_excel.to_csv(
        SALIDA_EQUIPOS_EXCEL,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # GUARDAR SIMULACIONES
    # --------------------------------------------------------

    pd.DataFrame(
        simulaciones_salida
    ).to_csv(
        SALIDA_SIMULACIONES,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # RESUMEN
    # ========================================================

    print()
    print("=" * 70)
    print(
        "RESULTADO"
    )
    print("=" * 70)

    for perfil in [
        "SEGURO",
        "INTERMEDIO",
        "ARRIESGADO"
    ]:

        print()
        print(
            ">>>",
            perfil
        )

        # ----------------------------------------------------
        # TITULARES
        # ----------------------------------------------------

        print()
        print(
            "11 INICIAL"
        )

        datos = [

            x
            for x in equipos_salida

            if (
                x[
                    "perfil"
                ]
                == perfil
                and
                x[
                    "tipo_registro"
                ]
                == "TITULAR"
            )
        ]

        for jugador in datos:

            print(

                jugador[
                    "position"
                ],

                "|",

                jugador[
                    "player_name"
                ],

                "|",

                jugador[
                    "team_name"
                ],

                "| rival:",

                jugador.get(
                    "rival",
                    ""
                ),

                "|",

                "LOCAL"
                if jugador.get(
                    "es_local",
                    False
                )
                else "VISITANTE",

                "| score:",

                round(
                    safe_float(
                        jugador[
                            "score_contextual"
                        ]
                    ),
                    3
                ),

                "| hist:",

                jugador[
                    "partidos_historicos"
                ],

                "| participaciones 3:",

                jugador.get(
                    "participaciones_ultimos_3",
                    0
                ),

                "| titulares 3:",

                jugador[
                    "titulares_ultimos_3"
                ],

                "| usado antes:",

                jugador.get(
                    "veces_usado_otros_equipos",
                    0
                ),
            )

        if datos:

            print()
            print(
                "Sim promedio:",
                round(
                    safe_float(
                        datos[0][
                            "sim_promedio_equipo"
                        ]
                    ),
                    2
                )
            )

            print(
                "Sim P90:",
                round(
                    safe_float(
                        datos[0][
                            "sim_p90_equipo"
                        ]
                    ),
                    2
                )
            )

            print(
                "Prob >=100:",
                round(
                    safe_float(
                        datos[0][
                            "prob_100"
                        ]
                    ) * 100,
                    2
                ),
                "%"
            )

            print(
                "Prob >=140:",
                round(
                    safe_float(
                        datos[0][
                            "prob_140"
                        ]
                    ) * 100,
                    2
                ),
                "%"
            )

        # ----------------------------------------------------
        # FLEX
        # ----------------------------------------------------

        print()
        print(
            "FLEX"
        )

        flex_equipo = (
            flex_por_perfil.get(
                perfil,
                []
            )
        )

        for jugador in flex_equipo:

            print(

                jugador[
                    "position"
                ],

                "|",

                jugador[
                    "player_name"
                ],

                "|",

                jugador[
                    "team_name"
                ],

                "| rival:",

                jugador.get(
                    "rival",
                    ""
                ),

                "|",

                "LOCAL"
                if jugador.get(
                    "es_local",
                    False
                )
                else "VISITANTE",

                "| score:",

                round(
                    safe_float(
                        jugador[
                            "score_contextual"
                        ]
                    ),
                    3
                ),

                "| score FLEX:",

                round(
                    safe_float(
                        jugador.get(
                            "score_flex",
                            0
                        )
                    ),
                    3
                ),

                "| hist:",

                jugador[
                    "partidos_historicos"
                ],

                "| participaciones 3:",

                jugador.get(
                    "participaciones_ultimos_3",
                    0
                ),

                "| titulares 3:",

                jugador[
                    "titulares_ultimos_3"
                ],

                "| flex usado antes:",

                jugador.get(
                    "veces_flex_usado",
                    0
                ),

                "| titular mismo:",

                jugador.get(
                    "titular_mismo_equipo",
                    False
                ),

                "| titular otro:",

                jugador.get(
                    "titular_otro_equipo",
                    False
                ),
            )

        # ----------------------------------------------------
        # VALIDACIÓN FLEX DEL EQUIPO
        # ----------------------------------------------------

        print()

        print(
            "Cantidad FLEX:",
            len(
                flex_equipo
            )
        )

        for posicion in [
            "DEF",
            "VOL",
            "DEL"
        ]:

            cantidad = len(
                [
                    x
                    for x in flex_equipo
                    if x[
                        "position"
                    ]
                    == posicion
                ]
            )

            print(
                " ",
                posicion,
                ":",
                cantidad
            )

    # ========================================================
    # REPETICIÓN ENTRE LOS 3 EQUIPOS
    # ========================================================

    print()
    print(
        "Jugadores utilizados en más de un equipo:"
    )

    todos_los_equipos = []

    for perfil in [
        "SEGURO",
        "INTERMEDIO",
        "ARRIESGADO"
    ]:

        todos_los_equipos.extend(
            equipos_generados.get(
                perfil,
                []
            )
        )

    contador_jugadores = {}

    for jugador in todos_los_equipos:

        player_id = str(
            jugador[
                "player_id"
            ]
        )

        contador_jugadores[
            player_id
        ] = contador_jugadores.get(
            player_id,
            0
        ) + 1

    repetidos = []

    for player_id, cantidad in (
        contador_jugadores.items()
    ):

        if cantidad > 1:

            jugador_info = next(
                (
                    j
                    for j in todos_los_equipos

                    if str(
                        j[
                            "player_id"
                        ]
                    )
                    == player_id
                ),

                None
            )

            if jugador_info:

                repetidos.append(
                    (
                        jugador_info[
                            "player_name"
                        ],

                        jugador_info[
                            "team_name"
                        ],

                        cantidad
                    )
                )

    if repetidos:

        for (
            nombre,
            club,
            cantidad
        ) in sorted(
            repetidos,
            key=lambda x: (
                -x[2],
                x[0]
            )
        ):

            print(
                "-",
                nombre,
                "|",
                club,
                "|",
                cantidad,
                "equipos"
            )

    else:

        print(
            "Ningún jugador se repite."
        )

    # ========================================================
    # REPETICIÓN ENTRE LOS FLEX
    # ========================================================

    print()
    print(
        "Jugadores FLEX utilizados en más de un equipo:"
    )

    contador_flex = {}

    for perfil in [
        "SEGURO",
        "INTERMEDIO",
        "ARRIESGADO"
    ]:

        for jugador in (
            flex_por_perfil.get(
                perfil,
                []
            )
        ):

            player_id = str(
                jugador[
                    "player_id"
                ]
            )

            contador_flex[
                player_id
            ] = contador_flex.get(
                player_id,
                0
            ) + 1

    repetidos_flex = []

    for player_id, cantidad in (
        contador_flex.items()
    ):

        if cantidad > 1:

            jugador_info = None

            for perfil in [
                "SEGURO",
                "INTERMEDIO",
                "ARRIESGADO"
            ]:

                for jugador in (
                    flex_por_perfil.get(
                        perfil,
                        []
                    )
                ):

                    if str(
                        jugador[
                            "player_id"
                        ]
                    ) == player_id:

                        jugador_info = jugador
                        break

                if jugador_info:
                    break

            if jugador_info:

                repetidos_flex.append(
                    (
                        jugador_info[
                            "player_name"
                        ],

                        jugador_info[
                            "team_name"
                        ],

                        cantidad
                    )
                )

    if repetidos_flex:

        for (
            nombre,
            club,
            cantidad
        ) in sorted(
            repetidos_flex,
            key=lambda x: (
                -x[2],
                x[0]
            )
        ):

            print(
                "-",
                nombre,
                "|",
                club,
                "|",
                cantidad,
                "FLEX"
            )

    else:

        print(
            "Ningún FLEX se repite."
        )

    # ========================================================
    # RESUMEN TOTAL DE FLEX
    # ========================================================

    print()
    print(
        "TOTAL FLEX GENERADOS:"
    )

    total_flex = sum(
        len(
            flex_por_perfil.get(
                perfil,
                []
            )
        )

        for perfil in [
            "SEGURO",
            "INTERMEDIO",
            "ARRIESGADO"
        ]
    )

    print(
        total_flex,
        "de 18 posibles"
    )

    # --------------------------------------------------------
    # ARCHIVOS
    # --------------------------------------------------------

    print()
    print(
        "Archivos generados:"
    )

    print(
        "-",
        SALIDA_CANDIDATOS
    )

    print(
        "-",
        SALIDA_EQUIPOS
    )

    print(
        "-",
        SALIDA_EQUIPOS_EXCEL
    )

    print(
        "-",
        SALIDA_SIMULACIONES
    )


if __name__ == "__main__":

    main()