import pandas as pd

df = pd.read_csv("datos/dataset_jugadores.csv")

# Solo jugadores que participaron
df = df[df["minutesPlayed"].notna()].copy()

estadisticas = [
    ("totalShots", "Tiros"),
    ("onTargetScoringAttempt", "Tiros al arco"),
    ("bigChanceCreated", "Ocasiones claras creadas"),
    ("bigChanceMissed", "Ocasiones claras falladas"),
    ("keyPass", "Pases clave"),
    ("hitWoodwork", "Palo"),
    ("progressiveBallCarriesCount", "Progresiones"),
    ("totalOffside", "Offsides"),
    ("penaltyMiss", "Penales fallados"),
]

print("\n=== ACCIONES OFENSIVAS ===\n")

for columna, nombre in estadisticas:

    datos = df[columna].fillna(0)

    registros = (datos > 0).sum()
    total = datos.sum()

    print(f"--- {nombre} ({columna}) ---")
    print(f"Registros con dato > 0: {registros}")
    print(f"Total: {total:.0f}")
    print(f"Promedio por actuación: {datos.mean():.3f}")
    print(f"Máximo en una actuación: {datos.max():.0f}")
    print()

print("=== POR POSICION ===\n")

for posicion in ["G", "D", "M", "F"]:

    datos_pos = df[df["position"] == posicion]

    print(f"--- POSICION {posicion} ---")
    print(f"Actuaciones: {len(datos_pos)}")

    for columna, nombre in estadisticas:

        datos = datos_pos[columna].fillna(0)

        print(
            f"{nombre}: "
            f"total={datos.sum():.0f} | "
            f"con acción={(datos > 0).sum()} | "
            f"promedio={datos.mean():.3f} | "
            f"máx={datos.max():.0f}"
        )

    print()

print("=== COBERTURA REAL DEL DATASET ===\n")

total_filas = len(df)

for columna, nombre in estadisticas:

    con_dato = df[columna].notna().sum()
    porcentaje = con_dato / total_filas * 100

    print(
        f"{nombre}: "
        f"{con_dato}/{total_filas} "
        f"({porcentaje:.1f}%)"
    )