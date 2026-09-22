import pandas as pd

df = pd.read_csv("datos/contexto_equipos.csv")
df["date"] = pd.to_datetime(df["date"])

df = df.sort_values(["team_id", "date", "match_id"]).copy()

estadisticas = [
    "shots_on_target",
    "chances_created",
    "accurate_passes",
    "passes",
    "progressive_passes",
    "passes_into_final_third",
    "accurate_crosses",
    "progressive_carries",
    "duels_won",
    "duels_lost",
    "tackles",
    "interceptions",
    "recoveries",
    "clearances",
    "blocks",
    "dribbled_past",
    "miscontrols",
    "dispossessed",
    "take_ons",
    "take_ons_won",
    "failed_dribbles",
    "saves",
]

rows = []

for team_id, grupo in df.groupby("team_id", sort=False):

    historial = []

    for _, r in grupo.iterrows():

        ultimos_5 = historial[-5:]

        fila = {
            "match_id": r["match_id"],
            "date": r["date"].date(),
            "team_id": r["team_id"],
            "team_name": r["team_name"],
        }

        # Promedio de cada estadística en los últimos 5
        for stat in estadisticas:

            valores = [x[stat] for x in ultimos_5]

            fila[f"prom_ultimos_5_{stat}"] = (
                sum(valores) / len(valores)
                if valores
                else 0
            )

        # Indicadores derivados
        if ultimos_5:

            fila["prom_ultimos_5_diferencia_duelos"] = (
                sum(x["duels_won"] - x["duels_lost"] for x in ultimos_5)
                / len(ultimos_5)
            )

            fila["prom_ultimos_5_diferencia_recuperaciones_perdidas"] = (
                sum(x["recoveries"] - x["dispossessed"] for x in ultimos_5)
                / len(ultimos_5)
            )

            total_pases = sum(x["passes"] for x in ultimos_5)
            pases_correctos = sum(x["accurate_passes"] for x in ultimos_5)

            fila["prom_ultimos_5_precision_pases"] = (
                pases_correctos / total_pases
                if total_pases > 0
                else 0
            )

        else:

            fila["prom_ultimos_5_diferencia_duelos"] = 0
            fila["prom_ultimos_5_diferencia_recuperaciones_perdidas"] = 0
            fila["prom_ultimos_5_precision_pases"] = 0

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
    "datos/rendimiento_reciente_equipos.csv",
    index=False,
    encoding="utf-8-sig"
)

print("CREADO:", len(out), "filas")
print("COLUMNAS:", len(out.columns))
print()
print(out.head(10).to_string(index=False))