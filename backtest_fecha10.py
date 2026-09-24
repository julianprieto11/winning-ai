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

# Corte original utilizado para entrenar el Modelo C.
FECHA_CORTE_MODELO_C = pd.Timestamp("2026-08-01")

BACKTEST_DATASET_FILE = "datos/backtest_dataset.csv"
CONTEXTO_MATCHUP_FILE = "datos/contexto_matchup.csv"

# El Modelo C funciona como señal complementaria; no reemplaza
# el motor original ni ninguna regla de selección.
PESO_MODELO_C = 0.30

# ============================================================
# DIVERSIDAD ENTRE LOS 3 EQUIPOS
# ============================================================

PENALIZACION_REPETICION = {
    "SEGURO": 0.00,
    "INTERMEDIO": 0.30,
    "ARRIESGADO": 0.45,
}

# ============================================================
# FLEX
# ============================================================

# Si un jugador ya fue utilizado como FLEX en un equipo,
# NO puede volver a aparecer como FLEX en otro equipo.

# Si ya fue titular del MISMO equipo que estamos armando FLEX,
# queda bloqueado completamente.
PENALIZACION_FLEX_TITULAR_MISMO = 1.00

# Si fue titular de otro de los equipos, recibe una
# penalización dependiendo del perfil.
PENALIZACION_FLEX_TITULAR_OTRO = {
    "SEGURO": 0.00,
    "INTERMEDIO": 0.18,
    "ARRIESGADO": 0.30,
}

# ============================================================
# MATCHUP / MODELO C
# ============================================================

# El archivo contexto_matchup.csv ya contiene el matchup calculado
# para cada jugador/partido. Este motor solamente lo incorpora como
# señal complementaria sobre el motor original.


def cargar_csv_seguro(ruta):

    if not os.path.exists(ruta):
        return pd.DataFrame()

    try:
        return pd.read_csv(
            ruta,
            low_memory=False,
        )
    except Exception as error:
        print()
        print("ADVERTENCIA: no se pudo cargar", ruta)
        print(error)
        return pd.DataFrame()


def normalizar_posicion_matchup(valor):

    texto = normalizar_texto(valor).upper()

    if texto in {"GK", "G", "ARQ", "ARQUERO", "GOALKEEPER"}:
        return "ARQ"
    if texto in {"DEF", "DF", "D", "DEFENDER", "DEFENSA"}:
        return "DEF"
    if texto in {"MID", "MF", "M", "VOL", "VOLANTE", "MIDFIELDER"}:
        return "VOL"
    if texto in {"FWD", "FW", "ST", "DEL", "DELANTERO", "FORWARD", "ATTACKER"}:
        return "DEL"

    return ""


contexto_matchup = cargar_csv_seguro(
    CONTEXTO_MATCHUP_FILE
)

if not contexto_matchup.empty:

    if "date" in contexto_matchup.columns:
        contexto_matchup["date"] = pd.to_datetime(
            contexto_matchup["date"],
            errors="coerce"
        )

    if "player_id" in contexto_matchup.columns:
        contexto_matchup["_player_id_str"] = (
            contexto_matchup["player_id"].astype(str)
        )

    if "team_id" in contexto_matchup.columns:
        contexto_matchup["_team_id_str"] = (
            contexto_matchup["team_id"].astype(str)
        )


def calcular_matchup_directo(
    player_id,
    team_id,
    rival_team_id,
    rival_team_name,
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

    if "date" not in contexto_matchup.columns:
        return salida

    fecha = pd.to_datetime(
        fecha_objetivo,
        errors="coerce"
    )

    if pd.isna(fecha):
        return salida

    # Regla anti-leakage:
    # solamente se puede usar historial estrictamente anterior
    # al partido objetivo. Para Fecha 10 esto permite utilizar
    # los registros históricos hasta 15/09/2026.
    fecha = pd.Timestamp(fecha).normalize()

    df = contexto_matchup.copy()

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    ).dt.normalize()

    # Primero identificamos al jugador. NO buscamos la fecha exacta
    # del partido objetivo porque contexto_matchup contiene historial.
    if "player_id" in df.columns:
        candidatos = df[
            df["player_id"].astype(str) == str(player_id)
        ].copy()
    elif "team_id" in df.columns:
        candidatos = df[
            df["team_id"].astype(str) == str(team_id)
        ].copy()
    else:
        return salida

    if candidatos.empty:
        return salida

    # Solo historial anterior al partido objetivo.
    candidatos = candidatos[
        candidatos["date"].notna()
        & (candidatos["date"] < fecha)
    ].copy()

    if candidatos.empty:
        return salida

    # Preferimos la misma posición cuando está disponible.
    if "position" in candidatos.columns:
        posicion_objetivo = normalizar_posicion_matchup(posicion)
        if posicion_objetivo:
            filtradas = candidatos[
                candidatos["position"].map(
                    normalizar_posicion_matchup
                ) == posicion_objetivo
            ]
            if not filtradas.empty:
                candidatos = filtradas

    # --------------------------------------------------------
    # PRIORIDAD 1: mismo rival histórico
    #
    # contexto_matchup.csv no tiene rival_team_id, pero sí
    # rival_team_name.
    # --------------------------------------------------------
    rival_objetivo = normalizar_texto(rival_team_name)

    if (
        rival_objetivo
        and "rival_team_name" in candidatos.columns
    ):
        exactas = candidatos[
            candidatos["rival_team_name"]
            .map(normalizar_texto)
            == rival_objetivo
        ].copy()

        if not exactas.empty:
            candidatos = exactas

    # --------------------------------------------------------
    # Dentro del conjunto elegido, priorizamos registros con
    # matchup_score disponible y luego el historial más reciente.
    # --------------------------------------------------------
    if "matchup_score" in candidatos.columns:
        score_numerico = pd.to_numeric(
            candidatos["matchup_score"],
            errors="coerce"
        )
        candidatos = (
            candidatos
            .assign(_matchup_score_num=score_numerico)
            .sort_values(
                ["_matchup_score_num", "date"],
                ascending=[False, False],
                na_position="last"
            )
        )
    else:
        candidatos = candidatos.sort_values(
            "date",
            ascending=False
        )

    fila = candidatos.iloc[0]

    for columna in salida:
        if columna in fila.index:
            salida[columna] = fila[columna]

    return salida


# ============================================================
# MODELO C
# ============================================================


def limpiar_columnas_modelo(df_modelo, columnas):

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
        if any(palabra in nombre for palabra in palabras_prohibidas):
            continue

        resultado.append(c)

    return list(dict.fromkeys(resultado))


def preparar_X_modelo(data, columnas):

    X = data[columnas].copy()

    if "position" in X.columns:
        X["position"] = (
            X["position"]
            .fillna("DESCONOCIDA")
            .astype(str)
        )

    return X


def crear_pipeline_modelo(X):

    columnas_numericas = (
        X.select_dtypes(include=["number", "bool"])
        .columns.tolist()
    )

    columnas_categoricas = (
        X.select_dtypes(exclude=["number", "bool"])
        .columns.tolist()
    )

    transformers = []

    if columnas_numericas:
        transformers.append(
            (
                "numericas",
                Pipeline([
                    ("imputer", SimpleImputer(strategy="median"))
                ]),
                columnas_numericas,
            )
        )

    if columnas_categoricas:
        transformers.append(
            (
                "categoricas",
                Pipeline([
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(
                        handle_unknown="ignore",
                        sparse_output=False,
                    )),
                ]),
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

    return Pipeline([
        ("preprocesador", preprocesador),
        ("modelo", modelo),
    ])


def entrenar_modelo_c():

    print()
    print("=" * 70)
    print("MODELO C - BASE + CONTEXTO + MATCHUP")
    print("=" * 70)

    if not os.path.exists(BACKTEST_DATASET_FILE):
        print(
            "ADVERTENCIA: no existe",
            BACKTEST_DATASET_FILE,
            "| se mantiene el motor original sin Modelo C."
        )
        return None, []

    df = pd.read_csv(
        BACKTEST_DATASET_FILE,
        low_memory=False,
    )

    if "date" not in df.columns or "winning_total" not in df.columns:
        print(
            "ADVERTENCIA: backtest_dataset.csv no contiene las columnas necesarias."
        )
        return None, []

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["date", "winning_total"]
    ).copy()

    base_columns = [
        c for c in df.columns
        if (
            c.startswith("prom_ultimos_5_")
            or c in {
                "minutos_promedio_historico",
                "partidos_historicos_minutos",
                "minutos_promedio_ultimos_5",
                "position",
            }
        )
    ]

    context_columns = [
        c for c in df.columns
        if (
            c.startswith("historico_")
            or c.startswith("rival_historico_")
        )
    ]

    matchup_columns = [
        c for c in df.columns
        if c.startswith("matchup_")
    ]

    base_columns = limpiar_columnas_modelo(df, base_columns)
    context_columns = limpiar_columnas_modelo(df, context_columns)
    matchup_columns = limpiar_columnas_modelo(df, matchup_columns)

    modelo_C = list(dict.fromkeys(
        base_columns + context_columns + matchup_columns
    ))

    if not modelo_C:
        print("ADVERTENCIA: Modelo C no tiene variables disponibles.")
        return None, []

    train = df[
        df["date"] < FECHA_CORTE_MODELO_C
    ].copy()

    if train.empty:
        print("ADVERTENCIA: no hay datos de entrenamiento para Modelo C.")
        return None, []

    X_train = preparar_X_modelo(train, modelo_C)
    y_train = train["winning_total"]

    pipeline = crear_pipeline_modelo(X_train)

    print(f"BASE:     {len(base_columns)} variables")
    print(f"CONTEXTO: {len(context_columns)} variables")
    print(f"MATCHUP:  {len(matchup_columns)} variables")
    print(f"MODELO C: {len(modelo_C)} variables")
    print(f"TRAIN:    {len(train):,} filas")
    print("Entrenando Modelo C...")

    pipeline.fit(X_train, y_train)

    print("Modelo C entrenado.")

    return pipeline, modelo_C


def completar_features_modelo_c(candidatos, columnas_modelo):

    candidatos = candidatos.copy()

    if candidatos.empty:
        return candidatos

    if not os.path.exists(BACKTEST_DATASET_FILE):
        return candidatos

    df_backtest = pd.read_csv(
        BACKTEST_DATASET_FILE,
        low_memory=False,
    )

    if "date" not in df_backtest.columns:
        return candidatos

    df_backtest["date"] = pd.to_datetime(
        df_backtest["date"],
        errors="coerce"
    )

    columnas_disponibles = [
        c for c in columnas_modelo
        if c in df_backtest.columns
    ]

    for indice, fila in candidatos.iterrows():

        fecha = fila.get("fecha_partido")
        if pd.isna(fecha):
            continue

        fecha = pd.Timestamp(fecha).normalize()

        posibles = df_backtest[
            df_backtest["date"].dt.normalize() == fecha
        ].copy()

        if "player_id" in posibles.columns:
            exactos = posibles[
                posibles["player_id"].astype(str)
                == str(fila.get("player_id"))
            ]
            if not exactos.empty:
                posibles = exactos

        if (
            "team_id" in posibles.columns
            and len(posibles) > 1
        ):
            exactos = posibles[
                posibles["team_id"].astype(str)
                == str(fila.get("team_id"))
            ]
            if not exactos.empty:
                posibles = exactos

        if posibles.empty:
            continue

        origen = posibles.iloc[0]

        for columna in columnas_disponibles:
            # Solo rellenamos si el candidato todavía no trae el valor.
            if (
                columna not in candidatos.columns
                or pd.isna(candidatos.at[indice, columna])
            ):
                candidatos.at[indice, columna] = origen[columna]

    return candidatos


def agregar_prediccion_modelo_c(candidatos, pipeline, columnas_modelo):

    candidatos = candidatos.copy()
    candidatos["prediccion_modelo_c"] = np.nan

    if pipeline is None or candidatos.empty:
        return candidatos

    candidatos = completar_features_modelo_c(
        candidatos,
        columnas_modelo
    )

    for columna in columnas_modelo:
        if columna not in candidatos.columns:
            candidatos[columna] = np.nan

    X = preparar_X_modelo(
        candidatos,
        columnas_modelo
    )

    try:
        candidatos["prediccion_modelo_c"] = pipeline.predict(X)
    except Exception as error:
        print()
        print("ADVERTENCIA Modelo C:")
        print(error)

    return candidatos


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
# ============================================================
# CONSTRUIR CANDIDATOS DE LA FECHA OBJETIVO
#
# La fecha objetivo todavía no tiene lineups reales.
# Por eso NO se deben usar lineups históricos como si fueran
# la alineación de la fecha objetivo.
#
# Los jugadores candidatos se obtienen del histórico disponible
# antes del corte y se vinculan a los clubes de los partidos
# de la fecha objetivo. La titularidad esperada se sigue tratando
# como una señal histórica mediante mapa_lineups.
# ============================================================

def normalizar_equipo_objetivo(valor):

    texto = normalizar_texto(valor)

    reemplazos = {
        "instituto de cordoba": "instituto",
        "instituto": "instituto",
        "ca independiente": "independiente",
        "independiente": "independiente",
        "ca talleres": "talleres",
        "talleres": "talleres",
        "club atletico union de santa fe": "union",
        "union de santa fe": "union",
        "union": "union",
        "gimnasia y esgrima": "gimnasia",
        "gimnasia lp": "gimnasia",
        "central cordoba de santiago": "central cordoba",
        "central cordoba": "central cordoba",
    }

    return reemplazos.get(texto, texto)


def construir_jugadores_objetivo(historico, partidos_objetivo):

    jugadores = {}

    if historico.empty or partidos_objetivo.empty:
        return jugadores

    historico = historico.copy()
    historico["player_id"] = (
        historico["player_id"].astype(str)
    )

    historico["_equipo_objetivo"] = (
        historico["team_name"]
        .map(normalizar_equipo_objetivo)
    )

    # Último club conocido de cada jugador antes de la fecha objetivo.
    ultimos = (
        historico
        .sort_values(["player_id", "date"])
        .groupby("player_id", as_index=False)
        .tail(1)
    )

    clubes_objetivo = {}

    for _, partido in partidos_objetivo.iterrows():

        home_nombre = str(
            partido.get("home_team_name", "")
        )
        away_nombre = str(
            partido.get("away_team_name", "")
        )

        home_key = normalizar_equipo_objetivo(home_nombre)
        away_key = normalizar_equipo_objetivo(away_nombre)

        clubes_objetivo[home_key] = {
            "team_name_fixture": home_nombre,
            "team_key": home_key,
            "rival_name": away_nombre,
            "rival_key": away_key,
            "es_local": True,
            "event_id": str(partido.get("sofascore_id", "")),
            "fecha_partido": partido.get("fecha", pd.NaT),
        }

        clubes_objetivo[away_key] = {
            "team_name_fixture": away_nombre,
            "team_key": away_key,
            "rival_name": home_nombre,
            "rival_key": home_key,
            "es_local": False,
            "event_id": str(partido.get("sofascore_id", "")),
            "fecha_partido": partido.get("fecha", pd.NaT),
        }

    # IDs de equipo del histórico, para que matchup conserve una
    # referencia estable aunque SofaScore y PitchAPI nombren distinto.
    equipo_id_por_clave = (
        ultimos
        .assign(
            _team_key=ultimos["team_name"].map(
                normalizar_equipo_objetivo
            )
        )
        .drop_duplicates("_team_key")
        .set_index("_team_key")["team_id"]
        .astype(str)
        .to_dict()
        if "team_id" in ultimos.columns
        else {}
    )

    for _, fila in ultimos.iterrows():

        player_id = str(fila["player_id"])
        team_name = str(fila.get("team_name", ""))
        team_key = normalizar_equipo_objetivo(team_name)

        objetivo = clubes_objetivo.get(team_key)

        if objetivo is None:
            continue

        rival_key = objetivo["rival_key"]

        jugadores[player_id] = {
            "player_id": player_id,
            "player_name": str(fila.get("player_name", "")),
            "team_id": str(fila.get("team_id", "")),
            "team_name": team_name,
            "team_key": team_key,
            "match_id_fecha_objetivo": objetivo["event_id"],
            "fecha_partido": objetivo["fecha_partido"],
            "event_id": objetivo["event_id"],            "rival_team_id": str(
                equipo_id_por_clave.get(rival_key, "")
            ),
            "rival_team_name": objetivo["rival_name"],
            "es_local": objetivo["es_local"],
        }

    return jugadores


# ============================================================
# MAPA DE TITULARIDADES HISTÓRICAS
# ============================================================


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
        #
        # La información pertenece al fixture de la fecha objetivo.
        # Nunca se reconstruye desde un lineup histórico.
        # ----------------------------------------------------

        es_local = bool(
            objetivo.get("es_local", False)
        )

        rival_name = str(
            objetivo.get("rival_team_name", "")
        )

        if not rival_name:
            continue

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

        # ----------------------------------------------------
        # MATCHUP / CONTEXTO ADICIONAL
        #
        # No reemplaza el motor original. Solo aporta una señal
        # adicional que luego utiliza Modelo C.
        # ----------------------------------------------------

        matchup = calcular_matchup_directo(
            objetivo["player_id"],
            objetivo["team_id"],
            objetivo.get("rival_team_id", ""),
            objetivo.get("rival_team_name", rival_name),
            posicion,
            objetivo.get("fecha_partido", pd.NaT),
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

                "fecha_partido": objetivo.get(
                    "fecha_partido",
                    pd.NaT
                ),

                "matchup_arq": matchup["matchup_arq"],

                "matchup_def": matchup["matchup_def"],

                "matchup_vol": matchup["matchup_vol"],

                "matchup_del": matchup["matchup_del"],

                "matchup_score": matchup["matchup_score"],

                "matchup_variables_usadas": matchup[
                    "matchup_variables_usadas"
                ],

                "starter_fecha10": titularidad[
                    "titular_2_de_3"
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
            "score_seleccion_original"
        ] = (
            df["score_contextual"] * 0.65
            + df["promedio"] * 0.20
            + df["estabilidad"] * 0.15
        )

    elif perfil_equipo == "ARRIESGADO":

        df[
            "score_seleccion_original"
        ] = (
            df["p90"] * 0.55
            + df["score_contextual"] * 0.25
            + df["maximo"] * 0.20
        )

    else:

        df[
            "score_seleccion_original"
        ] = (
            df["score_contextual"] * 0.45
            + df["promedio"] * 0.30
            + df["p90"] * 0.25
        )

    # --------------------------------------------------------
    # MOTOR C COMO SEÑAL COMPLEMENTARIA
    # --------------------------------------------------------

    if "prediccion_modelo_c" not in df.columns:
        df["prediccion_modelo_c"] = np.nan

    df["prediccion_modelo_c"] = pd.to_numeric(
        df["prediccion_modelo_c"],
        errors="coerce"
    )

    df["prediccion_modelo_c"] = df[
        "prediccion_modelo_c"
    ].fillna(
        df["score_seleccion_original"]
    )

    # El score original conserva el 70% del peso.
    # Modelo C aporta el 30% restante.
    df[
        "score_seleccion"
    ] = (
        df["score_seleccion_original"]
        * (1.0 - PESO_MODELO_C)
        + df["prediccion_modelo_c"]
        * PESO_MODELO_C
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
        # BLOQUEO ABSOLUTO
        # Un titular del MISMO equipo NO puede ser FLEX.
        # ----------------------------------------------------

        disponibles = disponibles[
            ~disponibles["titular_mismo_equipo"]
        ].copy()

        if disponibles.empty:
            print()
            print(
                "ADVERTENCIA FLEX:",
                perfil_equipo,
                "|",
                posicion,
                "| no quedaron candidatos después del bloqueo",
                "de titulares del mismo equipo."
            )
            continue

        # ----------------------------------------------------
        # SCORE FLEX
        # ----------------------------------------------------

        disponibles[
            "score_flex"
        ] = disponibles[
            "score_seleccion"
        ].copy()

        # ----------------------------------------------------
        # TITULAR DEL MISMO EQUIPO = 100% PENALIZACIÓN
        # Ya fue eliminado mediante bloqueo absoluto.
        # ----------------------------------------------------

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
# CONTEXTO EXPLICATIVO PARA EXCEL
# ============================================================

def _numero_contexto(valor):
    try:
        if pd.isna(valor):
            return np.nan
        return float(valor)
    except Exception:
        return np.nan


def _texto_numero(valor, decimales=2):
    numero = _numero_contexto(valor)
    if pd.isna(numero):
        return ""
    return f"{numero:.{decimales}f}"


def generar_contexto_jugador(jugador):
    """
    Capa explicativa. NO modifica scores ni reglas de selección.

    Usa:
    - fixture objetivo (local/visitante + rival);
    - matchup calculado previamente;
    - participación/titularidad reciente;
    - promedio y P90 históricos;
    - estadísticas históricas del rival cuando están disponibles.

    Nunca inventa una tendencia: si no hay evidencia suficiente,
    simplemente omite esa parte de la explicación.
    """
    club = str(jugador.get("team_name", "") or "")
    rival = str(jugador.get("rival", "") or "")
    posicion = str(jugador.get("position", "") or "").upper()
    local = jugador.get("es_local", False)

    ubicacion = "Local" if bool(local) else "Visitante"
    partes = []

    if rival:
        partes.append(f"{ubicacion} ante {rival}")

    # --------------------------------------------------------
    # MATCHUP
    # --------------------------------------------------------
    matchup = _numero_contexto(jugador.get("matchup_score"))
    variables = _numero_contexto(jugador.get("matchup_variables_usadas"))

    if not pd.isna(matchup):
        if matchup >= 0.60:
            frase_matchup = "el matchup es favorable"
        elif matchup <= 0.40:
            frase_matchup = "el matchup es menos favorable"
        else:
            frase_matchup = "el matchup es equilibrado"

        if not pd.isna(variables) and variables > 0:
            partes.append(
                f"{frase_matchup} para {posicion} "
                f"(score {matchup:.2f}; {int(variables)} variables)"
            )
        else:
            partes.append(f"{frase_matchup} para {posicion}")

    # --------------------------------------------------------
    # TENDENCIA DEL RIVAL
    # Se calcula solo con historial anterior a la fecha objetivo.
    # --------------------------------------------------------
    fecha_objetivo = jugador.get("fecha_partido", pd.NaT)
    fecha_objetivo = pd.to_datetime(fecha_objetivo, errors="coerce")

    rival_contexto = pd.DataFrame()

    if (
        not pd.isna(fecha_objetivo)
        and not contexto_matchup.empty
        and "team_name" in contexto_matchup.columns
        and "date" in contexto_matchup.columns
    ):
        dfc = contexto_matchup.copy()
        dfc["date"] = pd.to_datetime(dfc["date"], errors="coerce")

        rival_normalizado = normalizar_texto(rival)

        if rival_normalizado:
            rival_contexto = dfc[
                (dfc["date"] < fecha_objetivo.normalize())
                & (
                    dfc["team_name"]
                    .map(normalizar_texto)
                    == rival_normalizado
                )
            ].copy()

    def promedio_rival(columnas):
        valores = []
        for columna in columnas:
            if columna in rival_contexto.columns:
                serie = pd.to_numeric(
                    rival_contexto[columna],
                    errors="coerce"
                ).dropna()
                if not serie.empty:
                    valores.append(float(serie.mean()))
        if not valores:
            return np.nan
        return float(np.mean(valores))

    def mediana_liga(columnas):
        if contexto_matchup.empty:
            return np.nan

        valores = []
        dfc = contexto_matchup.copy()

        if "date" in dfc.columns:
            fechas = pd.to_datetime(dfc["date"], errors="coerce")
            if not pd.isna(fecha_objetivo):
                dfc = dfc[fechas < fecha_objetivo.normalize()]

        for columna in columnas:
            if columna in dfc.columns:
                serie = pd.to_numeric(
                    dfc[columna],
                    errors="coerce"
                ).dropna()
                if not serie.empty:
                    valores.append(float(serie.median()))

        if not valores:
            return np.nan
        return float(np.mean(valores))

    if not rival_contexto.empty:

        if posicion == "DEL":
            columnas = [
                "rival_expectedGoals",
                "rival_expectedGoalsOnTarget",
                "rival_shotsOnGoal",
                "rival_totalShotsInsideBox",
                "rival_touchesInOppBox",
                "rival_bigChanceCreated",
            ]

            valor = promedio_rival(columnas)

            # En el historial del propio rival, rival_X representa
            # lo que sus oponentes produjeron contra él: es decir,
            # lo que el rival concedió.
            if not pd.isna(valor):
                mediana = mediana_liga(columnas)
                if not pd.isna(mediana):
                    if valor > mediana * 1.08:
                        partes.append(
                            "el rival viene concediendo un contexto alto "
                            "de xG, tiros y presencia en el área"
                        )
                    elif valor < mediana * 0.92:
                        partes.append(
                            "el rival viene concediendo un contexto bajo "
                            "de xG, tiros y presencia en el área"
                        )

        elif posicion == "VOL":
            columnas = [
                "sofascore_ballPossession",
                "sofascore_passes",
                "sofascore_accuratePasses",
            ]

            valor = promedio_rival(columnas)

            if not pd.isna(valor):
                mediana = mediana_liga(columnas)
                if not pd.isna(mediana):
                    if valor < mediana * 0.92:
                        partes.append(
                            "el rival suele tener menor volumen de "
                            "posesión y pases, favoreciendo la participación"
                            " del volante con pelota"
                        )
                    elif valor > mediana * 1.08:
                        partes.append(
                            "el rival suele dominar posesión y pases, "
                            "lo que reduce el margen de circulación del volante"
                        )

        elif posicion == "ARQ":
            columnas = [
                "sofascore_shotsOnGoal",
                "sofascore_totalShotsOnGoal",
                "sofascore_expectedGoals",
                "sofascore_totalShotsInsideBox",
                "sofascore_touchesInOppBox",
            ]

            valor = promedio_rival(columnas)

            if not pd.isna(valor):
                mediana = mediana_liga(columnas)
                if not pd.isna(mediana):
                    if valor > mediana * 1.08:
                        partes.append(
                            "el rival suele generar más tiros y xG, "
                            "elevando el volumen potencial de atajadas"
                        )
                    elif valor < mediana * 0.92:
                        partes.append(
                            "el rival suele generar menos tiros y xG, "
                            "reduciendo el volumen esperado de atajadas"
                        )

        elif posicion == "DEF":
            columnas = [
                "rival_expectedGoals",
                "rival_shotsOnGoal",
                "rival_totalShotsInsideBox",
                "rival_touchesInOppBox",
            ]

            valor = promedio_rival(columnas)

            if not pd.isna(valor):
                mediana = mediana_liga(columnas)
                if not pd.isna(mediana):
                    if valor < mediana * 0.92:
                        partes.append(
                            "el rival viene generando menos xG y tiros, "
                            "un contexto más favorable para sostener acciones defensivas"
                        )
                    elif valor > mediana * 1.08:
                        partes.append(
                            "el rival viene generando más xG y tiros, "
                            "por lo que el defensor tendrá mayor carga defensiva"
                        )

    # --------------------------------------------------------
    # FORMA / REGULARIDAD DEL JUGADOR
    # --------------------------------------------------------
    participaciones = _numero_contexto(
        jugador.get("participaciones_ultimos_3")
    )
    titulares = _numero_contexto(
        jugador.get("titulares_ultimos_3")
    )
    promedio = _numero_contexto(
        jugador.get("promedio")
    )
    p90 = _numero_contexto(
        jugador.get("p90")
    )

    forma = []

    if not pd.isna(participaciones):
        forma.append(
            f"{int(participaciones)}/3 participaciones recientes"
        )

    if not pd.isna(titulares):
        forma.append(
            f"{int(titulares)}/3 titularidades recientes"
        )

    if forma:
        partes.append("viene con " + " y ".join(forma))

    if not pd.isna(promedio) and not pd.isna(p90):
        partes.append(
            f"promedio histórico {promedio:.2f} y P90 {p90:.2f}"
        )

    return ". ".join(partes) + "." if partes else "Sin contexto adicional disponible."

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
    # FECHA OBJETIVO
    # --------------------------------------------------------

    # El fixture de la fecha objetivo se obtiene de los JSON de
    # SofaScore. Todavía no necesita lineups reales.
    jugadores_objetivo = construir_jugadores_objetivo(
        historico_hasta_corte,
        partidos_fecha10
    )

    print()
    print(
        f"Jugadores candidatos de Fecha {FECHA_OBJETIVO}:",
        len(jugadores_objetivo)
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
        local_visitante,        rendimiento,
        posiciones
    )

    if candidatos.empty:

        print()
        print(
            "ERROR: no se generaron candidatos."
        )

        return

    # --------------------------------------------------------
    # MODELO C: BASE + CONTEXTO + MATCHUP
    #
    # Es una señal adicional. No reemplaza el motor original.
    # --------------------------------------------------------

    modelo_c, columnas_modelo_c = entrenar_modelo_c()

    if modelo_c is not None:

        candidatos = agregar_prediccion_modelo_c(
            candidatos,
            modelo_c,
            columnas_modelo_c
        )

        cantidad_modelo = (
            candidatos["prediccion_modelo_c"]
            .notna()
            .sum()
        )

        print()
        print(
            "Predicciones Modelo C:",
            f"{cantidad_modelo:,}/{len(candidatos):,}"
        )

    else:

        candidatos["prediccion_modelo_c"] = np.nan

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

    print()
    print(
        "Matchup cargado:",
        "SI" if not contexto_matchup.empty else "NO"
    )

    if not candidatos.empty and "matchup_score" in candidatos.columns:
        cantidad_matchup = candidatos["matchup_score"].notna().sum()
        print(
            "Jugadores con matchup:",
            f"{cantidad_matchup:,}/{len(candidatos):,}"
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

                    "matchup_score": jugador.get(
                        "matchup_score",
                        ""
                    ),

                    "matchup_variables_usadas": jugador.get(
                        "matchup_variables_usadas",
                        ""
                    ),

                    "prediccion_modelo_c": jugador.get(
                        "prediccion_modelo_c",
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
    # GENERAR CONTEXTO EXPLICATIVO
    # --------------------------------------------------------
    # Es una columna de auditoría para entender la selección.
    # NO participa del score ni modifica la selección.
    for jugador in equipos_salida:
        jugador["contexto_explicativo"] = generar_contexto_jugador(jugador)

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

        "matchup_score": "Matchup score",

        "contexto_explicativo": "Contexto",

        "prediccion_modelo_c": "Predicción Modelo C",

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

        "Matchup score",

        "Predicción Modelo C",

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
                round(                    safe_float(
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