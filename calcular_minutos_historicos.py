import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO = "datos/contexto_matchup.csv"
SALIDA = "datos/minutos_historicos.csv"

# ============================================================
# CARGAR
# ============================================================

df = pd.read_csv(ARCHIVO)

df["date"] = pd.to_datetime(df["date"])

df = df.sort_values(
    ["player_id", "date"]
).copy()

# ============================================================
# HISTORIAL SIN LEAKAGE
# ============================================================

# Para cada jugador:
# shift(1) elimina el partido actual del cálculo.

df["minutos_promedio_historico"] = (
    df.groupby("player_id")["minutes_played"]
      .transform(lambda s: s.shift(1).expanding().mean())
)

df["partidos_historicos_minutos"] = (
    df.groupby("player_id")["minutes_played"]
      .transform(lambda s: s.shift(1).expanding().count())
)

df["minutos_promedio_ultimos_5"] = (
    df.groupby("player_id")["minutes_played"]
      .transform(lambda s: s.shift(1).rolling(5, min_periods=1).mean())
)

# ============================================================
# GUARDAR
# ============================================================

columnas = [
    "date",
    "player_id",
    "player_name",
    "minutos_promedio_historico",
    "partidos_historicos_minutos",
    "minutos_promedio_ultimos_5",
]

salida = df[columnas].copy()

salida.to_csv(
    SALIDA,
    index=False,
    encoding="utf-8-sig"
)

# ============================================================
# RESUMEN
# ============================================================

print("=" * 80)
print("WINNING AI - MINUTOS HISTÓRICOS SIN LEAKAGE")
print("=" * 80)

print(f"\nFilas generadas: {len(salida):,}")
print(f"Jugadores: {salida['player_id'].nunique():,}")

print("\nPrimeras filas:")

print(
    salida.head(20).to_string(index=False)
)

print("\n" + "=" * 80)
print(f"Archivo generado: {SALIDA}")
print("=" * 80)