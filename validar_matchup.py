import pandas as pd
import numpy as np


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO = "datos/contexto_matchup.csv"


# ============================================================
# CARGA
# ============================================================

print("=" * 60)
print("VALIDACIÓN HISTÓRICA DEL MATCHUP")
print("=" * 60)

df = pd.read_csv(
    ARCHIVO,
    low_memory=False
)

print(f"Filas totales: {len(df)}")


# ============================================================
# LIMPIEZA
# ============================================================

columnas_necesarias = [
    "matchup_score",
    "winning_total",
    "position",
    "player_name",
    "team_name",
    "match_id",
    "date",
]

faltantes = [
    columna
    for columna in columnas_necesarias
    if columna not in df.columns
]

if faltantes:
    print()
    print("ERROR: faltan columnas:")
    print(faltantes)
    raise SystemExit


df["matchup_score"] = pd.to_numeric(
    df["matchup_score"],
    errors="coerce"
)

df["winning_total"] = pd.to_numeric(
    df["winning_total"],
    errors="coerce"
)


df_validos = df[
    df["matchup_score"].notna()
    & df["winning_total"].notna()
].copy()


print(
    f"Filas válidas para analizar: "
    f"{len(df_validos)}"
)


if len(df_validos) == 0:
    print("No hay filas válidas.")
    raise SystemExit


# ============================================================
# CUARTILES DEL MATCHUP
# ============================================================

q1 = df_validos[
    "matchup_score"
].quantile(0.25)

q2 = df_validos[
    "matchup_score"
].quantile(0.50)

q3 = df_validos[
    "matchup_score"
].quantile(0.75)


def clasificar_matchup(valor):

    if valor <= q1:
        return "BAJO"

    if valor <= q3:
        return "MEDIO"

    return "ALTO"


df_validos["nivel_matchup"] = (
    df_validos["matchup_score"].apply(
        clasificar_matchup
    )
)


# ============================================================
# RESULTADOS GENERALES
# ============================================================

print()
print("=" * 60)
print("PUNTOS WINNING SEGÚN NIVEL MATCHUP")
print("=" * 60)

resumen = (
    df_validos
    .groupby("nivel_matchup", observed=True)
    .agg(
        jugadores=("winning_total", "count"),
        matchup_promedio=("matchup_score", "mean"),
        winning_promedio=("winning_total", "mean"),
        winning_mediana=("winning_total", "median"),
        winning_maximo=("winning_total", "max"),
    )
    .reindex(["BAJO", "MEDIO", "ALTO"])
)

print(
    resumen.to_string(
        float_format=lambda x: f"{x:.3f}"
    )
)


# ============================================================
# RESULTADOS POR POSICIÓN
# ============================================================

print()
print("=" * 60)
print("RESULTADOS POR POSICIÓN")
print("=" * 60)

resumen_posicion = (
    df_validos
    .groupby(
        ["position", "nivel_matchup"],
        observed=True
    )
    .agg(
        jugadores=("winning_total", "count"),
        matchup_promedio=("matchup_score", "mean"),
        winning_promedio=("winning_total", "mean"),
        winning_mediana=("winning_total", "median"),
        winning_maximo=("winning_total", "max"),
    )
    .reset_index()
)

print(
    resumen_posicion.to_string(
        index=False,
        float_format=lambda x: f"{x:.3f}"
    )
)


# ============================================================
# CORRELACIÓN GENERAL
# ============================================================

print()
print("=" * 60)
print("CORRELACIÓN")
print("=" * 60)

correlacion_general = df_validos[
    [
        "matchup_score",
        "winning_total",
    ]
].corr().iloc[0, 1]

print(
    "Correlación MATCHUP vs Winning: "
    f"{correlacion_general:.4f}"
)


# ============================================================
# CORRELACIÓN POR POSICIÓN
# ============================================================

print()
print("CORRELACIÓN POR POSICIÓN")

for posicion, grupo in df_validos.groupby(
    "position",
    dropna=True
):

    if len(grupo) < 5:
        continue

    correlacion = grupo[
        [
            "matchup_score",
            "winning_total",
        ]
    ].corr().iloc[0, 1]

    print(
        f"{posicion}: "
        f"{correlacion:.4f} "
        f"({len(grupo)} registros)"
    )


# ============================================================
# VALORES EXTREMOS
# ============================================================

print()
print("=" * 60)
print("MATCHUP MÁS ALTOS")
print("=" * 60)

columnas_muestra = [
    "date",
    "match_id",
    "player_name",
    "team_name",
    "position",
    "matchup_score",
    "winning_total",
]

print(
    df_validos
    .sort_values(
        "matchup_score",
        ascending=False
    )[columnas_muestra]
    .head(15)
    .to_string(index=False)
)


print()
print("=" * 60)
print("MATCHUP MÁS BAJOS")
print("=" * 60)

print(
    df_validos
    .sort_values(
        "matchup_score",
        ascending=True
    )[columnas_muestra]
    .head(15)
    .to_string(index=False)
)


# ============================================================
# GUARDAR RESUMEN
# ============================================================

resumen.to_csv(
    "datos/validacion_matchup_resumen.csv"
)

resumen_posicion.to_csv(
    "datos/validacion_matchup_posicion.csv",
    index=False
)


print()
print("=" * 60)
print("VALIDACIÓN FINALIZADA")
print("=" * 60)

print(
    "Archivos generados:"
)

print(
    "datos/validacion_matchup_resumen.csv"
)

print(
    "datos/validacion_matchup_posicion.csv"
)