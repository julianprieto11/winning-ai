import pandas as pd

df = pd.read_csv("datos/dataset_jugadores.csv")

print()
print("=" * 100)
print("GOLES A FAVOR MIENTRAS EL JUGADOR ESTABA EN CANCHA")
print("=" * 100)

# Comparamos los goles totales del equipo con los goles que el jugador
# ya tiene registrados individualmente.
#
# Por ahora solamente mostramos los datos disponibles para validar
# que el resultado del partido y los goles individuales sean coherentes.

resultado = df[
    df["goals"].fillna(0) > 0
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
            "home_score",
            "away_score",
            "goals_conceded_while_playing"
        ]
    ]
    .sort_values(["match_id", "team_name", "player_name"])
    .to_string(index=False)
)

print()
print("=" * 100)
print("RESUMEN")
print("=" * 100)

print("Registros con goles:", len(resultado))
print("Goles individuales registrados:", resultado["goals"].fillna(0).sum())