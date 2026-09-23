import json
import os
import glob
import pandas as pd

MATCHUP = "datos/contexto_matchup.csv"
PARTIDOS = "datos/partidos"

print("=" * 60)
print("DIAGNOSTICO DE JUGADORES SIN MATCHUP")
print("=" * 60)

df = pd.read_csv(MATCHUP)

cols = ["match_id", "date", "player_name", "team_name", "rival_team_name",
        "position", "matchup_score", "matchup_score_propio",
        "matchup_score_rival", "matchup_score_interaccion"]
faltantes = [c for c in cols if c not in df.columns]
if faltantes:
    raise ValueError(f"Faltan columnas en contexto_matchup.csv: {faltantes}")

candidatos = df[df["matchup_score"].isna()].copy()
print(f"Filas sin matchup: {len(candidatos)}")

# Cargamos alineaciones de SofaScore y construimos un índice por partido/jugador.
indice = {}

for ruta in glob.glob(os.path.join(PARTIDOS, "*.json")):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)

        event = data.get("event", {})
        match_id = str(event.get("id") or event.get("event", {}).get("id") or "")
        if not match_id:
            match_id = str(data.get("match_id") or "")
        if not match_id:
            continue

        lineups = data.get("lineups", {})
        if isinstance(lineups, list):
            bloques = lineups
        else:
            bloques = []
            for key in ("home", "away"):
                bloque = lineups.get(key, {}) if isinstance(lineups, dict) else {}
                bloques.append(bloque)

        for bloque in bloques:
            jugadores = bloque.get("players", []) if isinstance(bloque, dict) else []
            for item in jugadores:
                jugador = item.get("player", {}) or {}
                pid = jugador.get("id")
                if pid is None:
                    continue

                stats = item.get("statistics") or {}
                indice[(match_id, str(pid))] = {
                    "titular": item.get("substitute") is False,
                    "suplente": item.get("substitute") is True,
                    "minutos": stats.get("minutesPlayed"),
                    "rating": stats.get("rating"),
                }

    except Exception:
        pass

# Intento adicional por nombre cuando no hay player_id en el dataset.
por_nombre = {}
for ruta in glob.glob(os.path.join(PARTIDOS, "*.json")):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
        event = data.get("event", {})
        match_id = str(event.get("id") or "")
        lineups = data.get("lineups", {})
        bloques = lineups if isinstance(lineups, list) else [
            lineups.get("home", {}), lineups.get("away", {})
        ]
        for bloque in bloques:
            for item in (bloque.get("players", []) if isinstance(bloque, dict) else []):
                jugador = item.get("player", {}) or {}
                nombre = str(jugador.get("name") or "").strip().casefold()
                if not nombre:
                    continue
                stats = item.get("statistics") or {}
                por_nombre[(match_id, nombre)] = {
                    "titular": item.get("substitute") is False,
                    "suplente": item.get("substitute") is True,
                    "minutos": stats.get("minutesPlayed"),
                    "rating": stats.get("rating"),
                }
    except Exception:
        pass

def obtener_estado(row):
    match_id = str(row["match_id"])
    nombre = str(row["player_name"]).strip().casefold()

    # Si existe player_id en el CSV, usarlo primero.
    pid = row.get("player_id")
    if pd.notna(pid):
        info = indice.get((match_id, str(int(pid)) if float(pid).is_integer() else str(pid)))
        if info is not None:
            return info, "player_id"

    info = por_nombre.get((match_id, nombre))
    if info is not None:
        return info, "nombre"

    return None, "no_encontrado"

resultados = []

for _, row in candidatos.iterrows():
    info, metodo = obtener_estado(row)

    if info is None:
        estado = "NO_ENCONTRADO_EN_ALINEACIONES"
    elif info["minutos"] is not None and float(info["minutos"]) > 0:
        estado = "REVISAR_JUGO"
    elif info["titular"]:
        estado = "REVISAR_TITULAR_SIN_MINUTOS"
    else:
        estado = "NO_JUGO"

    resultados.append({
        "match_id": row["match_id"],
        "date": row["date"],
        "player_name": row["player_name"],
        "team_name": row["team_name"],
        "rival_team_name": row["rival_team_name"],
        "position": row["position"],
        "matchup_score": row["matchup_score"],
        "matchup_score_propio": row["matchup_score_propio"],
        "matchup_score_rival": row["matchup_score_rival"],
        "matchup_score_interaccion": row["matchup_score_interaccion"],
        "titular": info["titular"] if info else None,
        "minutos": info["minutos"] if info else None,
        "rating": info["rating"] if info else None,
        "metodo_verificacion": metodo,
        "estado": estado,
    })

salida = pd.DataFrame(resultados)
salida = salida.sort_values(["estado", "date", "team_name", "player_name"])

os.makedirs("datos", exist_ok=True)
ruta_salida = "datos/revision_matchup_nan.csv"
salida.to_csv(ruta_salida, index=False, encoding="utf-8-sig")

print(f"ARCHIVO: {ruta_salida}")
print()
print("RESUMEN:")
print(salida["estado"].value_counts(dropna=False).to_string())
print()
print("CASOS QUE REALMENTE REQUIEREN REVISION:")
revisar = salida[salida["estado"].isin([
    "REVISAR_JUGO",
    "REVISAR_TITULAR_SIN_MINUTOS"
])]
print(f"Total: {len(revisar)}")
if len(revisar):
    print(revisar[[
        "date","player_name","team_name","rival_team_name",
        "position","titular","minutos","matchup_score"
    ]].to_string(index=False))
