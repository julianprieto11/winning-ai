import json
import glob
import os
import random

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingRegressor


# ============================================================
# CONFIGURACIÓN
# ============================================================

FECHA_OBJETIVO = 10
COMPETENCIA_OBJETIVO = "Clausura"

# Todo lo anterior a esta fecha puede utilizarse como histórico.
# Fecha 10 comienza el 18/09/2026.
CORTE_HISTORICO = pd.Timestamp("2026-09-16")

# Corte ORIGINAL utilizado por backtest_comparar_modelos.py
FECHA_CORTE_MODELO_C = pd.Timestamp("2026-08-01")

HISTORICO_FILE = "datos/dataset_winning_pitchapi.csv"
BACKTEST_DATASET_FILE = "datos/backtest_dataset.csv"

CONTEXTO_EQUIPOS_FILE = "datos/contexto_equipos.csv"
FORMA_RECIENTE_FILE = "datos/forma_reciente_equipos.csv"
FORMA_LOCAL_VISITANTE_FILE = "datos/forma_local_visitante_equipos.csv"
RENDIMIENTO_RECIENTE_FILE = "datos/rendimiento_reciente_equipos.csv"

CONTEXTO_MATCHUP_FILE = "datos/contexto_matchup.csv"

LINEUPS_DIR = "datos/pitchapi/lineups"
PARTIDOS_DIR = "datos/partidos"

POSICIONES_FILE = "datos/posiciones_finales_jugadores.csv"

SALIDA_CANDIDATOS = "datos/candidatos_fecha10_final.csv"
SALIDA_EQUIPOS = "datos/fecha10_equipos_predichos.csv"
SALIDA_EQUIPOS_EXCEL = "datos/fecha10_equipos_predichos_excel.csv"
SALIDA_SIMULACIONES = "datos/fecha10_simulaciones.csv"

N_SIMULACIONES = 10000


# ============================================================
# PESO DEL NUEVO MODELO
# ============================================================

PESO_MODELO_C = 0.30


# ============================================================
# DIVERSIDAD ENTRE LOS 3 EQUIPOS
# ============================================================

PENALIZACION_REPETICION = {
    "SEGURO": 0.00,
    "INTERMEDIO": 0.18,
    "ARRIESGADO": 0.28,
}


# ============================================================
# PENALIZACIÓN FLEX
# ============================================================

PENALIZACION_FLEX_TITULAR_MISMO = 0.70

PENALIZACION_FLEX_TITULAR_OTRO = {
    "SEGURO": 0.00,
    "INTERMEDIO": 0.18,
    "ARRIESGADO": 0.30,
}


# ============================================================
# VARIABLES MATCHUP
# ============================================================

VARIABLES_ARQ = [
    "rival_shotsOnGoal",
    "rival_totalShotsOnGoal",
    "rival_expectedGoals",
    "rival_totalShotsInsideBox",
    "rival_bigChanceCreated",
    "rival_touchesInOppBox",
    "rival_accurateCross",
    "rival_cornerKicks",
    "rival_freeKicks",
    "rival_shotsOffGoal",
]

VARIABLES_DEF = [
    "rival_finalThirdEntries",
    "rival_touchesInOppBox",
    "rival_totalShotsInsideBox",
    "rival_totalShotsOnGoal",
    "rival_shotsOnGoal",
    "rival_expectedGoals",
    "rival_accurateCross",
    "rival_cornerKicks",
    "rival_fouledFinalThird",
    "rival_duelWonPercent",
    "rival_aerialDuelsPercentage",
    "rival_errorsLeadToShot",
]

VARIABLES_VOL = [
    "rival_ballPossession",
    "rival_passes",
    "rival_accuratePasses",
    "rival_finalThirdEntries",
    "rival_ballRecovery",
    "rival_duelWonPercent",
    "rival_groundDuelsPercentage",
    "rival_aerialDuelsPercentage",
    "rival_dispossessed",
    "rival_fouls",
    "rival_fouledFinalThird",
    "rival_totalTackle",
]

VARIABLES_DEL = [
    "rival_expectedGoals",
    "rival_totalShotsOnGoal",
    "rival_shotsOnGoal",
    "rival_totalShotsInsideBox",
    "rival_touchesInOppBox",
    "rival_bigChanceCreated",
    "rival_bigChanceMissed",
    "rival_fouls",
    "rival_fouledFinalThird",
    "rival_duelWonPercent",
    "rival_groundDuelsPercentage",
    "rival_aerialDuelsPercentage",
    "rival_dispossessed",
    "rival_errorsLeadToShot",
    "rival_errorsLeadToGoal",
]


DIRECCION = {}


def agregar_direccion(variables, direccion):
    for variable in variables:
        DIRECCION[variable] = direccion


# ============================================================
# DIRECCIÓN SEMÁNTICA
# ============================================================

agregar_direccion(
    VARIABLES_ARQ,
    +1
)

agregar_direccion(
    VARIABLES_DEF,
    -1
)

agregar_direccion(
    VARIABLES_VOL,
    +1
)

agregar_direccion(
    VARIABLES_DEL,
    +1
)

for variable in [
    "rival_dispossessed",
    "rival_fouls",
    "rival_errorsLeadToShot",
    "rival_errorsLeadToGoal",
]:
    DIRECCION[variable] = -1


# ============================================================
# MAPEO VARIABLES MATCHUP
# ============================================================

MAPA_VARIABLES = {}

for variable in set(
    VARIABLES_ARQ
    + VARIABLES_DEF
    + VARIABLES_VOL
    + VARIABLES_DEL
):
    MAPA_VARIABLES[variable] = variable


# ============================================================
# UTILIDADES
# ============================================================

def normalizar_texto(valor):

    if pd.isna(valor):
        return ""

    texto = str(valor).strip().lower()

    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }

    for origen, destino in reemplazos.items():
        texto = texto.replace(
            origen,
            destino
        )

    return texto


def convertir_fecha(valor):

    return pd.to_datetime(
        valor,
        errors="coerce"
    )


def safe_float(valor, default=0.0):

    try:

        if pd.isna(valor):
            return default

        return float(valor)

    except Exception:

        return default


def percentile_rank(valor, serie):

    serie = pd.to_numeric(
        serie,
        errors="coerce"
    ).dropna()

    if len(serie) == 0 or pd.isna(valor):
        return np.nan

    return float(
        (serie <= valor).mean()
    )


# ============================================================
# CARGAR FECHA 10 DESDE SOFASCORE
# ============================================================

def cargar_fecha_objetivo():

    partidos = []

    for archivo in glob.glob(
        os.path.join(
            PARTIDOS_DIR,
            "*.json"
        )
    ):

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
        )

        if (
            isinstance(event, dict)
            and "event" in event
        ):

            event = event["event"]

        if not isinstance(
            event,
            dict
        ):

            continue

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
            + str(
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
                "event_id": str(
                    event.get("id")
                ),
                "event": event,
                "data": data,
            }
        )

    unicos = {}

    for partido in partidos:

        unicos[
            partido["event_id"]
        ] = partido

    partidos = list(
        unicos.values()
    )

    partidos.sort(
        key=lambda x:
        x["event"].get(
            "startTimestamp",
            0
        )
    )

    return partidos


# ============================================================
# CARGAR LINEUPS PITCHAPI
#
# IMPORTANTE:
# Los archivos de PitchAPI no necesariamente contienen
# el event_id de SofaScore.
#
# La asociación se hace mediante:
# LOCAL + VISITANTE
# ============================================================

def cargar_lineups_pitchapi():

    lineups = []

    archivos = glob.glob(
        os.path.join(
            LINEUPS_DIR,
            "*_lineups.json"
        )
    )

    for archivo in archivos:

        try:

            with open(
                archivo,
                "r",
                encoding="utf-8"
            ) as f:

                raw = json.load(f)

        except Exception:

            continue

        if not isinstance(
            raw,
            dict
        ):

            continue

        data = raw.get(
            "data",
            {}
        )

        if not isinstance(
            data,
            dict
        ):

            continue

        if not data:
            continue

        match_id = data.get(
            "match_id"
        )

        if match_id is None:

            nombre = os.path.basename(
                archivo
            )

            match_id = nombre.replace(
                "_lineups.json",
                ""
            )

        lineups.append(
            {
                "match_id": str(
                    match_id
                ),
                "data": data,
                "archivo": archivo,
            }
        )

    return lineups


def encontrar_lineup_pitchapi(
    partido,
    lineups_pitchapi
):

    event = partido[
        "event"
    ]

    home = event.get(
        "homeTeam",
        {}
    ) or {}

    away = event.get(
        "awayTeam",
        {}
    ) or {}

    home_name = normalizar_texto(
        home.get(
            "name",
            ""
        )
    )

    away_name = normalizar_texto(
        away.get(
            "name",
            ""
        )
    )

    if not home_name or not away_name:
        return None

    candidatos = []

    for lineup in lineups_pitchapi:

        data = lineup[
            "data"
        ]

        lineup_home = data.get(
            "home_team",
            {}
        ) or {}

        lineup_away = data.get(
            "away_team",
            {}
        ) or {}

        lineup_home_name = normalizar_texto(
            lineup_home.get(
                "name",
                ""
            )
        )

        lineup_away_name = normalizar_texto(
            lineup_away.get(
                "name",
                ""
            )
        )

        if (
            lineup_home_name == home_name
            and lineup_away_name == away_name
        ):

            candidatos.append(
                lineup
            )

    if not candidatos:
        return None

    # Si hay varios, preferimos uno que tenga
    # jugadores realmente cargados.
    for candidato in candidatos:

        data = candidato[
            "data"
        ]

        home = data.get(
            "home",
            {}
        ) or {}

        away = data.get(
            "away",
            {}
        ) or {}

        starters_home = home.get(
            "starters"
        ) or []

        subs_home = home.get(
            "subs"
        ) or []

        starters_away = away.get(
            "starters"
        ) or []

        subs_away = away.get(
            "subs"
        ) or []

        cantidad = (
            len(starters_home)
            + len(subs_home)
            + len(starters_away)
            + len(subs_away)
        )

        if cantidad > 0:
            return candidato

    return candidatos[0]


# ============================================================
# CONSTRUIR JUGADORES OBJETIVO
# ============================================================

def construir_jugadores_objetivo(
    partidos,
    lineups_pitchapi
):

    jugadores = []

    for partido in partidos:

        event = partido[
            "event"
        ]

        fecha_timestamp = event.get(
            "startTimestamp"
        )

        if fecha_timestamp:

            fecha_partido = pd.to_datetime(
                fecha_timestamp,
                unit="s"
            ).normalize()

        else:

            fecha_partido = pd.NaT

        lineup = encontrar_lineup_pitchapi(
            partido,
            lineups_pitchapi
        )

        if lineup is None:
            continue

        data = lineup[
            "data"
        ]

        home_team = data.get(
            "home_team",
            {}
        ) or {}

        away_team = data.get(
            "away_team",
            {}
        ) or {}

        for lado, equipo, rival in [
            (
                "home",
                home_team,
                away_team
            ),
            (
                "away",
                away_team,
                home_team
            ),
        ]:

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

            rival_team_id = str(
                rival.get(
                    "id",
                    ""
                )
            )

            rival_team_name = rival.get(
                "name",
                ""
            )

            if not team_id:
                continue

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

                if not isinstance(
                    jugador,
                    dict
                ):
                    continue

                player_id = str(
                    jugador.get(
                        "player_id",
                        ""
                    )
                )

                if not player_id:
                    continue

                jugadores.append(
                    {
                        "player_id": player_id,
                        "player_name": jugador.get(
                            "name",
                            ""
                        ),
                        "team_id": team_id,
                        "team_name": team_name,
                        "match_id_fecha10":
                            lineup["match_id"],
                        "starter_fecha10": True,
                        "fecha_partido":
                            fecha_partido,
                        "event_id":
                            event.get("id"),
                        "rival_team_id":
                            rival_team_id,
                        "rival_team_name":
                            rival_team_name,
                        "es_local":
                            lado == "home",
                    }
                )

            for jugador in subs:

                if not isinstance(
                    jugador,
                    dict
                ):
                    continue

                player_id = str(
                    jugador.get(
                        "player_id",
                        ""
                    )
                )

                if not player_id:
                    continue

                jugadores.append(
                    {
                        "player_id": player_id,
                        "player_name": jugador.get(
                            "name",
                            ""
                        ),
                        "team_id": team_id,
                        "team_name": team_name,
                        "match_id_fecha10":
                            lineup["match_id"],
                        "starter_fecha10": False,
                        "fecha_partido":
                            fecha_partido,
                        "event_id":
                            event.get("id"),
                        "rival_team_id":
                            rival_team_id,
                        "rival_team_name":
                            rival_team_name,
                        "es_local":
                            lado == "home",
                    }
                )

    if not jugadores:
        return pd.DataFrame()

    objetivo = pd.DataFrame(
        jugadores
    )

    objetivo = objetivo.drop_duplicates(
        subset=[
            "player_id",
            "event_id",
        ]
    ).copy()

    return objetivo


# ============================================================
# NORMALIZAR POSICIONES
# ============================================================

def normalizar_posicion(valor):

    texto = normalizar_texto(
        valor
    ).upper()

    if texto in [
        "GK",
        "G",
        "ARQ",
        "ARQUERO",
        "GOALKEEPER",
    ]:

        return "ARQ"

    if texto in [
        "DEF",
        "DF",
        "D",
        "DEFENDER",
        "DEFENSA",
    ]:

        return "DEF"

    if texto in [
        "MID",
        "MF",
        "M",
        "VOL",
        "VOLANTE",
        "MIDFIELDER",
    ]:

        return "VOL"

    if texto in [
        "FWD",
        "FW",
        "ST",
        "DEL",
        "DELANTERO",
        "FORWARD",
        "ATTACKER",
    ]:

        return "DEL"

    return ""


# ============================================================
# POSICIONES FINALES
# ============================================================

def cargar_posiciones():

    if not os.path.exists(
        POSICIONES_FILE
    ):

        return {}

    try:

        df = pd.read_csv(
            POSICIONES_FILE,
            low_memory=False
        )

    except Exception:

        return {}

    resultado = {}

    id_col = None
    pos_col = None

    for c in df.columns:

        n = normalizar_texto(
            c
        )

        if n in [
            "player_id",
            "jugador_id",
        ]:

            id_col = c

        if n in [
            "position",
            "posicion",
            "posicion_final",
        ]:

            pos_col = c

    if (
        id_col is None
        or pos_col is None
    ):

        return {}

    for _, row in df.iterrows():

        if pd.isna(
            row[id_col]
        ):

            continue

        posicion = normalizar_posicion(
            row[pos_col]
        )

        if posicion:

            resultado[
                str(
                    row[id_col]
                )
            ] = posicion

    return resultado


# ============================================================
# HISTÓRICO DE JUGADORES
# ============================================================

def construir_historico_jugadores(
    historico
):

    historico = historico.copy()

    historico["date"] = pd.to_datetime(
        historico["date"],
        errors="coerce"
    )

    historico = historico[
        historico["date"]
        < CORTE_HISTORICO
    ].copy()

    return historico


# ============================================================
# PERFIL HISTÓRICO
# ============================================================

def perfil_jugador(
    grupo
):

    valores = pd.to_numeric(
        grupo["winning_total"],
        errors="coerce"
    ).dropna()

    if len(valores) == 0:

        return {
            "promedio": 0.0,
            "p90": 0.0,
            "std": 0.0,
            "minimo": 0.0,
            "maximo": 0.0,
            "weighted_recent": 0.0,
            "estabilidad": 0.0,
            "confianza": 0.5,
            "partidos": 0,
        }

    valores = valores.astype(
        float
    )

    recientes = valores.tail(
        5
    )

    if len(recientes) > 0:

        pesos = np.arange(
            1,
            len(recientes) + 1
        )

        weighted_recent = float(
            np.average(
                recientes,
                weights=pesos
            )
        )

    else:

        weighted_recent = float(
            valores.mean()
        )

    std = float(
        valores.std()
        if len(valores) > 1
        else 0.0
    )

    estabilidad = (
        1.0
        / (
            1.0
            + std
        )
    )

    confianza = min(
        1.0,
        0.5
        + min(
            len(valores),
            15
        ) / 30
        + estabilidad * 0.2
    )

    return {
        "promedio": float(
            valores.mean()
        ),
        "p90": float(
            valores.quantile(0.90)
        ),
        "std": std,
        "minimo": float(
            valores.min()
        ),
        "maximo": float(
            valores.max()
        ),
        "weighted_recent":
            weighted_recent,
        "estabilidad":
            estabilidad,
        "confianza":
            confianza,
        "partidos":
            len(valores),
    }


# ============================================================
# ACTIVIDAD RECIENTE
# ============================================================

def actividad_reciente(
    grupo,
    cantidad=3
):

    if grupo.empty:
        return False

    grupo = grupo.sort_values(
        "date"
    )

    ultimos = grupo.tail(
        cantidad
    )

    return len(ultimos) > 0


# ============================================================
# CARGAR CSV
# ============================================================

def cargar_csv_seguro(
    archivo
):

    if not os.path.exists(
        archivo
    ):

        return pd.DataFrame()

    try:

        return pd.read_csv(
            archivo,
            low_memory=False
        )

    except Exception:

        return pd.DataFrame()


contexto_equipos = cargar_csv_seguro(
    CONTEXTO_EQUIPOS_FILE
)

forma_reciente = cargar_csv_seguro(
    FORMA_RECIENTE_FILE
)

forma_local_visitante = cargar_csv_seguro(
    FORMA_LOCAL_VISITANTE_FILE
)

rendimiento_reciente = cargar_csv_seguro(
    RENDIMIENTO_RECIENTE_FILE
)


# ============================================================
# FACTOR CONTEXTO
# ============================================================

def buscar_fila_equipo(
    df,
    equipo
):

    if df.empty:
        return None

    objetivo = normalizar_texto(
        equipo
    )

    for columna in [
        "team_name",
        "equipo",
        "team",
        "nombre_equipo",
    ]:

        if columna not in df.columns:
            continue

        mask = (
            df[columna]
            .astype(str)
            .map(normalizar_texto)
            == objetivo
        )

        encontrado = df[
            mask
        ]

        if not encontrado.empty:
            return encontrado.iloc[-1]

    return None


def extraer_factor_numerico(
    fila
):

    if fila is None:
        return 1.0

    valores = []

    for columna in fila.index:

        nombre = normalizar_texto(
            columna
        )

        if nombre in [
            "factor",
            "score",
            "indice",
            "forma",
            "rendimiento",
        ]:

            valor = safe_float(
                fila[columna],
                np.nan
            )

            if not pd.isna(
                valor
            ):

                valores.append(
                    valor
                )

    if not valores:
        return 1.0

    valor = float(
        np.mean(
            valores
        )
    )

    if valor > 2:

        valor = (
            1.0
            + valor / 100.0
        )

    return max(
        0.75,
        min(
            1.25,
            valor
        )
    )


def factor_contexto_equipo(
    equipo,
    rival,
    es_local
):

    factores = []

    fila = buscar_fila_equipo(
        contexto_equipos,
        equipo
    )

    if fila is not None:

        factores.append(
            extraer_factor_numerico(
                fila
            )
        )

    fila = buscar_fila_equipo(
        forma_reciente,
        equipo
    )

    if fila is not None:

        factores.append(
            extraer_factor_numerico(
                fila
            )
        )

    fila = buscar_fila_equipo(
        forma_local_visitante,
        equipo
    )

    if fila is not None:

        factores.append(
            extraer_factor_numerico(
                fila
            )
        )

    fila = buscar_fila_equipo(
        rendimiento_reciente,
        equipo
    )

    if fila is not None:

        factores.append(
            extraer_factor_numerico(
                fila
            )
        )

    if not factores:
        return 1.0

    return float(
        np.mean(
            factores
        )
    )


# ============================================================
# CARGAR MATCHUP
# ============================================================

contexto_matchup = cargar_csv_seguro(
    CONTEXTO_MATCHUP_FILE
)

if not contexto_matchup.empty:

    if "date" in contexto_matchup.columns:

        contexto_matchup[
            "date"
        ] = pd.to_datetime(
            contexto_matchup["date"],
            errors="coerce"
        )

    if "player_id" in contexto_matchup.columns:

        contexto_matchup[
            "_player_id_str"
        ] = (
            contexto_matchup[
                "player_id"
            ]
            .astype(str)
        )

    if "team_id" in contexto_matchup.columns:

        contexto_matchup[
            "_team_id_str"
        ] = (
            contexto_matchup[
                "team_id"
            ]
            .astype(str)
        )


# ============================================================
# MATCHUP DIRECTO FECHA 10
# ============================================================

def calcular_matchup_directo(
    player_id,
    team_id,
    rival_team_id,
    posicion,
    fecha_objetivo
):

    salida = {
        "matchup_arq": np.nan,
        "matchup_def": np.nan,
        "matchup_vol": np.nan,
        "matchup_del": np.nan,
        "matchup_score": np.nan,
        "matchup_variables_usadas": np.nan,
    }

    if contexto_matchup.empty:
        return salida

    df = contexto_matchup.copy()

    if "date" not in df.columns:
        return salida

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    candidatos = pd.DataFrame()

    if "player_id" in df.columns:

        candidatos = df[
            (
                df["player_id"].astype(str)
                == str(player_id)
            )
            & (
                df["date"]
                == pd.Timestamp(
                    fecha_objetivo
                )
            )
        ].copy()

    if (
        candidatos.empty
        and "team_id" in df.columns
    ):

        candidatos = df[
            (
                df["team_id"].astype(str)
                == str(team_id)
            )
            & (
                df["date"]
                == pd.Timestamp(
                    fecha_objetivo
                )
            )
        ].copy()

    if candidatos.empty:
        return salida

    if (
        len(candidatos) > 1
        and "position" in candidatos.columns
    ):

        posicion_norm = candidatos[
            "position"
        ].map(
            normalizar_posicion
        )

        filtradas = candidatos[
            posicion_norm == posicion
        ]

        if not filtradas.empty:
            candidatos = filtradas

    fila = candidatos.iloc[0]

    for columna in salida:

        if columna in fila.index:

            salida[
                columna
            ] = fila[
                columna
            ]

    return salida


# ============================================================
# MODELO C
# ============================================================

def limpiar_columnas_modelo(
    df_modelo,
    columnas
):

    columnas_prohibidas = {
        "winning_total",
        "date",
        "match_id",
        "player_id",
        "player_name",
        "team_id",
        "team_name",
        "round_name",
        "minutes_played",
        "match_finished",
    }

    resultado = []

    palabras_prohibidas = [
        "sofascore_event",
        "sofascore_match",
        "resultado_puntos",
        "bonus_resultado",
        "valla_invicta",
        "goles_asistencias",
        "match_finished",
        "winning_total",
    ]

    for c in columnas:

        if c not in df_modelo.columns:
            continue

        if c in columnas_prohibidas:
            continue

        nombre = c.lower()

        if any(
            palabra in nombre
            for palabra in palabras_prohibidas
        ):

            continue

        resultado.append(
            c
        )

    return list(
        dict.fromkeys(
            resultado
        )
    )


def preparar_X_modelo(
    data,
    columnas
):

    X = data[
        columnas
    ].copy()

    if "position" in X.columns:

        X["position"] = (
            X["position"]
            .fillna(
                "DESCONOCIDA"
            )
            .astype(str)
        )

    return X


def crear_pipeline_modelo(
    X
):

    columnas_numericas = (
        X.select_dtypes(
            include=[
                "number",
                "bool",
            ]
        )
        .columns
        .tolist()
    )

    columnas_categoricas = (
        X.select_dtypes(
            exclude=[
                "number",
                "bool",
            ]
        )
        .columns
        .tolist()
    )

    transformers = []

    if columnas_numericas:

        transformers.append(
            (
                "numericas",
                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(
                                strategy="median"
                            ),
                        )
                    ]
                ),
                columnas_numericas,
            )
        )

    if columnas_categoricas:

        transformers.append(
            (
                "categoricas",
                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(
                                strategy="most_frequent"
                            ),
                        ),
                        (
                            "onehot",
                            OneHotEncoder(
                                handle_unknown="ignore",
                                sparse_output=False,
                            ),
                        ),
                    ]
                ),
                columnas_categoricas,
            )
        )

    preprocesador = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )

    modelo = HistGradientBoostingRegressor(
        max_iter=300,
        learning_rate=0.05,
        max_leaf_nodes=31,
        l2_regularization=1.0,
        random_state=42,
    )

    return Pipeline(
        [
            (
                "preprocesador",
                preprocesador,
            ),
            (
                "modelo",
                modelo,
            ),
        ]
    )


def entrenar_modelo_c():

    print(
        "\n============================================================"
    )

    print(
        "MODELO C - BASE + CONTEXTO + MATCHUP"
    )

    print(
        "============================================================"
    )

    if not os.path.exists(
        BACKTEST_DATASET_FILE
    ):

        print(
            "ERROR: no existe "
            f"{BACKTEST_DATASET_FILE}"
        )

        return None, []

    df = pd.read_csv(
        BACKTEST_DATASET_FILE,
        low_memory=False,
    )

    if "date" not in df.columns:

        print(
            "ERROR: backtest_dataset.csv "
            "no contiene date."
        )

        return None, []

    if "winning_total" not in df.columns:

        print(
            "ERROR: backtest_dataset.csv "
            "no contiene winning_total."
        )

        return None, []

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    df = df.dropna(
        subset=[
            "date",
            "winning_total",
        ]
    ).copy()

    # --------------------------------------------------------
    # VARIABLES EXACTAS DEL MODELO C ORIGINAL
    # --------------------------------------------------------

    base_columns = [
        c
        for c in df.columns
        if (
            c.startswith(
                "prom_ultimos_5_"
            )
            or c in {
                "minutos_promedio_historico",
                "partidos_historicos_minutos",
                "minutos_promedio_ultimos_5",
                "position",
            }
        )
    ]

    context_columns = [
        c
        for c in df.columns
        if (
            c.startswith(
                "historico_"
            )
            or c.startswith(
                "rival_historico_"
            )
        )
    ]

    matchup_columns = [
        c
        for c in df.columns
        if c.startswith(
            "matchup_"
        )
    ]

    base_columns = limpiar_columnas_modelo(
        df,
        base_columns
    )

    context_columns = limpiar_columnas_modelo(
        df,
        context_columns
    )

    matchup_columns = limpiar_columnas_modelo(
        df,
        matchup_columns
    )

    modelo_C = list(
        dict.fromkeys(
            base_columns
            + context_columns
            + matchup_columns
        )
    )

    if not modelo_C:

        print(
            "ERROR: el Modelo C no tiene "
            "variables disponibles."
        )

        return None, []

    # IMPORTANTE:
    # Se mantiene el corte ORIGINAL del modelo
    # comparador: 2026-08-01.
    train = df[
        df["date"]
        < FECHA_CORTE_MODELO_C
    ].copy()

    if train.empty:

        print(
            "ERROR: no hay datos de entrenamiento."
        )

        return None, []

    X_train = preparar_X_modelo(
        train,
        modelo_C
    )

    y_train = train[
        "winning_total"
    ]

    pipeline = crear_pipeline_modelo(
        X_train
    )

    print(
        f"BASE:     {len(base_columns)} variables"
    )

    print(
        f"CONTEXTO: {len(context_columns)} variables"
    )

    print(
        f"MATCHUP:  {len(matchup_columns)} variables"
    )

    print(
        f"MODELO C: {len(modelo_C)} variables"
    )

    print(
        f"TRAIN:    {len(train):,} filas"
    )

    print(
        "Entrenando Modelo C..."
    )

    pipeline.fit(
        X_train,
        y_train
    )

    print(
        "Modelo C entrenado."
    )

    return pipeline, modelo_C


# ============================================================
# COMPLETAR FEATURES MODELO C
# ============================================================

def completar_features_modelo_c(
    candidatos,
    columnas_modelo
):

    candidatos = candidatos.copy()

    if candidatos.empty:
        return candidatos

    if not os.path.exists(
        BACKTEST_DATASET_FILE
    ):

        return candidatos

    df_backtest = pd.read_csv(
        BACKTEST_DATASET_FILE,
        low_memory=False,
    )

    if "date" not in df_backtest.columns:
        return candidatos

    df_backtest["date"] = pd.to_datetime(
        df_backtest["date"],
        errors="coerce",
    )

    columnas_disponibles = [
        c
        for c in columnas_modelo
        if c in df_backtest.columns
    ]

    for indice, fila in candidatos.iterrows():

        player_id = fila.get(
            "player_id"
        )

        team_id = fila.get(
            "team_id"
        )

        fecha = fila.get(
            "fecha_partido"
        )

        if pd.isna(
            fecha
        ):

            continue

        fecha = pd.Timestamp(
            fecha
        ).normalize()

        posibles = df_backtest[
            df_backtest["date"]
            .dt.normalize()
            == fecha
        ].copy()

        if (
            player_id is not None
            and "player_id" in posibles.columns
        ):

            exactos = posibles[
                posibles[
                    "player_id"
                ].astype(str)
                == str(player_id)
            ]

            if not exactos.empty:

                posibles = exactos

        if (
            team_id is not None
            and "team_id" in posibles.columns
            and len(posibles) > 1
        ):

            exactos = posibles[
                posibles[
                    "team_id"
                ].astype(str)
                == str(team_id)
            ]

            if not exactos.empty:

                posibles = exactos

        if posibles.empty:
            continue

        origen = posibles.iloc[0]

        for columna in columnas_disponibles:

            candidatos.at[
                indice,
                columna
            ] = origen[
                columna
            ]

    return candidatos


# ============================================================
# CONSTRUIR CANDIDATOS
# ============================================================

def construir_candidatos(
    historico,
    partidos,
    posiciones
):

    historico = historico.copy()

    historico["date"] = pd.to_datetime(
        historico["date"],
        errors="coerce",
    )

    historico = historico[
        historico["date"]
        < CORTE_HISTORICO
    ].copy()

    # --------------------------------------------------------
    # CARGAR LINEUPS REALES DE PITCHAPI
    # --------------------------------------------------------

    lineups_pitchapi = (
        cargar_lineups_pitchapi()
    )

    print(
        f"Lineups PitchAPI cargados: "
        f"{len(lineups_pitchapi):,}"
    )

    # --------------------------------------------------------
    # CONSTRUIR JUGADORES DE FECHA 10
    # --------------------------------------------------------

    objetivo = construir_jugadores_objetivo(
        partidos,
        lineups_pitchapi
    )

    if objetivo.empty:

        print(
            "ERROR: no se encontraron "
            "jugadores de Fecha 10 en "
            "los lineups de PitchAPI."
        )

        return pd.DataFrame()

    print(
        f"Jugadores objetivo encontrados: "
        f"{len(objetivo):,}"
    )

    # --------------------------------------------------------
    # ASIGNAR POSICIONES
    # --------------------------------------------------------

    objetivo["position"] = (
        objetivo["player_id"]
        .astype(str)
        .map(posiciones)
    )

    objetivo = objetivo[
        objetivo["position"].isin(
            [
                "ARQ",
                "DEF",
                "VOL",
                "DEL",
            ]
        )
    ].copy()

    print(
        f"Jugadores con posición válida: "
        f"{len(objetivo):,}"
    )

    if objetivo.empty:
        return pd.DataFrame()

    # --------------------------------------------------------
    # HISTORIAL POR JUGADOR
    # --------------------------------------------------------

    if "player_id" not in historico.columns:

        return pd.DataFrame()

    historico["_player_id_str"] = (
        historico["player_id"]
        .astype(str)
    )

    candidatos = []

    for _, jugador in objetivo.iterrows():

        player_id = jugador[
            "player_id"
        ]

        grupo = historico[
            historico[
                "_player_id_str"
            ]
            == str(player_id)
        ].copy()

        # Fallback por nombre.
        if (
            grupo.empty
            and "player_name"
            in historico.columns
        ):

            grupo = historico[
                historico[
                    "player_name"
                ]
                .astype(str)
                .map(
                    normalizar_texto
                )
                == normalizar_texto(
                    jugador[
                        "player_name"
                    ]
                )
            ].copy()

        if grupo.empty:
            continue

        grupo = grupo.sort_values(
            "date"
        )

        if not actividad_reciente(
            grupo,
            3
        ):

            continue

        perfil = perfil_jugador(
            grupo
        )

        if perfil[
            "partidos"
        ] == 0:

            continue

        factor_contexto = (
            factor_contexto_equipo(
                jugador[
                    "team_name"
                ],
                jugador[
                    "rival_team_name"
                ],
                jugador[
                    "es_local"
                ]
            )
        )

        # ----------------------------------------------------
        # MATCHUP
        # ----------------------------------------------------

        matchup = calcular_matchup_directo(
            jugador[
                "player_id"
            ],
            jugador[
                "team_id"
            ],
            jugador[
                "rival_team_id"
            ],
            jugador[
                "position"
            ],
            jugador[
                "fecha_partido"
            ],
        )

        fila = {
            "player_id":
                jugador[
                    "player_id"
                ],

            "player_name":
                jugador[
                    "player_name"
                ],

            "team_id":
                jugador[
                    "team_id"
                ],

            "team_name":
                jugador[
                    "team_name"
                ],

            "position":
                jugador[
                    "position"
                ],

            "starter":
                jugador[
                    "starter_fecha10"
                ],

            "fecha_partido":
                jugador[
                    "fecha_partido"
                ],

            "event_id":
                jugador[
                    "event_id"
                ],

            "rival_team_id":
                jugador[
                    "rival_team_id"
                ],

            "rival_team_name":
                jugador[
                    "rival_team_name"
                ],

            "es_local":
                jugador[
                    "es_local"
                ],

            "partidos_historial":
                perfil[
                    "partidos"
                ],

            "promedio_winning":
                perfil[
                    "promedio"
                ],

            "p90":
                perfil[
                    "p90"
                ],

            "std":
                perfil[
                    "std"
                ],

            "minimo":
                perfil[
                    "minimo"
                ],

            "maximo":
                perfil[
                    "maximo"
                ],

            "weighted_recent":
                perfil[
                    "weighted_recent"
                ],

            "estabilidad":
                perfil[
                    "estabilidad"
                ],

            "confianza":
                perfil[
                    "confianza"
                ],

            "factor_contexto":
                factor_contexto,

            "matchup_arq":
                matchup[
                    "matchup_arq"
                ],

            "matchup_def":
                matchup[
                    "matchup_def"
                ],

            "matchup_vol":
                matchup[
                    "matchup_vol"
                ],

            "matchup_del":
                matchup[
                    "matchup_del"
                ],

            "matchup_score":
                matchup[
                    "matchup_score"
                ],

            "matchup_variables_usadas":
                matchup[
                    "matchup_variables_usadas"
                ],
        }

        # ----------------------------------------------------
        # MOTOR ORIGINAL
        # ----------------------------------------------------

        score_base = (
            perfil[
                "weighted_recent"
            ] * 0.35
            + perfil[
                "promedio"
            ] * 0.40
            + perfil[
                "p90"
            ] * 0.25
        )

        factor_confianza = (
            0.90
            + perfil[
                "confianza"
            ] * 0.10
        )

        score_contextual = (
            score_base
            * factor_contexto
            * factor_confianza
        )

        fila[
            "score_base"
        ] = score_base

        fila[
            "factor_confianza"
        ] = factor_confianza

        fila[
            "score_contextual"
        ] = score_contextual

        candidatos.append(
            fila
        )

    resultado = pd.DataFrame(
        candidatos
    )

    return resultado


# ============================================================
# SCORE MODELO C
# ============================================================

def agregar_prediccion_modelo_c(
    candidatos,
    pipeline,
    columnas_modelo
):

    candidatos = candidatos.copy()

    candidatos[
        "prediccion_modelo_c"
    ] = np.nan

    if (
        pipeline is None
        or candidatos.empty
    ):

        return candidatos

    candidatos = completar_features_modelo_c(
        candidatos,
        columnas_modelo
    )

    for columna in columnas_modelo:

        if columna not in candidatos.columns:

            candidatos[
                columna
            ] = np.nan

    X = preparar_X_modelo(
        candidatos,
        columnas_modelo
    )

    try:

        predicciones = pipeline.predict(
            X
        )

        candidatos[
            "prediccion_modelo_c"
        ] = predicciones

    except Exception as error:

        print(
            "\nADVERTENCIA Modelo C:"
        )

        print(
            error
        )

    return candidatos


# ============================================================
# SCORE DE SELECCIÓN
# ============================================================

def calcular_score_seleccion(
    fila,
    perfil_equipo
):

    promedio = safe_float(
        fila.get(
            "promedio_winning",
            0
        )
    )

    p90 = safe_float(
        fila.get(
            "p90",
            0
        )
    )

    estabilidad = safe_float(
        fila.get(
            "estabilidad",
            0
        )
    )

    score_contextual = safe_float(
        fila.get(
            "score_contextual",
            0
        )
    )

    pred_modelo = fila.get(
        "prediccion_modelo_c",
        np.nan
    )

    # --------------------------------------------------------
    # MOTOR ORIGINAL
    # --------------------------------------------------------

    if perfil_equipo == "SEGURO":

        score_original = (
            score_contextual * 0.65
            + promedio * 0.20
            + estabilidad * 0.15
        )

    elif perfil_equipo == "ARRIESGADO":

        score_original = (
            p90 * 0.55
            + score_contextual * 0.25
            + safe_float(
                fila.get(
                    "maximo",
                    0
                )
            ) * 0.20
        )

    else:

        score_original = (
            score_contextual * 0.45
            + promedio * 0.30
            + p90 * 0.25
        )

    # --------------------------------------------------------
    # MODELO C
    # --------------------------------------------------------

    if pd.isna(
        pred_modelo
    ):

        pred_modelo = score_original

    pred_modelo = safe_float(
        pred_modelo,
        score_original
    )

    score_modelo_c = (
        pred_modelo
    )

    # --------------------------------------------------------
    # BLEND
    # --------------------------------------------------------

    score_final = (
        score_original
        * (1.0 - PESO_MODELO_C)
        + score_modelo_c
        * PESO_MODELO_C
    )

    return float(
        score_final
    )


# ============================================================
# SEPARAR PRINCIPAL / FLEX
# ============================================================

def separar_principal_flex(
    candidatos
):

    return (
        candidatos.copy(),
        candidatos.copy()
    )


# ============================================================
# SELECCIONAR EQUIPO
# ============================================================

def seleccionar_equipo(
    candidatos,
    perfil_equipo,
    jugadores_usados
):

    posiciones_requeridas = {
        "ARQ": 1,
        "DEF": 3,
        "VOL": 3,
        "DEL": 3,
    }

    seleccionados = []

    clubes_usados = {}

    for posicion, cantidad in (
        posiciones_requeridas.items()
    ):

        disponibles = candidatos[
            candidatos[
                "position"
            ]
            == posicion
        ].copy()

        if disponibles.empty:
            continue

        disponibles[
            "score_seleccion"
        ] = disponibles.apply(
            lambda fila:
            calcular_score_seleccion(
                fila,
                perfil_equipo
            ),
            axis=1
        )

        def calcular_diversidad(
            fila
        ):

            player_id = str(
                fila[
                    "player_id"
                ]
            )

            penalizacion = (
                PENALIZACION_REPETICION[
                    perfil_equipo
                ]
                if player_id
                in jugadores_usados
                else 0.0
            )

            return (
                fila[
                    "score_seleccion"
                ]
                - penalizacion
            )

        disponibles[
            "score_diversidad"
        ] = disponibles.apply(
            calcular_diversidad,
            axis=1
        )

        disponibles = disponibles.sort_values(
            [
                "score_diversidad",
                "score_seleccion",
                "score_contextual",
                "promedio_winning",
                "p90",
            ],
            ascending=False,
        )

        elegidos = []

        for _, fila in disponibles.iterrows():

            team_id = str(
                fila[
                    "team_id"
                ]
            )

            cantidad_club = clubes_usados.get(
                team_id,
                0
            )

            if cantidad_club >= 3:
                continue

            elegidos.append(
                fila
            )

            clubes_usados[
                team_id
            ] = (
                cantidad_club
                + 1
            )

            if len(elegidos) >= cantidad:
                break

        seleccionados.extend(
            elegidos
        )

    return pd.DataFrame(
        seleccionados
    )


# ============================================================
# CONSTRUIR FLEX
#
# 2 DEF + 2 VOL + 2 DEL
# ============================================================

def construir_flex(
    candidatos,
    titulares,
    perfil_equipo,
    flex_global
):

    resultado = []

    titulares_ids = set(
        titulares[
            "player_id"
        ].astype(str)
    )

    titulares_clubes = set(
        titulares[
            "team_id"
        ].astype(str)
    )

    for posicion in [
        "DEF",
        "VOL",
        "DEL",
    ]:

        disponibles = candidatos[
            candidatos[
                "position"
            ]
            == posicion
        ].copy()

        if disponibles.empty:
            continue

        disponibles[
            "score_seleccion"
        ] = disponibles.apply(
            lambda fila:
            calcular_score_seleccion(
                fila,
                perfil_equipo
            ),
            axis=1
        )

        def score_flex(
            fila
        ):

            score = fila[
                "score_seleccion"
            ]

            player_id = str(
                fila[
                    "player_id"
                ]
            )

            team_id = str(
                fila[
                    "team_id"
                ]
            )

            if player_id in flex_global:

                return -999999

            if player_id in titulares_ids:

                score -= (
                    PENALIZACION_FLEX_TITULAR_MISMO
                )

            if team_id in titulares_clubes:

                score -= (
                    PENALIZACION_FLEX_TITULAR_OTRO[
                        perfil_equipo
                    ]
                )

            return score

        disponibles[
            "score_flex"
        ] = disponibles.apply(
            score_flex,
            axis=1
        )

        disponibles = disponibles.sort_values(
            [
                "score_flex",
                "score_seleccion",
                "score_contextual",
                "promedio_winning",
            ],
            ascending=False,
        )

        cantidad = 0

        for _, fila in disponibles.iterrows():

            player_id = str(
                fila[
                    "player_id"
                ]
            )

            if player_id in flex_global:
                continue

            fila = fila.copy()

            fila[
                "tipo"
            ] = "FLEX"

            fila[
                "flex_posicion"
            ] = posicion

            resultado.append(
                fila
            )

            flex_global.add(
                player_id
            )

            cantidad += 1

            if cantidad >= 2:
                break

    return pd.DataFrame(
        resultado
    )


# ============================================================
# SIMULACIONES
# ============================================================

def simular_equipo(
    titulares,
    perfil_equipo
):

    if titulares.empty:

        return {
            "media": 0.0,
            "p90": 0.0,
            "prob_superar_media": 0.0,
        }

    medias = []

    for _, fila in titulares.iterrows():

        media = safe_float(
            fila.get(
                "score_contextual",
                0
            )
        )

        pred = safe_float(
            fila.get(
                "prediccion_modelo_c",
                media
            )
        )

        media = (
            media
            * (1.0 - PESO_MODELO_C)
            + pred
            * PESO_MODELO_C
        )

        desviacion = max(
            0.05,
            safe_float(
                fila.get(
                    "std",
                    0.5
                )
            )
        )

        if perfil_equipo == "ARRIESGADO":

            centro = safe_float(
                fila.get(
                    "p90",
                    media
                )
            )

        else:

            centro = media

        medias.append(
            (
                centro,
                desviacion
            )
        )

    simulaciones = np.zeros(
        N_SIMULACIONES
    )

    for centro, desviacion in medias:

        simulaciones += np.random.normal(
            centro,
            desviacion,
            N_SIMULACIONES
        )

    media_total = float(
        np.mean(
            simulaciones
        )
    )

    p90_total = float(
        np.percentile(
            simulaciones,
            90
        )
    )

    prob_superar_media = float(
        np.mean(
            simulaciones
            >= media_total
        )
    )

    return {
        "media": media_total,
        "p90": p90_total,
        "prob_superar_media":
            prob_superar_media,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 70
    )

    print(
        "WINNING AI - BACKTEST FECHA 10 + MODELO C"
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # HISTÓRICO
    # --------------------------------------------------------

    print(
        "\n[1/8] Cargando histórico..."
    )

    historico = pd.read_csv(
        HISTORICO_FILE,
        low_memory=False,
    )

    historico["date"] = pd.to_datetime(
        historico["date"],
        errors="coerce",
    )

    historico = historico[
        historico["date"]
        < CORTE_HISTORICO
    ].copy()

    print(
        f"Histórico hasta "
        f"{CORTE_HISTORICO.date()}: "
        f"{len(historico):,} registros"
    )

    # --------------------------------------------------------
    # MODELO C
    # --------------------------------------------------------

    print(
        "\n[2/8] Entrenando Modelo C..."
    )

    modelo_c, columnas_modelo_c = (
        entrenar_modelo_c()
    )

    # --------------------------------------------------------
    # FECHA 10
    # --------------------------------------------------------

    print(
        "\n[3/8] Cargando Fecha 10..."
    )

    partidos = cargar_fecha_objetivo()

    print(
        f"Partidos Fecha {FECHA_OBJETIVO}: "
        f"{len(partidos)}"
    )

    for partido in partidos:

        event = partido[
            "event"
        ]

        home = (
            event.get(
                "homeTeam",
                {}
            )
            or {}
        )

        away = (
            event.get(
                "awayTeam",
                {}
            )
            or {}
        )

        fecha = pd.to_datetime(
            event.get(
                "startTimestamp"
            ),
            unit="s",
        ).date()

        print(
            f"{fecha} | "
            f"{home.get('name')} - "
            f"{away.get('name')} | "
            f"{event.get('id')}"
        )

    # --------------------------------------------------------
    # POSICIONES
    # --------------------------------------------------------

    print(
        "\n[4/8] Cargando posiciones..."
    )

    posiciones = cargar_posiciones()

    print(
        f"Posiciones cargadas: "
        f"{len(posiciones):,}"
    )

    # --------------------------------------------------------
    # CANDIDATOS
    # --------------------------------------------------------

    print(
        "\n[5/8] Construyendo candidatos..."
    )

    candidatos = construir_candidatos(
        historico,
        partidos,
        posiciones,
    )

    if candidatos.empty:

        print(
            "\nERROR: no se pudieron "
            "construir candidatos."
        )

        return

    print(
        f"Candidatos: "
        f"{len(candidatos):,}"
    )

    # --------------------------------------------------------
    # MODELO C
    # --------------------------------------------------------

    print(
        "\nAplicando Modelo C..."
    )

    candidatos = agregar_prediccion_modelo_c(
        candidatos,
        modelo_c,
        columnas_modelo_c,
    )

    cantidad_modelo = (
        candidatos[
            "prediccion_modelo_c"
        ]
        .notna()
        .sum()
    )

    print(
        "Predicciones Modelo C: "
        f"{cantidad_modelo:,}/"
        f"{len(candidatos):,}"
    )

    # --------------------------------------------------------
    # GUARDAR CANDIDATOS
    # --------------------------------------------------------

    candidatos.to_csv(
        SALIDA_CANDIDATOS,
        index=False,
    )

    print(
        f"\nCandidatos guardados: "
        f"{SALIDA_CANDIDATOS}"
    )

    # --------------------------------------------------------
    # 3 PERFILES
    # --------------------------------------------------------

    perfiles = [
        "SEGURO",
        "INTERMEDIO",
        "ARRIESGADO",
    ]

    jugadores_usados_global = set()

    flex_global = set()

    filas_equipos = []

    filas_excel = []

    filas_simulaciones = []

    for perfil_equipo in perfiles:

        print(
            "\n"
            + "=" * 70
        )

        print(
            f"EQUIPO {perfil_equipo}"
        )

        print(
            "=" * 70
        )

        titulares = seleccionar_equipo(
            candidatos,
            perfil_equipo,
            jugadores_usados_global,
        )

        if titulares.empty:

            print(
                "No se pudo construir equipo."
            )

            continue

        # ----------------------------------------------------
        # Registrar titulares globales
        # ----------------------------------------------------

        for player_id in titulares[
            "player_id"
        ]:

            jugadores_usados_global.add(
                str(player_id)
            )

        # ----------------------------------------------------
        # FLEX
        # ----------------------------------------------------

        flex = construir_flex(
            candidatos,
            titulares,
            perfil_equipo,
            flex_global,
        )

        # ----------------------------------------------------
        # SIMULACIONES
        # ----------------------------------------------------

        simulacion = simular_equipo(
            titulares,
            perfil_equipo,
        )

        filas_simulaciones.append(
            {
                "perfil":
                    perfil_equipo,

                "media_simulada":
                    simulacion[
                        "media"
                    ],

                "p90_simulado":
                    simulacion[
                        "p90"
                    ],

                "prob_superar_media":
                    simulacion[
                        "prob_superar_media"
                    ],
            }
        )

        # ----------------------------------------------------
        # IMPRIMIR TITULARES
        # ----------------------------------------------------

        print(
            f"\nTITULARES: "
            f"{len(titulares)}"
        )

        for numero, (_, jugador) in enumerate(
            titulares.iterrows(),
            start=1,
        ):

            score = calcular_score_seleccion(
                jugador,
                perfil_equipo,
            )

            print(
                f"{numero:02d}. "
                f"{jugador['position']} | "
                f"{jugador['player_name']} | "
                f"{jugador['team_name']} | "
                f"score={score:.4f} | "
                f"MC={safe_float(jugador.get('prediccion_modelo_c', np.nan), 0):.4f}"
            )

            fila_salida = jugador.to_dict()

            fila_salida[
                "perfil"
            ] = perfil_equipo

            fila_salida[
                "tipo"
            ] = "TITULAR"

            fila_salida[
                "score_seleccion"
            ] = score

            fila_salida[
                "prediccion_modelo_c"
            ] = safe_float(
                jugador.get(
                    "prediccion_modelo_c",
                    np.nan
                ),
                np.nan,
            )

            filas_equipos.append(
                fila_salida
            )

            filas_excel.append(
                fila_salida
            )

        # ----------------------------------------------------
        # IMPRIMIR FLEX
        # ----------------------------------------------------

        print(
            f"\nFLEX: "
            f"{len(flex)}"
        )

        if not flex.empty:

            for numero, (_, jugador) in enumerate(
                flex.iterrows(),
                start=1,
            ):

                score = calcular_score_seleccion(
                    jugador,
                    perfil_equipo,
                )

                print(
                    f"FLEX {numero:02d}. "
                    f"{jugador['position']} | "
                    f"{jugador['player_name']} | "
                    f"{jugador['team_name']} | "
                    f"score={score:.4f} | "
                    f"MC={safe_float(jugador.get('prediccion_modelo_c', np.nan), 0):.4f}"
                )

                fila_salida = jugador.to_dict()

                fila_salida[
                    "perfil"
                ] = perfil_equipo

                fila_salida[
                    "tipo"
                ] = "FLEX"

                fila_salida[
                    "score_seleccion"
                ] = score

                filas_equipos.append(
                    fila_salida
                )

                filas_excel.append(
                    fila_salida
                )

    # ========================================================
    # GUARDAR EQUIPOS
    # ========================================================

    print(
        "\n[7/8] Guardando equipos..."
    )

    if filas_equipos:

        salida_equipos = pd.DataFrame(
            filas_equipos
        )

        salida_equipos.to_csv(
            SALIDA_EQUIPOS,
            index=False,
        )

        print(
            f"CSV: {SALIDA_EQUIPOS}"
        )

    if filas_excel:

        salida_excel = pd.DataFrame(
            filas_excel
        )

        salida_excel.to_csv(
            SALIDA_EQUIPOS_EXCEL,
            index=False,
        )

        print(
            f"Excel-compatible CSV: "
            f"{SALIDA_EQUIPOS_EXCEL}"
        )

    # ========================================================
    # GUARDAR SIMULACIONES
    # ========================================================

    print(
        "\n[8/8] Guardando simulaciones..."
    )

    pd.DataFrame(
        filas_simulaciones
    ).to_csv(
        SALIDA_SIMULACIONES,
        index=False,
    )

    print(
        f"Simulaciones: "
        f"{SALIDA_SIMULACIONES}"
    )

    # ========================================================
    # VALIDACIONES
    # ========================================================

    print(
        "\n"
        + "=" * 70
    )

    print(
        "VALIDACIÓN FINAL"
    )

    print(
        "=" * 70
    )

    if filas_equipos:

        salida = pd.DataFrame(
            filas_equipos
        )

        for perfil in perfiles:

            grupo = salida[
                salida[
                    "perfil"
                ]
                == perfil
            ]

            titulares = grupo[
                grupo[
                    "tipo"
                ]
                == "TITULAR"
            ]

            flex = grupo[
                grupo[
                    "tipo"
                ]
                == "FLEX"
            ]

            print(
                f"\n{perfil}"
            )

            print(
                f"  Titulares: "
                f"{len(titulares)}"
            )

            print(
                f"  FLEX: "
                f"{len(flex)}"
            )

            if not titulares.empty:

                print(
                    "  Clubes titulares:"
                )

                print(
                    titulares[
                        "team_name"
                    ]
                    .value_counts()
                    .to_dict()
                )

    print(
        "\nRepetición global de titulares:"
    )

    if filas_equipos:

        titulares_global = pd.DataFrame(
            filas_equipos
        )

        titulares_global = titulares_global[
            titulares_global[
                "tipo"
            ]
            == "TITULAR"
        ]

        repetidos = (
            titulares_global[
                "player_id"
            ]
            .astype(str)
            .value_counts()
        )

        repetidos = repetidos[
            repetidos > 1
        ]

        if repetidos.empty:

            print(
                "  OK - sin repeticiones."
            )

        else:

            print(
                repetidos.to_dict()
            )

    print(
        "\n"
        + "=" * 70
    )

    print(
        "BACKTEST FECHA 10 + MODELO C TERMINADO"
    )

    print(
        "=" * 70
    )


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":

    main()