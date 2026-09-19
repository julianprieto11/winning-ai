import pandas as pd

ARCHIVO = "datos/mapa_posiciones_pitchapi.csv"

df = pd.read_csv(ARCHIVO)

posiciones = ["ARQ", "DEF", "VOL", "DEL"]

for p in posiciones:
    df[p] = pd.to_numeric(df[p], errors="coerce").fillna(0)

df["total"] = df[posiciones].sum(axis=1)

# Posición dominante
df["dominante"] = df[posiciones].idxmax(axis=1)

# Porcentaje de la posición dominante
df["confianza"] = (
    df[posiciones].max(axis=1) / df["total"] * 100
)

# Ordenar por cantidad de casos
df = df.sort_values("total", ascending=False)

print()
print("=" * 100)
print("ZONAS CON MAYOR CANTIDAD DE REGISTROS")
print("=" * 100)

print(
    df[
        [
            "pitch_x",
            "pitch_y",
            "total",
            "ARQ",
            "DEF",
            "VOL",
            "DEL",
            "dominante",
            "confianza",
        ]
    ]
    .head(40)
    .to_string(index=False)
)

print()
print("=" * 100)
print("ZONAS AMBIGUAS — CONFIANZA < 80%")
print("=" * 100)

ambiguas = df[
    (df["total"] >= 10) &
    (df["confianza"] < 80)
]

print(
    ambiguas[
        [
            "pitch_x",
            "pitch_y",
            "total",
            "ARQ",
            "DEF",
            "VOL",
            "DEL",
            "dominante",
            "confianza",
        ]
    ].to_string(index=False)
)

print()
print("=" * 100)
print("RESUMEN POR POSICIÓN DOMINANTE")
print("=" * 100)

resumen = (
    df.groupby("dominante")
    .agg(
        zonas=("dominante", "count"),
        registros=("total", "sum"),
    )
    .sort_values("registros", ascending=False)
)

print(resumen.to_string())