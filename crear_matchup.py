import pandas as pd
import numpy as np


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO_ENTRADA = "datos/contexto_equipos.csv"
ARCHIVO_SALIDA = "datos/contexto_matchup.csv"

MIN_PARTIDOS_RIVAL = 3


# ============================================================
# VARIABLES MATCHUP POR POSICIÓN
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


# ============================================================
# DIRECCIÓN SEMÁNTICA
#
# +1 = un valor alto aumenta el contexto positivo
# -1 = un valor alto aumenta la dificultad
# ============================================================

DIRECCION = {}


def agregar_direccion(variables, direccion):
    for variable in variables:
        DIRECCION[variable] = direccion


# ------------------------------------------------------------
# ARQUERO
#
# Más producción ofensiva rival = más trabajo para ARQ.
# ------------------------------------------------------------

agregar_direccion([
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
], +1)


# ------------------------------------------------------------
# DEFENSA
#
# Más ataques del rival = más volumen defensivo.
# Errores rivales también generan oportunidades defensivas.
# ------------------------------------------------------------

agregar_direccion([
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
], +1)


# ------------------------------------------------------------
# VOLANTE
#
# Buscamos intensidad y volumen de interacción.
# ------------------------------------------------------------

agregar_direccion([
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
], +1)


# ------------------------------------------------------------
# DELANTERO
#
# Volumen ofensivo rival crea contexto de partido.
#
# Pero un rival fuerte en duelos representa mayor dificultad
# directa para el delantero.
# ------------------------------------------------------------

agregar_direccion([
    "rival_expectedGoals",
    "rival_totalShotsOnGoal",
    "rival_shotsOnGoal",
    "rival_totalShotsInsideBox",
    "rival_touchesInOppBox",
    "rival_bigChanceCreated",
    "rival_bigChanceMissed",
    "rival_fouls",
    "rival_fouledFinalThird",
    "rival_dispossessed",
    "rival_errorsLeadToShot",
    "rival_errorsLeadToGoal",
], +1)

agregar_direccion([
    "rival_duelWonPercent",
    "rival_groundDuelsPercentage",
    "rival_aerialDuelsPercentage",
], -1)


# ============================================================
# NORMALIZAR POSICIÓN
# ============================================================

def normalizar_posicion(valor):

    if pd.isna(valor):
        return None

    texto = str(valor).upper().strip()

    if texto in ["GK", "G", "ARQ", "GOALKEEPER"]:
        return "ARQ"

    if texto in ["D", "DF", "DEF", "DEFENDER"]:
        return "DEF"

    if texto in ["M", "MF", "MID", "VOL", "MIDFIELDER"]:
        return "VOL"

    if texto in ["F", "FW", "DEL", "FORWARD", "ATTACKER"]:
        return "DEL"

    return None


# ============================================================
# PERCENTIL EMPÍRICO
# ============================================================

def percentile_rank(valor, serie):

    if pd.isna(valor):
        return np.nan

    serie = pd.to_numeric(
        serie,
        errors="coerce"
    ).dropna()

    if len(serie) == 0:
        return np.nan

    return (
        (serie <= valor).sum()
        / len(serie)
    )


# ============================================================
# CARGA
# ============================================================

print("=" * 60)
print("CREANDO CONTEXTO MATCHUP")
print("=" * 60)

df = pd.read_csv(
    ARCHIVO_ENTRADA,
    low_memory=False
)

print(
    f"Filas entrada: {len(df)}"
)


# ============================================================
# FECHA Y POSICIÓN
# ============================================================

df["fecha_matchup"] = pd.to_datetime(
    df["pitchapi_fecha"],
    errors="coerce"
)

df["position_normalizada"] = (
    df["position"].apply(
        normalizar_posicion
    )
)


# ============================================================
# IDENTIFICAR RIVAL
# ============================================================

df["rival_team_id"] = np.where(
    df["team_id"] == df["pitchapi_home_team_id"],
    df["pitchapi_away_team_id"],
    np.where(
        df["team_id"] == df["pitchapi_away_team_id"],
        df["pitchapi_home_team_id"],
        np.nan
    )
)

df["rival_team_name"] = np.where(
    df["team_id"] == df["pitchapi_home_team_id"],
    df["pitchapi_away_team"],
    np.where(
        df["team_id"] == df["pitchapi_away_team_id"],
        df["pitchapi_home_team"],
        np.nan
    )
)


# ============================================================
# TODAS LAS VARIABLES
# ============================================================

VARIABLES_MATCHUP = sorted(
    set(
        VARIABLES_ARQ
        + VARIABLES_DEF
        + VARIABLES_VOL
        + VARIABLES_DEL
    )
)

print(
    f"Variables MATCHUP: {len(VARIABLES_MATCHUP)}"
)


# ============================================================
# MAPEO FUNDAMENTAL
#
# El MATCHUP usa nombres:
#
#     rival_expectedGoals
#
# Pero para construir el HISTORIAL DEL RIVAL debemos mirar:
#
#     sofascore_expectedGoals
#
# porque queremos saber cuánto produjo el rival en sus propios
# partidos anteriores.
# ============================================================

MAPA_VARIABLES = {}

for variable_rival in VARIABLES_MATCHUP:

    nombre_base = variable_rival.replace(
        "rival_",
        "",
        1
    )

    columna_propia = (
        "sofascore_" + nombre_base
    )

    if columna_propia in df.columns:
        MAPA_VARIABLES[
            variable_rival
        ] = columna_propia


print(
    f"Variables con fuente SofaScore: "
    f"{len(MAPA_VARIABLES)}"
)


# ============================================================
# TABLA EQUIPO-PARTIDO
#
# Una fila por:
#
#     match_id + team_id
#
# Las estadísticas propias salen de sofascore_*.
# ============================================================

columnas_base = [
    "match_id",
    "fecha_matchup",
    "team_id",
    "team_name",
]

columnas_estadisticas = sorted(
    set(
        MAPA_VARIABLES.values()
    )
)

columnas_equipo = (
    columnas_base
    + columnas_estadisticas
)

df_equipo = (
    df[columnas_equipo]
    .groupby(
        ["match_id", "team_id"],
        as_index=False,
        sort=False
    )
    .first()
)

print(
    f"Partidos/equipos históricos: "
    f"{len(df_equipo)}"
)


# ============================================================
# HISTORIAL POR EQUIPO
# ============================================================

historial_equipo = {}

for team_id, grupo in df_equipo.groupby(
    "team_id"
):

    grupo = grupo.sort_values(
        "fecha_matchup"
    )

    historial_equipo[
        team_id
    ] = grupo


# ============================================================
# RESULTADO
# ============================================================

resultado = df.copy()

resultado["rival_partidos_historicos"] = np.nan

resultado["matchup_arq"] = np.nan
resultado["matchup_def"] = np.nan
resultado["matchup_vol"] = np.nan
resultado["matchup_del"] = np.nan
resultado["matchup_score"] = np.nan

resultado["matchup_variables_usadas"] = np.nan


# ============================================================
# PROCESAMIENTO
# ============================================================

total = len(resultado)

contador_historial = 0


for indice, fila in resultado.iterrows():

    fecha_objetivo = fila[
        "fecha_matchup"
    ]

    rival_id = fila[
        "rival_team_id"
    ]

    if pd.isna(fecha_objetivo):
        continue

    if pd.isna(rival_id):
        continue


    # ========================================================
    # HISTORIAL DEL RIVAL
    # ========================================================

    historial_rival = historial_equipo.get(
        rival_id
    )

    if historial_rival is None:
        continue


    # SOLO PARTIDOS ANTERIORES
    historial_rival = historial_rival[
        historial_rival[
            "fecha_matchup"
        ] < fecha_objetivo
    ]


    if len(historial_rival) < MIN_PARTIDOS_RIVAL:
        continue


    contador_historial += 1

    resultado.at[
        indice,
        "rival_partidos_historicos"
    ] = len(historial_rival)


    # ========================================================
    # POSICIÓN
    # ========================================================

    posicion = fila[
        "position_normalizada"
    ]

    if posicion == "ARQ":

        variables_posicion = VARIABLES_ARQ

    elif posicion == "DEF":

        variables_posicion = VARIABLES_DEF

    elif posicion == "VOL":

        variables_posicion = VARIABLES_VOL

    elif posicion == "DEL":

        variables_posicion = VARIABLES_DEL

    else:
        continue


    scores = []


    # ========================================================
    # PROCESAR CADA VARIABLE
    # ========================================================

    for variable_rival in variables_posicion:

        columna_propia = MAPA_VARIABLES.get(
            variable_rival
        )

        if columna_propia is None:
            continue


        # ----------------------------------------------------
        # HISTORIAL DEL RIVAL
        # ----------------------------------------------------

        serie_rival = pd.to_numeric(
            historial_rival[
                columna_propia
            ],
            errors="coerce"
        ).dropna()


        if len(serie_rival) == 0:
            continue


        promedio_rival = (
            serie_rival.mean()
        )


        # ----------------------------------------------------
        # HISTORIAL DE TODA LA LIGA
        #
        # Solamente partidos anteriores.
        # ----------------------------------------------------

        liga_previa = df_equipo[
            df_equipo[
                "fecha_matchup"
            ] < fecha_objetivo
        ]


        serie_liga = pd.to_numeric(
            liga_previa[
                columna_propia
            ],
            errors="coerce"
        ).dropna()


        if len(serie_liga) == 0:
            continue


        # ----------------------------------------------------
        # PERCENTIL DEL RIVAL
        # ----------------------------------------------------

        percentil = percentile_rank(
            promedio_rival,
            serie_liga
        )


        if pd.isna(percentil):
            continue


        # ----------------------------------------------------
        # DIRECCIÓN
        # ----------------------------------------------------

        direccion = DIRECCION.get(
            variable_rival,
            +1
        )


        if direccion < 0:
            percentil = (
                1.0 - percentil
            )


        scores.append(
            percentil
        )


    # ========================================================
    # SCORE
    # ========================================================

    if len(scores) == 0:
        continue


    score = float(
        np.mean(scores)
    )


    if posicion == "ARQ":

        resultado.at[
            indice,
            "matchup_arq"
        ] = score

    elif posicion == "DEF":

        resultado.at[
            indice,
            "matchup_def"
        ] = score

    elif posicion == "VOL":

        resultado.at[
            indice,
            "matchup_vol"
        ] = score

    elif posicion == "DEL":

        resultado.at[
            indice,
            "matchup_del"
        ] = score


    resultado.at[
        indice,
        "matchup_score"
    ] = score


    resultado.at[
        indice,
        "matchup_variables_usadas"
    ] = len(scores)


    # ========================================================
    # PROGRESO
    # ========================================================

    if (indice + 1) % 2000 == 0:

        print(
            f"Procesadas: "
            f"{indice + 1}/{total}"
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
    errors="ignore"
)


# ============================================================
# GUARDAR
# ============================================================

resultado.to_csv(
    ARCHIVO_SALIDA,
    index=False
)


# ============================================================
# RESUMEN
# ============================================================

print("=" * 60)
print("MATCHUP CREADO CORRECTAMENTE")
print("=" * 60)

print(
    f"FILAS: {len(resultado)}"
)

print(
    f"COLUMNAS: {len(resultado.columns)}"
)

print(
    f"ARCHIVO: {ARCHIVO_SALIDA}"
)

print(
    f"FILAS CON HISTORIAL DEL RIVAL: "
    f"{contador_historial}"
)


for columna in [
    "matchup_arq",
    "matchup_def",
    "matchup_vol",
    "matchup_del",
    "matchup_score",
]:

    serie = resultado[
        columna
    ].dropna()

    print()
    print(
        columna.upper()
    )

    if len(serie) == 0:

        print(
            "Sin datos"
        )

    else:

        print(
            serie.describe().to_string()
        )


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
    "rival_partidos_historicos",
    "matchup_variables_usadas",
    "matchup_arq",
    "matchup_def",
    "matchup_vol",
    "matchup_del",
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
            "player_name"
        ]
    )
    .head(20)
    .to_string(index=False)
)