import pandas as pd

df = pd.read_csv("datos/dataset_jugadores.csv")

print()
print("=" * 100)
print("GOLES CONCEDIDOS MIENTRAS EL JUGADOR ESTABA EN CANCHA")
print("=" * 100)

resultado = df[
    df["goals_conceded_while_playing"] > 0
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
            "goals_conceded_while_playing",
            "home_score",
            "away_score"
        ]
    ]
    .sort_values(["match_id", "team_name", "player_name"])
    .to_string(index=False)
)

print()
print("=" * 100)
print("RESUMEN")
print("=" * 100)

print(
    "Total de registros con goles concedidos:",
    len(resultado)
)

print(
    "Total de goles concedidos registrados:",
    resultado["goals_conceded_while_playing"].sum()
)

print()
print("Máximo de goles concedidos a un jugador en un partido:")

print(
    resultado["goals_conceded_while_playing"].max()
)