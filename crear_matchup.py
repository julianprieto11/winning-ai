import pandas as pd
import numpy as np


# ============================================================
# MATCHUP V3
#
# Arquitectura:
#
#   HISTORIAL DEL PROPIO EQUIPO
#          +
#   HISTORIAL DEL RIVAL
#          +
#   INTERACCION PROPIO VS RIVAL
#          ↓
#      MATCHUP SCORE
#
# IMPORTANTE:
# - No exige historial jugador vs rival.
# - Todo se calcula usando solamente datos anteriores a la fecha objetivo.
# - No modifica ninguna regla del motor de selección.
# - El historial individual del jugador sigue perteneciendo a
#   score_contextual; aquí medimos el contexto del partido.
# ============================================================

ARCHIVO_ENTRADA = "datos/contexto_equipos.csv"
ARCHIVO_SALIDA = "datos/contexto_matchup.csv"

EPSILON = 1e-6


# ============================================================
# CONFIGURACION POR POSICION
#
# Las variables fueron seleccionadas a partir de los análisis
# históricos V2. No se usan porcentajes de cobertura.
#
# Cada grupo se promedia internamente. Los tres componentes
# disponibles se combinan con el mismo peso: no imponemos
# pesos arbitrarios antes de validar el resultado.
# ============================================================

CONFIG = {
    "ARQ": {
        # Producción/actividad del propio equipo relevante para ARQ.
        "propio": [
            "goalkeeperSaves",
            "ballRecovery",
            "totalClearance",
        ],

        # Producción del rival que determina volumen de trabajo.
        "rival_produccion": [
            "shotsOnGoal",
            "totalShotsOnGoal",
            "expectedGoals",
            "totalShotsInsideBox",
            "touchesInOppBox",
        ],

        # Interacción: volumen ofensivo rival respecto de la
        # capacidad defensiva/actividad del propio equipo.
        "interaccion": [
            "shotsOnGoal",
            "totalShotsOnGoal",
            "expectedGoals",
        ],

        # En ARQ un rival activo genera trabajo.
        "direccion_rival": +1,
        "tipo_interaccion": "rival_vs_propio",
    },

    "DEF": {
        # La evidencia histórica mostró señal positiva para
        # circulación/participación del propio equipo.
        "propio": [
            "passes",
            "accuratePasses",
            "ballPossession",
            "ballRecovery",
            "duelWonPercent",
        ],

        # Para DEF, mayor producción ofensiva rival aumenta
        # el riesgo de perder acciones/bonus defensivos.
        "rival_produccion": [
            "expectedGoals",
            "shotsOnGoal",
            "totalShotsOnGoal",
            "totalShotsInsideBox",
            "touchesInOppBox",
            "ballPossession",
        ],

        # La interacción mide cuánto puede imponer el propio
        # equipo respecto del contexto ofensivo rival.
        "interaccion": [
            "passes",
            "accuratePasses",
            "ballPossession",
            "expectedGoals",
            "shotsOnGoal",
        ],

        "direccion_rival": -1,
        "tipo_interaccion": "propio_vs_rival",
    },

    "VOL": {
        "propio": [
            "passes",
            "accuratePasses",
            "ballPossession",
            "duelWonPercent",
            "ballRecovery",
            "freeKicks",
        ],

        # El análisis histórico mostró relación negativa entre
        # dominio/pases del rival y puntos Winning del volante.
        "rival_produccion": [
            "ballPossession",
            "passes",
            "accuratePasses",
            "duelWonPercent",
            "totalClearance",
        ],

        "interaccion": [
            "passes",
            "accuratePasses",
            "ballPossession",
            "shotsOnGoal",
        ],

        "direccion_rival": -1,
        "tipo_interaccion": "propio_vs_rival",
    },

    "DEL": {
        "propio": [
            "expectedGoals",
            "shotsOnGoal",
            "totalShotsInsideBox",
            "touchesInOppBox",
            "bigChanceCreated",
            "accuratePasses",
            "passes",
        ],

        # Para DEL importa especialmente cuánto concede el rival.
        # En esta sección NO usamos la producción del rival sino
        # sus estadísticas rival_X: lo que el rival suele permitir.
        "rival_concede": [
            "expectedGoals",
            "expectedGoalsOnTarget",
            "shotsOnGoal",
            "totalShotsInsideBox",
            "touchesInOppBox",
            "bigChanceCreated",
        ],

        # Las interacciones xG/xGOT/tiros fueron las señales más
        # fuertes encontradas en el análisis histórico.
        "interaccion": [
            "expectedGoals",
            "expectedGoalsOnTarget",
            "shotsOnGoal",
        ],

        "tipo_interaccion": "propio_vs_concede",
    },
}


# ============================================================
# POSICIONES
# ============================================================

def normalizar_posicion(valor):
    if pd.isna(valor):
        return None

    texto = str(valor).upper().strip()

    if texto in {"GK", "G", "ARQ", "GOALKEEPER", "ARQUERO"}:
        return "ARQ"

    if texto in {"D", "DF", "DEF", "DEFENDER", "DEFENSA"}:
        return "DEF"

    if texto in {"M", "MF", "MID", "VOL", "MIDFIELDER", "VOLANTE"}:
        return "VOL"

    if texto in {"F", "FW", "FWD", "DEL", "FORWARD", "ATTACKER", "DELANTERO"}:
        return "DEL"

    return None


# ============================================================
# PERCENTIL EMPIRICO
# ============================================================

def percentile_rank(valor, serie):
    if pd.isna(valor):
        return np.nan

    serie = pd.to_numeric(serie, errors="coerce").dropna()

    if len(serie) == 0:
        return np.nan

    return float((serie <= valor).sum() / len(serie))


def percentil_previo(valor, serie, fechas, fecha_objetivo):
    """
    Percentil calculado solamente contra observaciones anteriores
    a la fecha objetivo. Esto evita leakage temporal.
    """
    mascara = fechas < fecha_objetivo
    serie_previa = serie.loc[mascara]

    return percentile_rank(valor, serie_previa)


# ============================================================
# CARGA
# ============================================================

print("=" * 60)
print("CREANDO CONTEXTO MATCHUP V3")
print("=" * 60)

df = pd.read_csv(
    ARCHIVO_ENTRADA,
    low_memory=False,
)

print(f"Filas entrada: {len(df)}")

df["fecha_matchup"] = pd.to_datetime(
    df["pitchapi_fecha"],
    errors="coerce",
).dt.normalize()

df["position_normalizada"] = df["position"].apply(
    normalizar_posicion
)


# ============================================================
# RIVAL
# ============================================================

df["rival_team_id"] = np.where(
    df["team_id"] == df["pitchapi_home_team_id"],
    df["pitchapi_away_team_id"],
    np.where(
        df["team_id"] == df["pitchapi_away_team_id"],
        df["pitchapi_home_team_id"],
        np.nan,
    ),
)

df["rival_team_name"] = np.where(
    df["team_id"] == df["pitchapi_home_team_id"],
    df["pitchapi_away_team"],
    np.where(
        df["team_id"] == df["pitchapi_away_team_id"],
        df["pitchapi_home_team"],
        np.nan,
    ),
)


# ============================================================
# VARIABLES NECESARIAS
# ============================================================

todas_variables = set()

for posicion, cfg in CONFIG.items():
    todas_variables.update(cfg.get("propio", []))
    todas_variables.update(cfg.get("rival_produccion", []))
    todas_variables.update(cfg.get("rival_concede", []))
    todas_variables.update(cfg.get("interaccion", []))

variables_disponibles = {
    variable
    for variable in todas_variables
    if f"sofascore_{variable}" in df.columns
    and f"rival_{variable}" in df.columns
}

print(f"Variables conceptuales: {len(todas_variables)}")
print(f"Variables con fuente SofaScore: {len(variables_disponibles)}")


# ============================================================
# TABLA EQUIPO-PARTIDO
#
# Una fila por equipo en cada partido.
#
# sofascore_X = lo que produjo el equipo.
# rival_X     = lo que produjo el rival / lo que este equipo
#               recibió o concedió en ese partido.
# ============================================================

columnas_equipo = [
    "match_id",
    "fecha_matchup",
    "team_id",
    "team_name",
]

for variable in sorted(variables_disponibles):
    columnas_equipo.append(f"sofascore_{variable}")
    columnas_equipo.append(f"rival_{variable}")

columnas_equipo = [
    columna
    for columna in columnas_equipo
    if columna in df.columns
]

df_equipo = (
    df[columnas_equipo]
    .groupby(
        ["match_id", "team_id"],
        as_index=False,
        sort=False,
    )
    .first()
)

# ------------------------------------------------------------
# NORMALIZACION DE LA PERSPECTIVA EQUIPO <-> RIVAL
#
# En contexto_equipos.csv puede ocurrir que una estadistica
# aparezca como NaN en sofascore_X para un equipo, mientras
# que la misma estadistica si exista como rival_X en la fila
# de su oponente. Como cada partido tiene dos perspectivas,
# ambas columnas contienen la misma informacion vista desde
# lados opuestos.
#
# Recuperamos esos valores antes de construir historiales.
# Esto evita que la disponibilidad de PROPIO/RIVAL/INTERACCION
# dependa de si la estadistica vino cargada en una perspectiva
# concreta del partido.
# ------------------------------------------------------------

# Obtener el rival de cada fila equipo-partido.
mapa_rivales = (
    df[["match_id", "team_id", "rival_team_id"]]
    .dropna(subset=["match_id", "team_id"])
    .drop_duplicates(subset=["match_id", "team_id"])
)

df_equipo = df_equipo.merge(
    mapa_rivales,
    on=["match_id", "team_id"],
    how="left",
)

for variable in sorted(variables_disponibles):
    propia = f"sofascore_{variable}"
    concedida = f"rival_{variable}"

    # Perspectiva del rival en el mismo partido.
    contraparte = df_equipo[
        ["match_id", "team_id", propia, concedida]
    ].copy()

    contraparte = contraparte.rename(
        columns={
            "team_id": "_rival_team_id_join",
            propia: "_oponente_sofascore",
            concedida: "_oponente_rival",
        }
    )

    df_equipo = df_equipo.merge(
        contraparte,
        left_on=["match_id", "rival_team_id"],
        right_on=["match_id", "_rival_team_id_join"],
        how="left",
        suffixes=("", "_contraparte"),
    )

    # sofascore_X del equipo = rival_X de la contraparte.
    df_equipo[propia] = df_equipo[propia].combine_first(
        df_equipo["_oponente_rival"]
    )

    # rival_X del equipo = sofascore_X de la contraparte.
    df_equipo[concedida] = df_equipo[concedida].combine_first(
        df_equipo["_oponente_sofascore"]
    )

    df_equipo = df_equipo.drop(
        columns=[
            "_rival_team_id_join",
            "_oponente_sofascore",
            "_oponente_rival",
        ],
        errors="ignore",
    )

df_equipo = df_equipo.sort_values(
    ["fecha_matchup", "match_id", "team_id"]
).reset_index(drop=True)

print(f"Partidos/equipos históricos: {len(df_equipo)}")


# ============================================================
# PRECALCULAR INTERACCIONES DE CADA PARTIDO
#
# Estas distribuciones sirven como referencia histórica.
# Para una fecha objetivo solamente se utilizan filas anteriores.
# ============================================================

for variable in sorted(variables_disponibles):
    columna_propia = f"sofascore_{variable}"
    columna_rival = f"rival_{variable}"

    df_equipo[f"_ratio_{variable}"] = (
        pd.to_numeric(df_equipo[columna_propia], errors="coerce")
        / (
            pd.to_numeric(df_equipo[columna_rival], errors="coerce").abs()
            + EPSILON
        )
    )

    df_equipo[f"_diferencia_{variable}"] = (
        pd.to_numeric(df_equipo[columna_propia], errors="coerce")
        - pd.to_numeric(df_equipo[columna_rival], errors="coerce")
    )


# ============================================================
# INDICES HISTORICOS POR EQUIPO
# ============================================================

historial_equipo = {}

for team_id, grupo in df_equipo.groupby("team_id"):
    historial_equipo[team_id] = grupo.sort_values(
        "fecha_matchup"
    ).copy()


# ============================================================
# RESULTADO
# ============================================================

resultado = df.copy()

resultado["rival_partidos_historicos"] = np.nan
resultado["propio_partidos_historicos"] = np.nan

resultado["matchup_arq"] = np.nan
resultado["matchup_def"] = np.nan
resultado["matchup_vol"] = np.nan
resultado["matchup_del"] = np.nan
resultado["matchup_score"] = np.nan

resultado["matchup_score_propio"] = np.nan
resultado["matchup_score_rival"] = np.nan
resultado["matchup_score_interaccion"] = np.nan

resultado["matchup_variables_usadas"] = np.nan
resultado["matchup_componentes"] = ""


# ============================================================
# FUNCIONES DE COMPONENTES
# ============================================================

def media_percentiles(
    valores,
    series_historicas,
    fechas_historicas,
    fecha_objetivo,
    direccion=+1,
):
    scores = []

    for valor, serie, fechas in zip(
        valores,
        series_historicas,
        fechas_historicas,
    ):
        if pd.isna(valor):
            continue

        score = percentil_previo(
            valor,
            serie,
            fechas,
            fecha_objetivo,
        )

        if pd.isna(score):
            continue

        if direccion < 0:
            score = 1.0 - score

        scores.append(score)

    if not scores:
        return np.nan, 0

    return float(np.mean(scores)), len(scores)


def promedio_historico(grupo, columna):
    if grupo is None or grupo.empty or columna not in grupo.columns:
        return np.nan

    serie = pd.to_numeric(
        grupo[columna],
        errors="coerce",
    ).dropna()

    if serie.empty:
        return np.nan

    return float(serie.mean())


# ============================================================
# PROCESAMIENTO
# ============================================================

total = len(resultado)
contador_con_historial = 0
contador_con_matchup = 0


for indice, fila in resultado.iterrows():

    fecha_objetivo = fila["fecha_matchup"]
    team_id = fila["team_id"]
    rival_id = fila["rival_team_id"]

    if pd.isna(fecha_objetivo):
        continue

    if pd.isna(team_id) or pd.isna(rival_id):
        continue

    posicion = fila["position_normalizada"]

    if posicion not in CONFIG:
        continue

    cfg = CONFIG[posicion]

    historial_propio = historial_equipo.get(team_id)
    historial_rival = historial_equipo.get(rival_id)

    if historial_propio is None or historial_rival is None:
        continue

    historial_propio = historial_propio[
        historial_propio["fecha_matchup"] < fecha_objetivo
    ].copy()

    historial_rival = historial_rival[
        historial_rival["fecha_matchup"] < fecha_objetivo
    ].copy()

    if historial_propio.empty or historial_rival.empty:
        continue

    contador_con_historial += 1

    resultado.at[
        indice,
        "propio_partidos_historicos"
    ] = len(historial_propio)

    resultado.at[
        indice,
        "rival_partidos_historicos"
    ] = len(historial_rival)

    # --------------------------------------------------------
    # COMPONENTE 1: PROPIO EQUIPO
    # --------------------------------------------------------

    propio_valores = []
    propio_series = []
    propio_fechas = []

    for variable in cfg.get("propio", []):
        if variable not in variables_disponibles:
            continue

        columna = f"sofascore_{variable}"

        valor = promedio_historico(
            historial_propio,
            columna,
        )

        if pd.isna(valor):
            continue

        propio_valores.append(valor)

        serie_liga = pd.to_numeric(
            df_equipo[columna],
            errors="coerce",
        )

        propio_series.append(serie_liga)
        propio_fechas.append(df_equipo["fecha_matchup"])

    score_propio, n_propio = media_percentiles(
        propio_valores,
        propio_series,
        propio_fechas,
        fecha_objetivo,
        +1,
    )

    # --------------------------------------------------------
    # COMPONENTE 2: RIVAL
    # --------------------------------------------------------

    rival_valores = []
    rival_series = []
    rival_fechas = []

    if "rival_concede" in cfg:

        # Cuánto suele conceder/permitir el rival.
        for variable in cfg["rival_concede"]:
            if variable not in variables_disponibles:
                continue

            columna = f"rival_{variable}"

            valor = promedio_historico(
                historial_rival,
                columna,
            )

            if pd.isna(valor):
                continue

            rival_valores.append(valor)

            serie_liga = pd.to_numeric(
                df_equipo[columna],
                errors="coerce",
            )

            rival_series.append(serie_liga)
            rival_fechas.append(df_equipo["fecha_matchup"])

        direccion_rival = +1

    else:

        # Producción del rival.
        for variable in cfg.get("rival_produccion", []):
            if variable not in variables_disponibles:
                continue

            # Para medir la producción del rival frente al equipo
            # objetivo usamos rival_X en el historial del propio equipo.
            # Esa columna representa lo que el rival produjo en esos
            # partidos desde la perspectiva del equipo objetivo.
            columna = f"rival_{variable}"

            valor = promedio_historico(
                historial_propio,
                columna,
            )

            if pd.isna(valor):
                continue

            rival_valores.append(valor)

            serie_liga = pd.to_numeric(
                df_equipo[columna],
                errors="coerce",
            )

            rival_series.append(serie_liga)
            rival_fechas.append(df_equipo["fecha_matchup"])

        direccion_rival = cfg.get(
            "direccion_rival",
            +1,
        )

    score_rival, n_rival = media_percentiles(
        rival_valores,
        rival_series,
        rival_fechas,
        fecha_objetivo,
        direccion_rival,
    )

    # --------------------------------------------------------
    # COMPONENTE 3: INTERACCION
    # --------------------------------------------------------

    interaccion_scores = []

    for variable in cfg.get("interaccion", []):

        if variable not in variables_disponibles:
            continue

        columna_propia = f"sofascore_{variable}"
        columna_rival = f"rival_{variable}"

        propio = promedio_historico(
            historial_propio,
            columna_propia,
        )

        if cfg["tipo_interaccion"] == "rival_vs_propio":

            rival = promedio_historico(
                historial_rival,
                f"sofascore_{variable}",
            )

            if pd.isna(propio) or pd.isna(rival):
                continue

            valor_interaccion = (
                rival
                / (abs(propio) + EPSILON)
            )

        elif cfg["tipo_interaccion"] == "propio_vs_concede":

            concede = promedio_historico(
                historial_rival,
                columna_rival,
            )

            if pd.isna(propio) or pd.isna(concede):
                continue

            valor_interaccion = (
                propio
                / (abs(concede) + EPSILON)
            )

        else:

            rival = promedio_historico(
                historial_rival,
                columna_propia,
            )

            if pd.isna(propio) or pd.isna(rival):
                continue

            valor_interaccion = (
                propio
                / (abs(rival) + EPSILON)
            )

        serie_liga = pd.to_numeric(
            df_equipo[f"_ratio_{variable}"],
            errors="coerce",
        )

        # Para rival_vs_propio necesitamos el inverso conceptual.
        # El percentil se calcula sobre la misma escala ratio de
        # partido para mantener una referencia histórica homogénea.
        if cfg["tipo_interaccion"] == "rival_vs_propio":
            valor_para_percentil = 1.0 / (
                valor_interaccion + EPSILON
            )
        else:
            valor_para_percentil = valor_interaccion

        score = percentil_previo(
            valor_para_percentil,
            serie_liga,
            df_equipo["fecha_matchup"],
            fecha_objetivo,
        )

        if pd.isna(score):
            continue

        interaccion_scores.append(score)

    if interaccion_scores:
        score_interaccion = float(
            np.mean(interaccion_scores)
        )
    else:
        score_interaccion = np.nan

    n_interaccion = len(interaccion_scores)

    # --------------------------------------------------------
    # SCORE FINAL
    #
    # Los componentes disponibles pesan igual.
    # No forzamos un 40/30/30 antes de validar.
    # --------------------------------------------------------

    componentes = []

    if not pd.isna(score_propio):
        componentes.append(score_propio)

    if not pd.isna(score_rival):
        componentes.append(score_rival)

    if not pd.isna(score_interaccion):
        componentes.append(score_interaccion)

    if not componentes:
        continue

    score_final = float(np.mean(componentes))

    contador_con_matchup += 1

    resultado.at[indice, "matchup_score"] = score_final
    resultado.at[indice, "matchup_score_propio"] = score_propio
    resultado.at[indice, "matchup_score_rival"] = score_rival
    resultado.at[indice, "matchup_score_interaccion"] = score_interaccion

    resultado.at[
        indice,
        "matchup_variables_usadas"
    ] = n_propio + n_rival + n_interaccion

    resultado.at[
        indice,
        "matchup_componentes"
    ] = (
        f"propio={n_propio};"
        f"rival={n_rival};"
        f"interaccion={n_interaccion}"
    )

    if posicion == "ARQ":
        resultado.at[indice, "matchup_arq"] = score_final
    elif posicion == "DEF":
        resultado.at[indice, "matchup_def"] = score_final
    elif posicion == "VOL":
        resultado.at[indice, "matchup_vol"] = score_final
    elif posicion == "DEL":
        resultado.at[indice, "matchup_del"] = score_final

    if (indice + 1) % 2000 == 0:
        print(
            f"Procesadas: {indice + 1}/{total}"
        )


# ============================================================
# LIMPIEZA
# ============================================================

resultado = resultado.drop(
    columns=[
        "fecha_matchup",
        "position_normalizada",
        "rival_team_id",
    ],
    errors="ignore",
)


# ============================================================
# GUARDAR
# ============================================================

resultado.to_csv(
    ARCHIVO_SALIDA,
    index=False,
)


# ============================================================
# RESUMEN
# ============================================================

print("=" * 60)
print("MATCHUP V3 CREADO CORRECTAMENTE")
print("=" * 60)

print(f"FILAS: {len(resultado)}")
print(f"COLUMNAS: {len(resultado.columns)}")
print(f"ARCHIVO: {ARCHIVO_SALIDA}")
print(f"FILAS CON HISTORIAL: {contador_con_historial}")
print(f"FILAS CON MATCHUP: {contador_con_matchup}")

for columna in [
    "matchup_arq",
    "matchup_def",
    "matchup_vol",
    "matchup_del",
    "matchup_score",
    "matchup_score_propio",
    "matchup_score_rival",
    "matchup_score_interaccion",
]:
    serie = pd.to_numeric(
        resultado[columna],
        errors="coerce",
    ).dropna()

    print()
    print(columna.upper())

    if serie.empty:
        print("Sin datos")
    else:
        print(serie.describe().to_string())


# ============================================================
# MUESTRA
# ============================================================

columnas_muestra = [
    "match_id",
    "date",
    "player_name",
    "team_name",
    "rival_team_name",
    "position",
    "pitchapi_es_local",
    "propio_partidos_historicos",
    "rival_partidos_historicos",
    "matchup_variables_usadas",
    "matchup_componentes",
    "matchup_score_propio",
    "matchup_score_rival",
    "matchup_score_interaccion",
    "matchup_score",
]

columnas_muestra = [
    columna
    for columna in columnas_muestra
    if columna in resultado.columns
]

print()
print("MUESTRA:")

print(
    resultado[
        columnas_muestra
    ]
    .drop_duplicates(
        subset=[
            "match_id",
            "player_name",
        ]
    )
    .head(20)
    .to_string(index=False)
)
