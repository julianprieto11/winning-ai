import pandas as pd

df = pd.read_csv("datos/dataset_jugadores.csv")

arqueros = df[
    (df["position"] == "G") &
    (df["goalAssist"].fillna(0) > 0)
].copy()

print()
print("=" * 100)
print("ASISTENCIAS DE ARQUEROS")
print("=" * 100)

print(
    arqueros[
        [
            "match_id",
            "player_id",
            "player_name",
            "team_name",
            "minutesPlayed",
            "goalAssist",
        ]
    ].to_string(index=False)
)