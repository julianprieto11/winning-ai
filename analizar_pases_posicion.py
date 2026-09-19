import pandas as pd

df = pd.read_csv("datos/dataset_jugadores.csv")

campos = [
    "accuratePass",
    "totalPass",
    "accurateOppositionHalfPasses",
    "accurateLongBalls",
    "accurateCross"
]

print("=" * 80)
print("PASES POR POSICIÓN")
print("=" * 80)

for posicion in ["G", "D", "M", "F"]:

    grupo = df[df["position"] == posicion]

    print()
    print(f"POSICIÓN {posicion}")
    print("-" * 80)
    print("Registros:", len(grupo))

    for campo in campos:
        valores = grupo[campo].dropna()

        if len(valores) == 0:
            print(f"{campo:35} sin datos")
            continue

        positivos = valores[valores > 0]

        promedio = positivos.mean() if len(positivos) else 0

        print(
            f"{campo:35} "
            f"datos={len(valores):5} "
            f"promedio>0={promedio:6.2f} "
            f"max={positivos.max() if len(positivos) else 0:.0f}"
        )