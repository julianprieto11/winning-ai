import pandas as pd

df = pd.read_csv("datos/dataset_jugadores.csv")

df = df[
    (df["totalPass"].notna()) &
    (df["totalPass"] > 0) &
    (df["accuratePass"].notna())
].copy()

df["precision"] = df["accuratePass"] / df["totalPass"]

print("=" * 80)
print("PRECISIÓN DE PASE")
print("=" * 80)

print("Registros con datos:", len(df))

print()
print("Promedio:", round(df["precision"].mean(), 3))
print("Mediana:", round(df["precision"].median(), 3))
print("Mínimo:", round(df["precision"].min(), 3))
print("Máximo:", round(df["precision"].max(), 3))

print()
print("PRECISIÓN POR POSICIÓN")
print("-" * 80)

for posicion in ["G", "D", "M", "F"]:

    grupo = df[df["position"] == posicion]

    print(
        f"{posicion}: "
        f"n={len(grupo):5}  "
        f"promedio={grupo['precision'].mean():.3f}  "
        f"mediana={grupo['precision'].median():.3f}"
    )

print()
print("DISTRIBUCIÓN")
print("-" * 80)

rangos = [
    ("0-50%", 0.00, 0.50),
    ("50-60%", 0.50, 0.60),
    ("60-70%", 0.60, 0.70),
    ("70-80%", 0.70, 0.80),
    ("80-90%", 0.80, 0.90),
    ("90-100%", 0.90, 1.01),
]

for nombre, minimo, maximo in rangos:
    cantidad = ((df["precision"] >= minimo) & (df["precision"] < maximo)).sum()

    print(
        f"{nombre:10} {cantidad:5} "
        f"({cantidad / len(df) * 100:5.1f}%)"
    )