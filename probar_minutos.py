import pandas as pd

df = pd.read_csv("datos/dataset_jugadores.csv")

print()
print("=" * 100)
print("JUGADORES CON MÁS DE 90 MINUTOS")
print("=" * 100)

resultado = df[
    df["minutesPlayed"] > 90
].copy()

print(
    resultado[
        [
            "match_id",
            "player_id",
            "player_name",
            "team_name",
            "position",
            "minutesPlayed",
            "goals",
            "goalAssist"
        ]
    ]
    .sort_values(["match_id", "minutesPlayed"])
    .to_string(index=False)
)

print()
print("Total de registros > 90 minutos:", len(resultado))