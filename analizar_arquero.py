import pandas as pd

df = pd.read_csv("datos/dataset_jugadores.csv")

# Solo jugadores que participaron
df = df[df["minutesPlayed"].notna()].copy()

# Solo arqueros
df = df[df["position"] == "G"].copy()

estadisticas = [
    ("goalkeeperSaves", "Atajadas"),
    ("aerialWon", "Aereas ganadas"),
    ("aerialLost", "Aereas perdidas"),
    ("punches", "Puñetazos/despejes de puño"),
    ("runsOut", "Salidas"),
    ("penaltyWon", "Penales ganados"),
]

print("\n=== ESTADISTICAS DE ARQUEROS ===\n")

for columna, nombre in estadisticas:

    if columna not in df.columns:
        print(f"--- {nombre} ({columna}) ---")
        print("NO EXISTE EN EL DATASET")
        print()
        continue

    datos = df[columna].fillna(0)

    registros = (datos > 0).sum()
    total = datos.sum()

    print(f"--- {nombre} ({columna}) ---")
    print(f"Registros con dato > 0: {registros}")
    print(f"Total: {total:.0f}")
    print(f"Promedio: {datos.mean():.3f}")
    print(f"Maximo: {datos.max():.0f}")
    print()

print("=== COBERTURA ===\n")

total_filas = len(df)

for columna, nombre in estadisticas:

    if columna not in df.columns:
        print(f"{nombre}: NO EXISTE")
        continue

    con_dato = df[columna].notna().sum()
    porcentaje = con_dato / total_filas * 100

    print(
        f"{nombre}: "
        f"{con_dato}/{total_filas} "
        f"({porcentaje:.1f}%)"
    )