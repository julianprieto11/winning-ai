import json
import glob
import os
import csv
from collections import defaultdict

LINEUPS_DIR = "datos/pitchapi/lineups"
MATCHES_DIR = "datos/pitchapi/matches"
SALIDA = "datos/historial_posiciones_pitchapi.csv"

print("=" * 70)
print("ANALISIS CRONOLOGICO DE POSICIONES PITCHAPI")
print("=" * 70)

# ============================================================
# 1. CARGAR FECHAS DE LOS PARTIDOS
# ============================================================

fechas_partidos = {}

archivos_matches = glob.glob(
    os.path.join(MATCHES_DIR, "*.json")
)

print()
print("Cargando fechas de partidos...")

for archivo in archivos_matches:
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)

        root = data.get("data", data)

        if not isinstance(root, dict):
            continue

        match_id = root.get("match_id")

        if not match_id:
            nombre = os.path.basename(archivo)
            match_id = os.path.splitext(nombre)[0]

        fecha = root.get("date")
        hora = root.get("time_utc")

        if fecha:
            fechas_partidos[match_id] = {
                "date": fecha,
                "time_utc": hora or ""
            }

    except Exception:
        continue

print("Partidos con fecha encontrada:", len(fechas_partidos))

# ============================================================
# 2. LEER LINEUPS
# ============================================================

archivos_lineups = glob.glob(
    os.path.join(LINEUPS_DIR, "*_lineups.json")
)

print("Archivos de lineups:", len(archivos_lineups))

registros = []

for archivo in archivos_lineups:

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        continue

    # Los lineups tienen la estructura:
    #
    # {
    #     "data": {
    #         "match_id": "...",
    #         "home_team": "...",
    #         "away_team": "...",
    #         "home": {...},
    #         "away": {...}
    #     }
    # }

    data = raw.get("data", raw)

    if not isinstance(data, dict):
        continue

    match_id = data.get("match_id")

    if not match_id:
        nombre = os.path.basename(archivo)
        match_id = nombre.replace("_lineups.json", "")

    fecha_info = fechas_partidos.get(match_id, {})

    fecha = fecha_info.get("date", "")
    time_utc = fecha_info.get("time_utc", "")

    # ========================================================
    # HOME / AWAY
    # ========================================================

    for lado in ["home", "away"]:

        equipo_data = data.get(lado, {})

        if not isinstance(equipo_data, dict):
            continue

        # Nombre del equipo.
        # Puede estar arriba en home_team / away_team.
        equipo = data.get(
            "home_team" if lado == "home" else "away_team",
            ""
        )

        # ====================================================
        # STARTERS
        # ====================================================

        starters = equipo_data.get("starters", [])

        if not isinstance(starters, list):
            continue

        for jugador in starters:

            if not isinstance(jugador, dict):
                continue

            player_id = jugador.get("player_id")

            if player_id is None:
                continue

            registros.append({
                "match_id": match_id,
                "date": fecha,
                "time_utc": time_utc,
                "player_id": player_id,
                "player_name": jugador.get("name", ""),
                "team": equipo,
                "side": lado,
                "starter": 1,
                "position_id": jugador.get("position_id")
            })

# ============================================================
# 3. ORDENAR CRONOLOGICAMENTE
# ============================================================

registros.sort(
    key=lambda x: (
        str(x["player_id"]),
        x["date"],
        x["time_utc"]
    )
)

# ============================================================
# 4. GUARDAR
# ============================================================

campos = [
    "match_id",
    "date",
    "time_utc",
    "player_id",
    "player_name",
    "team",
    "side",
    "starter",
    "position_id"
]

with open(
    SALIDA,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=campos
    )

    writer.writeheader()
    writer.writerows(registros)

print()
print("Registros guardados:", len(registros))
print("Salida:", SALIDA)

# ============================================================
# 5. RESUMEN
# ============================================================

jugadores = defaultdict(list)

for r in registros:
    jugadores[r["player_id"]].append(r)

print()
print("Jugadores:", len(jugadores))

# ============================================================
# 6. MOSTRAR EJEMPLOS CON CAMBIOS
# ============================================================

print()
print("=" * 70)
print("EJEMPLOS DE HISTORIAL CRONOLOGICO")
print("=" * 70)

mostrados = 0

for player_id, historial in jugadores.items():

    if len(historial) < 5:
        continue

    historial = sorted(
        historial,
        key=lambda x: (
            x["date"],
            x["time_utc"]
        )
    )

    posiciones = [
        str(x["position_id"])
        for x in historial
    ]

    if len(set(posiciones)) > 1:

        print()
        print(
            historial[-1]["player_name"],
            f"(ID {player_id})"
        )

        for x in historial[-10:]:
            print(
                f"  {x['date']} | "
                f"{x['team']} | "
                f"position_id={x['position_id']}"
            )

        mostrados += 1

        if mostrados >= 15:
            break

print()
print("=" * 70)
print("ANALISIS TERMINADO")
print("=" * 70)