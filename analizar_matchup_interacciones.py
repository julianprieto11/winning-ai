import pandas as pd
import numpy as np

# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO_JUGADORES = "datos/contexto_matchup.csv"
ARCHIVO_EQUIPOS = "datos/contexto_equipos_historico.csv"

ARCHIVO_SALIDA = "datos/analisis_matchup_interacciones.csv"

# ============================================================
# CARGAR DATOS
# ============================================================

print("=" * 70)
print("ANÁLISIS MATCHUP V2 - INTERACCIONES PROPIO VS RIVAL")
print("=" * 70)

jugadores = pd.read_csv(ARCHIVO_JUGADORES)
equipos = pd.read_csv(ARCHIVO_EQUIPOS)

jugadores["date"] = pd.to_datetime(jugadores["date"])
equipos["date"] = pd.to_datetime(equipos["date"])

print(f"Filas jugadores: {len(jugadores)}")
print(f"Filas equipos: {len(equipos)}")

# ============================================================
# PREPARAR HISTÓRICO DE EQUIPOS
# ============================================================

equipos = equipos.drop_duplicates(
    subset=["date", "team_id"],
    keep="first"
)

# ============================================================
# VARIABLES BASE
# ============================================================

variables_base = [
    "ballPossession",
    "totalShotsOnGoal",
    "shotsOnGoal",
    "shotsOffGoal",
    "totalShotsInsideBox",
    "totalShotsOutsideBox",
    "expectedGoals",
    "expectedGoalsOnTarget",
    "bigChanceCreated",
    "bigChanceMissed",
    "touchesInOppBox",
    "finalThirdEntries",
    "fouledFinalThird",
    "cornerKicks",
    "fouls",
    "passes",
    "accuratePasses",
    "accurateCross",
    "accurateLongBalls",
    "duelWonPercent",
    "dispossessed",
    "groundDuelsPercentage",
    "aerialDuelsPercentage",
    "dribblesPercentage",
    "wonTacklePercent",
    "totalTackle",
    "interceptionWon",
    "ballRecovery",
    "totalClearance",
    "goalkeeperSaves",
    "freeKicks",
    "offsides",
    "yellowCards",
    "blockedScoringAttempt",
]

# ============================================================
# UNIR HISTÓRICO
# ============================================================

columnas_equipos = [
    "date",
    "team_id",
]

for variable in variables_base:

    propia = f"historico_{variable}"
    rival = f"rival_historico_{variable}"

    if propia in equipos.columns:
        columnas_equipos.append(propia)

    if rival in equipos.columns:
        columnas_equipos.append(rival)

df = jugadores.merge(
    equipos[columnas_equipos],
    on=["date", "team_id"],
    how="left",
    validate="many_to_one"
)

print(
    f"Filas después de unir histórico: {len(df)}"
)

# ============================================================
# CREAR VARIABLES DE INTERACCIÓN
# ============================================================

print()
print("Creando variables de matchup...")

nuevas_variables = []

for variable in variables_base:

    propia = f"historico_{variable}"
    rival = f"rival_historico_{variable}"

    if propia not in df.columns or rival not in df.columns:
        continue

    # --------------------------------------------------------
    # DIFERENCIA
    # --------------------------------------------------------

    nombre_diferencia = f"matchup_diferencia_{variable}"

    df[nombre_diferencia] = (
        df[propia] - df[rival]
    )

    nuevas_variables.append(
        nombre_diferencia
    )

    # --------------------------------------------------------
    # RATIO
    # --------------------------------------------------------
    #
    # Solo se calcula cuando el rival es distinto de cero.
    # Si el rival es 0, dejamos NaN.
    #

    nombre_ratio = f"matchup_ratio_{variable}"

    df[nombre_ratio] = np.where(
        df[rival].notna() & (df[rival] != 0),
        df[propia] / df[rival],
        np.nan
    )

    nuevas_variables.append(
        nombre_ratio
    )

# ============================================================
# VARIABLES ESPECÍFICAS POR BLOQUE
# ============================================================

# ------------------------------------------------------------
# ATAQUE PROPIO
# ------------------------------------------------------------

ataque_propio = {
    "xg": "historico_expectedGoals",
    "xgot": "historico_expectedGoalsOnTarget",
    "tiros_arco": "historico_shotsOnGoal",
    "grandes_ocasion": "historico_bigChanceCreated",
    "entradas_area": "historico_touchesInOppBox",
    "ultimo_tercio": "historico_finalThirdEntries",
}

# ------------------------------------------------------------
# ATAQUE RIVAL
# ------------------------------------------------------------

ataque_rival = {
    "xg": "rival_historico_expectedGoals",
    "xgot": "rival_historico_expectedGoalsOnTarget",
    "tiros_arco": "rival_historico_shotsOnGoal",
    "grandes_ocasion": "rival_historico_bigChanceCreated",
    "entradas_area": "rival_historico_touchesInOppBox",
    "ultimo_tercio": "rival_historico_finalThirdEntries",
}

# ------------------------------------------------------------
# FUNCIÓN PARA CREAR RATIO/DIFERENCIA DE BLOQUES
# ------------------------------------------------------------

def crear_interaccion(
    nombre,
    columna_propia,
    columna_rival
):

    if (
        columna_propia not in df.columns
        or columna_rival not in df.columns
    ):
        return

    diferencia = (
        f"matchup_{nombre}_diferencia"
    )

    ratio = (
        f"matchup_{nombre}_ratio"
    )

    df[diferencia] = (
        df[columna_propia]
        - df[columna_rival]
    )

    df[ratio] = np.where(
        df[columna_rival].notna()
        & (df[columna_rival] != 0),
        df[columna_propia]
        / df[columna_rival],
        np.nan
    )

    nuevas_variables.append(diferencia)
    nuevas_variables.append(ratio)


# ============================================================
# INTERACCIONES OFENSIVAS
# ============================================================

for nombre in ataque_propio:

    crear_interaccion(
        f"ataque_{nombre}",
        ataque_propio[nombre],
        ataque_rival[nombre]
    )

# ============================================================
# CONTEXTO DE PELOTA PARADA
# ============================================================

crear_interaccion(
    "pelota_parada_faltas",
    "historico_fouledFinalThird",
    "rival_historico_fouls"
)

crear_interaccion(
    "pelota_parada_faltas_cometidas",
    "historico_fouls",
    "rival_historico_fouledFinalThird"
)

crear_interaccion(
    "corners",
    "historico_cornerKicks",
    "rival_historico_cornerKicks"
)

# ============================================================
# CONTEXTO DE POSESIÓN Y PASE
# ============================================================

crear_interaccion(
    "posesion",
    "historico_ballPossession",
    "rival_historico_ballPossession"
)

crear_interaccion(
    "pases",
    "historico_passes",
    "rival_historico_passes"
)

crear_interaccion(
    "pases_precisos",
    "historico_accuratePasses",
    "rival_historico_accuratePasses"
)

# ============================================================
# CONTEXTO DE DUELOS
# ============================================================

crear_interaccion(
    "duelos",
    "historico_duelWonPercent",
    "rival_historico_duelWonPercent"
)

crear_interaccion(
    "duelos_terrestres",
    "historico_groundDuelsPercentage",
    "rival_historico_groundDuelsPercentage"
)

crear_interaccion(
    "duelos_aereos",
    "historico_aerialDuelsPercentage",
    "rival_historico_aerialDuelsPercentage"
)

# ============================================================
# CONTEXTO DEFENSIVO
# ============================================================

crear_interaccion(
    "recuperaciones",
    "historico_ballRecovery",
    "rival_historico_ballRecovery"
)

crear_interaccion(
    "intercepciones",
    "historico_interceptionWon",
    "rival_historico_interceptionWon"
)

crear_interaccion(
    "tackles",
    "historico_totalTackle",
    "rival_historico_totalTackle"
)

crear_interaccion(
    "despejes",
    "historico_totalClearance",
    "rival_historico_totalClearance"
)

# ============================================================
# FUNCIÓN DE ANÁLISIS
# ============================================================

def analizar(grupo, nombre_grupo):

    resultados = []

    for variable in nuevas_variables:

        temp = grupo[
            [variable, "winning_total"]
        ].copy()

        temp[variable] = pd.to_numeric(
            temp[variable],
            errors="coerce"
        )

        temp["winning_total"] = pd.to_numeric(
            temp["winning_total"],
            errors="coerce"
        )

        temp = temp.dropna()

        n = len(temp)

        if n < 10:
            continue

        if temp[variable].nunique() < 2:
            continue

        if temp["winning_total"].nunique() < 2:
            continue

        pearson = temp[variable].corr(
            temp["winning_total"],
            method="pearson"
        )

        spearman = temp[variable].corr(
            temp["winning_total"],
            method="spearman"
        )

        resultados.append({
            "grupo": nombre_grupo,
            "variable": variable,
            "n": n,
            "pearson": pearson,
            "spearman": spearman,
            "abs_pearson": abs(pearson),
            "abs_spearman": abs(spearman),
        })

    resultado = pd.DataFrame(resultados)

    if not resultado.empty:

        resultado = resultado.sort_values(
            "abs_spearman",
            ascending=False
        )

    return resultado


# ============================================================
# ANÁLISIS GENERAL
# ============================================================

print()
print("Analizando interacciones generales...")

resultados = []

resultado_general = analizar(
    df,
    "GENERAL"
)

resultados.append(resultado_general)

# ============================================================
# ANÁLISIS POR POSICIÓN
# ============================================================

print()
print("Analizando por posición...")

for posicion in [
    "ARQ",
    "DEF",
    "VOL",
    "DEL",
]:

    grupo = df[
        df["position"] == posicion
    ].copy()

    print(
        f"  {posicion}: {len(grupo)} filas"
    )

    resultado = analizar(
        grupo,
        posicion
    )

    resultados.append(resultado)

# ============================================================
# UNIR RESULTADOS
# ============================================================

resultado_final = pd.concat(
    resultados,
    ignore_index=True
)

resultado_final = resultado_final.sort_values(
    ["grupo", "abs_spearman"],
    ascending=[True, False]
)

resultado_final.to_csv(
    ARCHIVO_SALIDA,
    index=False,
    encoding="utf-8-sig"
)

# ============================================================
# MOSTRAR RESULTADOS
# ============================================================

pd.set_option("display.max_rows", 200)
pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 220)

for grupo in [
    "GENERAL",
    "ARQ",
    "DEF",
    "VOL",
    "DEL",
]:

    print()
    print("=" * 70)
    print(f"TOP INTERACCIONES - {grupo}")
    print("=" * 70)

    x = resultado_final[
        resultado_final["grupo"] == grupo
    ].head(30)

    if not x.empty:

        print(
            x[
                [
                    "variable",
                    "n",
                    "pearson",
                    "spearman",
                ]
            ].to_string(index=False)
        )

print()
print("=" * 70)
print("ANÁLISIS FINALIZADO")
print("=" * 70)

print()
print(
    f"Variables de interacción creadas: "
    f"{len(nuevas_variables)}"
)

print(
    f"Archivo: {ARCHIVO_SALIDA}"
)