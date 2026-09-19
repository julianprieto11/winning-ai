import pandas as pd

df = pd.read_csv("datos/dataset_jugadores.csv")

campos = [
    "duelWon",
    "duelLost",
    "wonTackle",
    "interceptionWon",
    "ballRecovery",
    "totalClearance",
    "blockedScoringAttempt",
    "clearanceOffLine",
    "goals_conceded_while_playing",
    "team_clean_sheet"
]

print("=" * 70)
print("COBERTURA DE ESTADÍSTICAS DEFENSIVAS")
print("=" * 70)

total = len(df)

for campo in campos:

    if campo not in df.columns:
        print(f"{campo}: NO EXISTE")
        continue

    disponibles = df[campo].notna().sum()
    positivos = (df[campo].fillna(0) > 0).sum()

    porcentaje = disponibles / total * 100

    print(
        f"{campo:32} "
        f"datos: {disponibles:5}/{total} "
        f"({porcentaje:5.1f}%)  "
        f"con valor > 0: {positivos:5}"
    )

print()
print("PROMEDIOS DE LOS REGISTROS CON VALOR > 0")
print("-" * 70)

for campo in campos:

    if campo not in df.columns:
        continue

    valores = df.loc[df[campo] > 0, campo]

    if len(valores) == 0:
        continue

    print(
        f"{campo:32} "
        f"promedio: {valores.mean():.2f}  "
        f"máximo: {valores.max():.0f}"
    )