import json
import os
import pandas as pd


# ============================================================
# PARTIDOS FECHA 10 - SOFASCORE
# ============================================================

IDS_FECHA10 = [
    "16667329",
    "16667338",
    "16667328",
    "16667336",
    "16667325",
    "16667327",
    "16667333",
    "16667340",
    "16667330",
    "16667332",
    "16667326",
    "16671623",
    "16667335",
    "16667331",
    "16667337",
]


candidatos = []


# ============================================================
# LEER JUGADORES
# ============================================================

for event_id in IDS_FECHA10:

    archivo = f"datos/partidos/{event_id}.json"

    if not os.path.exists(archivo):
        print(f"NO EXISTE: {event_id}")
        continue

    with open(archivo, encoding="utf-8") as f:
        data = json.load(f)

    event = data["event"]["event"]


    for lado in ["home", "away"]:

        equipo = event[f"{lado}Team"]["name"]

        jugadores = data["lineups"][lado]["players"]


        for registro in jugadores:

            player = registro["player"]

            stats = registro.get("statistics", {})


            candidatos.append({
                "event_id": event_id,
                "equipo": equipo,
                "jugador": player["name"],
                "player_id": player["id"],
                "position": registro.get("position"),
                "substitute": registro.get("substitute"),
                "minutesPlayed": stats.get("minutesPlayed"),
                "rating": stats.get("rating"),
            })


# ============================================================
# DATAFRAME
# ============================================================

df = pd.DataFrame(candidatos)


# ============================================================
# GUARDAR
# ============================================================

salida = "datos/candidatos_fecha10.csv"

df.to_csv(
    salida,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# RESUMEN
# ============================================================

print()
print("=" * 80)
print("CANDIDATOS FECHA 10")
print("=" * 80)
print()

print(f"Registros: {len(df)}")
print(f"Jugadores únicos: {df['player_id'].nunique()}")

print()
print("Posiciones:")

print(
    df["position"]
    .value_counts(dropna=False)
)

print()
print(f"Archivo generado: {salida}")
print()