import pandas as pd
import json
import glob

df = pd.read_csv("datos/contexto_equipos.csv")

estados = {}

for archivo in glob.glob("datos/pitchapi/matches/*.json"):
    with open(archivo, encoding="utf-8") as f:
        data = json.load(f)

    partido = data["data"]

    estados[str(partido["id"])] = partido["status"]

df["status"] = df["match_id"].astype(str).map(estados)

print("TOTAL:", len(df))
print()
print("ESTADOS:")
print(df["status"].value_counts(dropna=False).to_string())
print()
print("SIN ESTADO:", df["status"].isna().sum())