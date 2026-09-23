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

cols = [
    "match_id", "date", "player_id", "player_name", "team_name",
    "rival_team_name", "position", "matchup_score",
    "matchup_score_propio", "matchup_score_rival",
    "matchup_score_interaccion", "sofascore_event_id"
]
faltantes = [c for c in cols if c not in df.columns]
if faltantes:
    raise ValueError(f"Faltan columnas en contexto_matchup.csv: {faltantes}")

candidatos = df[df["matchup_score"].isna()].copy()
print(f"Filas sin matchup: {len(candidatos)}")

# SofaScore event_id en contexto_matchup.csv corresponde al nombre
# del archivo JSON de datos/partidos/ cuando existe.
indice = {}

def normalizar_event_id(valor):
    if pd.isna(valor):
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() == "nan":
        return None
    try:
        numero = float(texto)
        if numero.is_integer():
            return str(int(numero))
    except (ValueError, TypeError):
        pass
    return texto

def normalizar_player_id(valor):
    if pd.isna(valor):
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() == "nan":
        return None
    try:
        numero = float(texto)
        if numero.is_integer():
            return str(int(numero))
    except (ValueError, TypeError):
        pass
    return texto

def agregar_bloque(event_id, bloque):
    if not isinstance(bloque, dict):
        return

    for item in bloque.get("players", []):
        jugador = item.get("player", {}) or {}
        stats = item.get("statistics") or {}

        # Guardamos las dos identificaciones que aparecen en SofaScore.
        ids = []
        for valor in (jugador.get("id"), jugador.get("sofascoreId")):
            normalizado = normalizar_player_id(valor)
            if normalizado is not None:
                ids.append(normalizado)

        nombre = str(jugador.get("name") or "").strip().casefold()
        info = {
            "titular": item.get("substitute") is False,
            "suplente": item.get("substitute") is True,
            "minutos": stats.get("minutesPlayed"),
            "rating": stats.get("rating"),
            "nombre": nombre,
            "player_id_sofascore": normalizar_player_id(jugador.get("id")),
            "sofascore_id": normalizar_player_id(jugador.get("sofascoreId")),
        }

        for pid in ids:
            indice[(event_id, "id", pid)] = info

        if nombre:
            indice[(event_id, "nombre", nombre)] = info

for ruta in glob.glob(os.path.join(PARTIDOS, "*.json")):
    try:
        event_id = os.path.splitext(os.path.basename(ruta))[0]
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)

        lineups = data.get("lineups", {})
        if isinstance(lineups, list):
            bloques = lineups
        elif isinstance(lineups, dict):
            bloques = [
                lineups.get("home", {}),
                lineups.get("away", {}),
            ]
        else:
            bloques = []

        for bloque in bloques:
            agregar_bloque(event_id, bloque)

    except Exception:
        pass

def obtener_estado(row):
    event_id = normalizar_event_id(row["sofascore_event_id"])

    # Si el partido no tiene correspondencia SofaScore, no podemos
    # verificar participación con alineaciones.
    if event_id is None:
        return None, "SIN_EVENTO_SOFASCORE"

    # player_id de contexto_matchup.csv es un ID interno p_..., no
    # necesariamente el mismo que SofaScore. Por eso primero probamos
    # por nombre y luego, por si coincidiera, por ID.
    nombre = str(row["player_name"]).strip().casefold()
    info = indice.get((event_id, "nombre", nombre))
    if info is not None:
        return info, "nombre"

    pid = normalizar_player_id(row.get("player_id"))
    if pid is not None:
        info = indice.get((event_id, "id", pid))
        if info is not None:
            return info, "player_id"

    return None, "NO_ENCONTRADO_EN_ALINEACION"

resultados = []

for _, row in candidatos.iterrows():
    info, metodo = obtener_estado(row)

    if metodo == "SIN_EVENTO_SOFASCORE":
        estado = "SIN_EVENTO_SOFASCORE"
    elif info is None:
        estado = "NO_ENCONTRADO_EN_ALINEACION"
    elif info["minutos"] is not None and float(info["minutos"]) > 0:
        estado = "REVISAR_JUGO"
    elif info["titular"]:
        estado = "REVISAR_TITULAR_SIN_MINUTOS"
    else:
        estado = "NO_JUGO"

    resultados.append({
        "match_id": row["match_id"],
        "sofascore_event_id": row["sofascore_event_id"],
        "date": row["date"],
        "player_id": row["player_id"],
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
        "date", "player_name", "team_name", "rival_team_name",
        "position", "titular", "minutos", "matchup_score"
    ]].to_string(index=False))
