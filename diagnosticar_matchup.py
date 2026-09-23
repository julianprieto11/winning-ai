import pandas as pd
import numpy as np

# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO_ENTRADA = "datos/contexto_matchup.csv"

ARCHIVO_GENERAL = "datos/diagnostico_matchup_general.csv"
ARCHIVO_POSICION = "datos/diagnostico_matchup_posicion.csv"


# ============================================================
# VARIABLES DE CONTEXTO
# ============================================================

VARIABLES_CONTEXTO = [
    "sofascore_ballPossession",
    "rival_ballPossession",

    "sofascore_totalShotsOnGoal",
    "rival_totalShotsOnGoal",

    "sofascore_shotsOnGoal",
    "rival_shotsOnGoal",

    "sofascore_shotsOffGoal",
    "rival_shotsOffGoal",

    "sofascore_blockedScoringAttempt",
    "rival_blockedScoringAttempt",

    "sofascore_totalShotsInsideBox",
    "rival_totalShotsInsideBox",

    "sofascore_totalShotsOutsideBox",
    "rival_totalShotsOutsideBox",

    "sofascore_expectedGoals",
    "rival_expectedGoals",

    "sofascore_expectedGoalsOnTarget",
    "rival_expectedGoalsOnTarget",

    "sofascore_bigChanceCreated",
    "rival_bigChanceCreated",

    "sofascore_bigChanceMissed",
    "rival_bigChanceMissed",

    "sofascore_touchesInOppBox",
    "rival_touchesInOppBox",

    "sofascore_finalThirdEntries",
    "rival_finalThirdEntries",

    "sofascore_fouledFinalThird",
    "rival_fouledFinalThird",

    "sofascore_cornerKicks",
    "rival_cornerKicks",

    "sofascore_fouls",
    "rival_fouls",

    "sofascore_passes",
    "rival_passes",

    "sofascore_accuratePasses",
    "rival_accuratePasses",

    "sofascore_accurateCross",
    "rival_accurateCross",

    "sofascore_accurateLongBalls",
    "rival_accurateLongBalls",

    "sofascore_duelWonPercent",
    "rival_duelWonPercent",

    "sofascore_dispossessed",
    "rival_dispossessed",

    "sofascore_groundDuelsPercentage",
    "rival_groundDuelsPercentage",

    "sofascore_aerialDuelsPercentage",
    "rival_aerialDuelsPercentage",

    "sofascore_dribblesPercentage",
    "rival_dribblesPercentage",

    "sofascore_wonTacklePercent",
    "rival_wonTacklePercent",

    "sofascore_totalTackle",
    "rival_totalTackle",

    "sofascore_interceptionWon",
    "rival_interceptionWon",

    "sofascore_ballRecovery",
    "rival_ballRecovery",

    "sofascore_totalClearance",
    "rival_totalClearance",

    "sofascore_goalkeeperSaves",
    "rival_goalkeeperSaves",

    "sofascore_freeKicks",
    "rival_freeKicks",

    "sofascore_offsides",
    "rival_offsides",

    "sofascore_yellowCards",
    "rival_yellowCards",

    "sofascore_errorsLeadToShot",
    "rival_errorsLeadToShot",

    "sofascore_errorsLeadToGoal",
    "rival_errorsLeadToGoal",
]


# ============================================================
# CARGAR DATOS
# ============================================================

print("=" * 60)
print("DIAGNÓSTICO DE VARIABLES MATCHUP")
print("=" * 60)

df = pd.read_csv(ARCHIVO_ENTRADA)

print(f"Filas totales: {len(df)}")

# Solo registros con Winning válido
df = df[
    df["winning_total"].notna()
].copy()

print(f"Filas válidas: {len(df)}")

print()


# ============================================================
# FUNCIÓN DE CORRELACIÓN
# ============================================================

def calcular_correlacion(datos, variable):
    """
    Calcula Pearson y Spearman entre una variable
    y winning_total.
    """

    temp = datos[[variable, "winning_total"]].copy()

    temp[variable] = pd.to_numeric(
        temp[variable],
        errors="coerce"
    )

    temp["winning_total"] = pd.to_numeric(
        temp["winning_total"],
        errors="coerce"
    )

    temp = temp.dropna()

    if len(temp) < 20:
        return {
            "n": len(temp),
            "pearson": np.nan,
            "spearman": np.nan
        }

    pearson = temp[variable].corr(
        temp["winning_total"],
        method="pearson"
    )

    spearman = temp[variable].corr(
        temp["winning_total"],
        method="spearman"
    )

    return {
        "n": len(temp),
        "pearson": pearson,
        "spearman": spearman
    }


# ============================================================
# DIAGNÓSTICO GENERAL
# ============================================================

resultados = []

for variable in VARIABLES_CONTEXTO:

    if variable not in df.columns:
        continue

    resultado = calcular_correlacion(
        df,
        variable
    )

    resultados.append({
        "variable": variable,
        "n": resultado["n"],
        "pearson": resultado["pearson"],
        "spearman": resultado["spearman"]
    })


diagnostico_general = pd.DataFrame(resultados)

diagnostico_general["abs_spearman"] = (
    diagnostico_general["spearman"].abs()
)

diagnostico_general = diagnostico_general.sort_values(
    "abs_spearman",
    ascending=False
)

diagnostico_general.to_csv(
    ARCHIVO_GENERAL,
    index=False
)


# ============================================================
# MOSTRAR RESULTADOS GENERALES
# ============================================================

print("=" * 60)
print("VARIABLES CON MAYOR CORRELACIÓN")
print("=" * 60)

print(
    diagnostico_general[
        [
            "variable",
            "n",
            "pearson",
            "spearman"
        ]
    ].head(25).to_string(
        index=False
    )
)

print()


# ============================================================
# DIAGNÓSTICO POR POSICIÓN
# ============================================================

resultados_posicion = []

posiciones = ["ARQ", "DEF", "VOL", "DEL"]

for posicion in posiciones:

    subset = df[
        df["position"].astype(str).str.upper() == posicion
    ].copy()

    print("=" * 60)
    print(f"POSICIÓN: {posicion}")
    print("=" * 60)

    print(f"Registros: {len(subset)}")

    for variable in VARIABLES_CONTEXTO:

        if variable not in subset.columns:
            continue

        resultado = calcular_correlacion(
            subset,
            variable
        )

        resultados_posicion.append({
            "position": posicion,
            "variable": variable,
            "n": resultado["n"],
            "pearson": resultado["pearson"],
            "spearman": resultado["spearman"],
            "abs_spearman": (
                abs(resultado["spearman"])
                if pd.notna(resultado["spearman"])
                else np.nan
            )
        })

    temp_pos = pd.DataFrame(
        [
            x for x in resultados_posicion
            if x["position"] == posicion
        ]
    )

    temp_pos = temp_pos.sort_values(
        "abs_spearman",
        ascending=False
    )

    print(
        temp_pos[
            [
                "variable",
                "n",
                "pearson",
                "spearman"
            ]
        ].head(15).to_string(
            index=False
        )
    )

    print()


# ============================================================
# GUARDAR POR POSICIÓN
# ============================================================

diagnostico_posicion = pd.DataFrame(
    resultados_posicion
)

diagnostico_posicion.to_csv(
    ARCHIVO_POSICION,
    index=False
)


# ============================================================
# VARIABLES MATCHUP ACTUALES
# ============================================================

print("=" * 60)
print("CORRELACIÓN DE LOS MATCHUP ACTUALES")
print("=" * 60)

for variable in [
    "matchup_arq",
    "matchup_def",
    "matchup_vol",
    "matchup_del",
    "matchup_score"
]:

    if variable not in df.columns:
        continue

    resultado = calcular_correlacion(
        df,
        variable
    )

    print(
        f"{variable}: "
        f"n={resultado['n']} | "
        f"Pearson={resultado['pearson']:.4f} | "
        f"Spearman={resultado['spearman']:.4f}"
    )

print()


# ============================================================
# FINAL
# ============================================================

print("=" * 60)
print("DIAGNÓSTICO FINALIZADO")
print("=" * 60)

print("Archivos generados:")
print(ARCHIVO_GENERAL)
print(ARCHIVO_POSICION)