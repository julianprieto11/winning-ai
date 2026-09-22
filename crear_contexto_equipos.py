import pandas as pd
import json
import glob
import os

df = pd.read_csv("datos/dataset_winning_pitchapi.csv")

files = {}

for f in glob.glob("datos/pitchapi/matches/*.json"):
    with open(f, encoding="utf-8") as archivo:
        d = json.load(archivo)["data"]
    files[str(d["id"])] = d

stats = [
    "goals",
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

for (match_id, team_id), g in df.groupby(["match_id", "team_id"]):

    d = files[str(match_id)]

    home_id = d["home_team"]["id"]
    away_id = d["away_team"]["id"]

    team_name = g["team_name"].iloc[0]
    home = d["home_team"]["name"]
    away = d["away_team"]["name"]

    goles_favor = pd.to_numeric(
        g["goals"], errors="coerce"
    ).fillna(0).sum()

    goles_contra = (
        d["score_away"]
        if team_id == home_id
        else d["score_home"]
    )

    row = {
        "match_id": match_id,
        "date": d["date"],
        "round_name": d["round_name"],
        "team_id": team_id,
        "team_name": team_name,
        "rival": away if team_id == home_id else home,
        "local_visitante": "LOCAL" if team_id == home_id else "VISITANTE",
        "goles_favor": goles_favor,
        "goles_contra": goles_contra,
    }

    for c in stats:
        row[c] = pd.to_numeric(
            g[c], errors="coerce"
        ).fillna(0).sum()

    rows.append(row)

out = pd.DataFrame(rows)

out = out.sort_values(
    ["date", "team_name"]
)

os.makedirs("datos", exist_ok=True)

out.to_csv(
    "datos/contexto_equipos.csv",
    index=False,
    encoding="utf-8-sig"
)

print("ARCHIVO CREADO: datos/contexto_equipos.csv")
print("FILAS:", len(out))
print("COLUMNAS:", len(out.columns))

print("\nPRIMERAS 5 FILAS:")
print(out.head(5).to_string(index=False))
