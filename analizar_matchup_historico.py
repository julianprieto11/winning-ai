import pandas as pd
import numpy as np

# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO_JUGADORES = "datos/contexto_matchup.csv"
ARCHIVO_EQUIPOS = "datos/contexto_equipos_historico.csv"

ARCHIVO_GENERAL = "datos/analisis_matchup_historico_general.csv"
ARCHIVO_POSICION = "datos/analisis_matchup_historico_posicion.csv"

# ============================================================
# CARGAR DATOS
# ============================================================

print("=" * 70)
print("ANÁLISIS HISTÓRICO MATCHUP V2")
print("=" * 70)

jugadores = pd.read_csv(ARCHIVO_JUGADORES)
equipos = pd.read_csv(ARCHIVO_EQUIPOS)

jugadores["date"] = pd.to_datetime(jugadores["date"])
equipos["date"] = pd.to_datetime(equipos["date"])

print(f"Filas jugadores: {len(jugadores)}")
print(f"Filas equipos: {len(equipos)}")

# ============================================================
# VARIABLES HISTÓRICAS
# ============================================================

variables = [
    c for c in equipos.columns
    if c.startswith("historico_")
    or c.startswith("rival_historico_")
]

# No usamos contadores como variables de rendimiento.
variables = [
    c for c in variables
    if c not in [
        "historico_partidos_historicos_equipo",
        "rival_historico_partidos_historicos_rival",
    ]
]

print(f"Variables históricas encontradas: {len(variables)}")

# ============================================================
# VALIDAR COLUMNAS NECESARIAS
# ============================================================

columnas_jugadores = [
    "date",
    "team_id",
    "player_id",
    "player_name",
    "position",
    "winning_total",
]

for col in columnas_jugadores:
    if col not in jugadores.columns:
        raise ValueError(
            f"No existe la columna '{col}' en {ARCHIVO_JUGADORES}"
        )

if "team_id" not in equipos.columns:
    raise ValueError(
        "No existe 'team_id' en el histórico de equipos."
    )

# ============================================================
# EVITAR DUPLICADOS EN HISTÓRICO DE EQUIPOS
# ============================================================

equipos = equipos.drop_duplicates(
    subset=["date", "team_id"],
    keep="first"
)

# ============================================================
# UNIR CONTEXTO HISTÓRICO AL JUGADOR
# ============================================================

print()
print("Uniendo contexto histórico jugador-equipo...")

columnas_merge = [
    "date",
    "team_id",
] + variables

df = jugadores.merge(
    equipos[columnas_merge],
    on=["date", "team_id"],
    how="left",
    validate="many_to_one"
)

print(f"Filas después de la unión: {len(df)}")

# ============================================================
# CONTROL DE UNIÓN
# ============================================================

historico_disponible = df[variables].notna().any(axis=1)

print(
    f"Jugadores con al menos un dato histórico: "
    f"{historico_disponible.sum()}"
)

print(
    f"Jugadores sin ningún dato histórico: "
    f"{(~historico_disponible).sum()}"
)

# ============================================================
# FUNCIÓN DE ANÁLISIS
# ============================================================

def analizar(grupo, nombre_grupo):

    resultados = []

    for variable in variables:

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

        # NaN = dato no disponible.
        # No se convierte en 0.
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
print("Analizando conjunto general...")

resultado_general = analizar(
    df,
    "GENERAL"
)

resultado_general.to_csv(
    ARCHIVO_GENERAL,
    index=False,
    encoding="utf-8-sig"
)

print(
    f"Guardado: {ARCHIVO_GENERAL}"
)

# ============================================================
# ANÁLISIS POR POSICIÓN
# ============================================================

print()
print("Analizando por posición...")

resultados_posicion = []

posiciones = [
    "ARQ",
    "DEF",
    "VOL",
    "DEL",
]

for posicion in posiciones:

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

    if not resultado.empty:
        resultados_posicion.append(
            resultado
        )

if resultados_posicion:

    resultado_posicion = pd.concat(
        resultados_posicion,
        ignore_index=True
    )

else:

    resultado_posicion = pd.DataFrame()

resultado_posicion.to_csv(
    ARCHIVO_POSICION,
    index=False,
    encoding="utf-8-sig"
)

print(
    f"Guardado: {ARCHIVO_POSICION}"
)

# ============================================================
# MOSTRAR RESULTADOS
# ============================================================

pd.set_option("display.max_rows", 200)
pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 220)

print()
print("=" * 70)
print("TOP GENERAL")
print("=" * 70)

if not resultado_general.empty:

    print(
        resultado_general[
            [
                "variable",
                "n",
                "pearson",
                "spearman",
            ]
        ]
        .head(30)
        .to_string(index=False)
    )

print()
print("=" * 70)
print("TOP POR POSICIÓN")
print("=" * 70)

for posicion in posiciones:

    print()
    print(f"--- {posicion} ---")

    if resultado_posicion.empty:
        continue

    x = resultado_posicion[
        resultado_posicion["grupo"] == posicion
    ].head(20)

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