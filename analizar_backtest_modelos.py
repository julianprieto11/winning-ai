import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================
# WINNING AI
# DATASET PARA BACKTEST TEMPORAL
# ============================================================
#
# MODELO A: BASE
#   - Historial reciente del jugador
#   - Minutos históricos
#
# MODELO B: BASE + CONTEXTO
#   - Todo lo anterior
#   - Contexto histórico propio
#   - Contexto histórico rival
#
# MODELO C: BASE + MATCHUP
#   - Todo lo anterior
#   - Diferencias y ratios propio vs rival
#
# TARGET:
#   winning_total del partido actual
#
# REGLA:
#   Ninguna variable del partido actual puede entrar
#   como predictor.
# ============================================================

BASE_DIR = Path("datos")

ARCHIVO_MATCHUP = BASE_DIR / "contexto_matchup.csv"
ARCHIVO_HISTORIAL = BASE_DIR / "historial_reciente_jugadores_v2.csv"
ARCHIVO_MINUTOS = BASE_DIR / "minutos_historicos.csv"
ARCHIVO_EQUIPOS = BASE_DIR / "contexto_equipos_historico.csv"

SALIDA = BASE_DIR / "backtest_dataset.csv"


# ============================================================
# 1. CARGAR
# ============================================================

print("=" * 70)
print("WINNING AI - DATASET BACKTEST TEMPORAL")
print("=" * 70)

print("\n[1/8] Cargando archivos...")

df_matchup = pd.read_csv(ARCHIVO_MATCHUP)
df_historial = pd.read_csv(ARCHIVO_HISTORIAL)
df_minutos = pd.read_csv(ARCHIVO_MINUTOS)
df_equipos = pd.read_csv(ARCHIVO_EQUIPOS)

print(f"contexto_matchup:       {len(df_matchup):,}")
print(f"historial jugadores:    {len(df_historial):,}")
print(f"minutos históricos:     {len(df_minutos):,}")
print(f"contexto equipos:       {len(df_equipos):,}")


# ============================================================
# 2. FECHAS
# ============================================================

print("\n[2/8] Normalizando fechas...")

for df in [
    df_matchup,
    df_historial,
    df_minutos,
    df_equipos,
]:
    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )


# ============================================================
# 3. BASE DEL PARTIDO
# ============================================================

print("\n[3/8] Construyendo base de partidos...")

columnas_identificacion = [
    "match_id",
    "date",
    "round_name",
    "player_id",
    "player_name",
    "team_id",
    "team_name",
    "position",
    "winning_total",
]

columnas_identificacion = [
    c for c in columnas_identificacion
    if c in df_matchup.columns
]

df = df_matchup[columnas_identificacion].copy()

df = df.drop_duplicates(
    subset=["date", "player_id"]
).reset_index(drop=True)


# ============================================================
# 4. HISTORIAL DEL JUGADOR
# ============================================================

print("\n[4/8] Agregando historial del jugador...")

columnas_historial = [
    c for c in df_historial.columns
    if c.startswith("prom_ultimos_5_")
]

columnas_historial += [
    "partidos_historial"
]

columnas_historial = list(dict.fromkeys(
    c for c in columnas_historial
    if c in df_historial.columns
))

df_historial_sel = df_historial[
    ["date", "player_id"] + columnas_historial
].copy()

df_historial_sel = df_historial_sel.drop_duplicates(
    subset=["date", "player_id"]
)

df = df.merge(
    df_historial_sel,
    on=["date", "player_id"],
    how="left"
)

print(
    f"Variables historial jugador: "
    f"{len(columnas_historial)}"
)


# ============================================================
# 5. MINUTOS HISTÓRICOS
# ============================================================

print("\n[5/8] Agregando minutos históricos...")

columnas_minutos = [
    "minutos_promedio_historico",
    "partidos_historicos_minutos",
    "minutos_promedio_ultimos_5",
]

columnas_minutos = [
    c for c in columnas_minutos
    if c in df_minutos.columns
]

df_minutos_sel = df_minutos[
    ["date", "player_id"] + columnas_minutos
].copy()

df_minutos_sel = df_minutos_sel.drop_duplicates(
    subset=["date", "player_id"]
)

df = df.merge(
    df_minutos_sel,
    on=["date", "player_id"],
    how="left"
)


# ============================================================
# 6. CONTEXTO EQUIPO / RIVAL
# ============================================================

print("\n[6/8] Agregando contexto histórico...")

columnas_contexto = []

for c in df_equipos.columns:

    if (
        c.startswith("historico_")
        or c.startswith("rival_historico_")
    ):
        if pd.api.types.is_numeric_dtype(df_equipos[c]):
            columnas_contexto.append(c)

columnas_contexto = list(dict.fromkeys(columnas_contexto))

df_contexto = df_equipos[
    ["date", "team_id"] + columnas_contexto
].copy()

df_contexto = df_contexto.drop_duplicates(
    subset=["date", "team_id"]
)

df = df.merge(
    df_contexto,
    on=["date", "team_id"],
    how="left"
)

print(
    f"Variables contexto equipo/rival: "
    f"{len(columnas_contexto)}"
)


# ============================================================
# 7. CREAR VARIABLES MATCHUP
# ============================================================

print("\n[7/8] Construyendo variables MATCHUP...")

# ------------------------------------------------------------
# Variables que tienen versión propia y rival
# ------------------------------------------------------------

pares = []

for c in columnas_contexto:

    if not c.startswith("historico_"):
        continue

    nombre_base = c.replace(
        "historico_",
        "",
        1
    )

    rival = f"rival_historico_{nombre_base}"

    if rival in df.columns:

        pares.append(
            (
                nombre_base,
                c,
                rival
            )
        )


print(
    f"Pares propio/rival encontrados: "
    f"{len(pares)}"
)


matchup_columns = []

for nombre, propio, rival in pares:

    diferencia = f"matchup_diferencia_{nombre}"
    ratio = f"matchup_ratio_{nombre}"

    df[diferencia] = (
        df[propio] - df[rival]
    )

    # Ratio solamente cuando ambos valores existen
    # y el rival no es 0.
    df[ratio] = np.where(
        df[rival].notna() & (df[rival] != 0),
        df[propio] / df[rival],
        np.nan
    )

    matchup_columns.append(diferencia)
    matchup_columns.append(ratio)


# ------------------------------------------------------------
# Bloques conceptuales adicionales
# ------------------------------------------------------------

# Ataque
def crear_diferencia(nombre, propio, rival):
    if propio in df.columns and rival in df.columns:

        col = f"matchup_{nombre}_diferencia"

        df[col] = (
            df[propio] - df[rival]
        )

        matchup_columns.append(col)


def crear_ratio(nombre, propio, rival):

    if propio in df.columns and rival in df.columns:

        col = f"matchup_{nombre}_ratio"

        df[col] = np.where(
            df[rival].notna() & (df[rival] != 0),
            df[propio] / df[rival],
            np.nan
        )

        matchup_columns.append(col)


# Estas llamadas solo se crean si existen las columnas.
crear_diferencia(
    "ataque_xg",
    "historico_expectedGoals",
    "rival_historico_expectedGoals"
)

crear_ratio(
    "ataque_xg",
    "historico_expectedGoals",
    "rival_historico_expectedGoals"
)

crear_diferencia(
    "ataque_tiros_arco",
    "historico_shotsOnGoal",
    "rival_historico_shotsOnGoal"
)

crear_ratio(
    "ataque_tiros_arco",
    "historico_shotsOnGoal",
    "rival_historico_shotsOnGoal"
)

crear_diferencia(
    "pases_precisos",
    "historico_accuratePasses",
    "rival_historico_accuratePasses"
)

crear_ratio(
    "pases_precisos",
    "historico_accuratePasses",
    "rival_historico_accuratePasses"
)

crear_diferencia(
    "posesion",
    "historico_ballPossession",
    "rival_historico_ballPossession"
)

crear_ratio(
    "posesion",
    "historico_ballPossession",
    "rival_historico_ballPossession"
)

crear_diferencia(
    "fouls",
    "historico_fouls",
    "rival_historico_fouls"
)

crear_ratio(
    "fouls",
    "historico_fouls",
    "rival_historico_fouls"
)

crear_diferencia(
    "freeKicks",
    "historico_freeKicks",
    "rival_historico_freeKicks"
)

crear_ratio(
    "freeKicks",
    "historico_freeKicks",
    "rival_historico_freeKicks"
)


# ============================================================
# 8. LIMPIEZA Y VALIDACIÓN
# ============================================================

print("\n[8/8] Validando dataset...")

# Eliminar duplicados
df = df.drop_duplicates(
    subset=["date", "player_id"]
).reset_index(drop=True)

# Orden cronológico
df = df.sort_values(
    ["date", "player_id"]
).reset_index(drop=True)


# ------------------------------------------------------------
# Variables de cada modelo
# ------------------------------------------------------------

base_columns = (
    columnas_historial
    + columnas_minutos
)

base_columns = [
    c for c in base_columns
    if c in df.columns
]

base_columns = list(dict.fromkeys(base_columns))


context_columns_final = [
    c for c in columnas_contexto
    if c in df.columns
]

matchup_columns = list(dict.fromkeys(
    c for c in matchup_columns
    if c in df.columns
))


# ------------------------------------------------------------
# Evitar target leakage
# ------------------------------------------------------------

columnas_prohibidas = [
    "winning_total",
    "minutes_played",
    "participacion",
    "area_rival",
    "ultimo_tercio",
    "carreras_progresivas",
    "duelos",
    "perdidas",
    "regates_fallidos",
    "exceso_perdidas",
    "pases",
    "peligro_creado",
    "defensa",
    "arquero",
    "goles_asistencias",
    "disciplina",
    "resultado_puntos",
    "bonus_resultado_jugador",
    "valla_invicta",
]

base_columns = [
    c for c in base_columns
    if c not in columnas_prohibidas
]

context_columns_final = [
    c for c in context_columns_final
    if c not in columnas_prohibidas
]

matchup_columns = [
    c for c in matchup_columns
    if c not in columnas_prohibidas
]


# ============================================================
# RESUMEN
# ============================================================

print("\n" + "=" * 70)
print("VALIDACIÓN FINAL")
print("=" * 70)

print(f"\nFilas: {len(df):,}")
print(f"Columnas: {len(df.columns):,}")

print(
    f"Fecha inicial: "
    f"{df['date'].min().date()}"
)

print(
    f"Fecha final: "
    f"{df['date'].max().date()}"
)

print(
    f"Jugadores: "
    f"{df['player_id'].nunique():,}"
)

print(
    f"\nVariables BASE: "
    f"{len(base_columns)}"
)

print(
    f"Variables CONTEXTO: "
    f"{len(context_columns_final)}"
)

print(
    f"Variables MATCHUP: "
    f"{len(matchup_columns)}"
)

print(
    f"\nTarget disponible: "
    f"{df['winning_total'].notna().sum():,}"
)

print(
    f"Target faltante: "
    f"{df['winning_total'].isna().sum():,}"
)


# ============================================================
# GUARDAR
# ============================================================

df.to_csv(
    SALIDA,
    index=False
)

print("\nArchivo generado:")

print(
    SALIDA.resolve()
)

print("\nDataset preparado correctamente.")
print("No se entrenó ningún modelo todavía.")