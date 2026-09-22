import pandas as pd

df = pd.read_csv("datos/dataset_winning_pitchapi.csv")
df["date"] = pd.to_datetime(df["date"])

df = df.sort_values(
    ["player_id", "date", "match_id"]
).copy()

estadisticas = [
    "minutes_played",
    "participacion",
    "area_rival",
    "ultimo_tercio",
    "carreras_progresivas",
    "duelos",
    "perdidas",
    "regates_fallidos",
    "exceso_perdidas",
    "pases",
    "peligro_creado",
    "defensa",
    "arquero",
    "goles_asistencias",
    "resultado_puntos",
    "valla_invicta",
    "winning_total",
    "accurate_passes",
    "passes",
    "progressive_passes",
    "precision_pases",
    "passes_into_final_third",
    "long_balls_accurate",
    "accurate_crosses",
    "progressive_carries",
    "take_ons",
    "take_ons_won",
    "failed_dribbles",
    "miscontrols",
    "dispossessed",
    "duels_won",
    "duels_lost",
    "tackles",
    "interceptions",
    "recoveries",
    "clearances",
    "blocks",
    "dribbled_past",
    "shots_on_target",
    "goals",
    "assists",
    "chances_created",
    "saves",
    "saved_penalties",
    "goals_conceded",
]

rows = []

for player_id, grupo in df.groupby("player_id", sort=False):

    historial = []

    for _, r in grupo.iterrows():

        ultimos_5 = historial[-5:]

        fila = {
            "match_id": r["match_id"],
            "date": r["date"].date(),
            "player_id": r["player_id"],
            "player_name": r["player_name"],
            "team_id": r["team_id"],
            "team_name": r["team_name"],
            "position": r["position"],
            "partidos_historial": len(ultimos_5),
        }

        for stat in estadisticas:

            valores = [x[stat] for x in ultimos_5]

            fila[f"prom_ultimos_5_{stat}"] = (
                sum(valores) / len(valores)
                if valores
                else 0
            )

        rows.append(fila)

        # Guardar partido actual para futuros cálculos
        historial.append(
            {
                stat: r[stat]
                for stat in estadisticas
            }
        )


out = pd.DataFrame(rows)

out.to_csv(
    "datos/historial_reciente_jugadores.csv",
    index=False,
    encoding="utf-8-sig"
)

print("CREADO:", len(out), "filas")
print("COLUMNAS:", len(out.columns))
print()
print(out.head(10).to_string(index=False))