import json
import glob
from collections import defaultdict

ARCHIVO_GLOB = "datos/pitchapi/lineups/*_lineups.json"

objetivos = [
    "Leandro Paredes",
    "Marcelo Torres",
    "Rodrigo Auzmendi",
    "Rubén Botta",
    "Franco Nicola",
]

resultados = defaultdict(list)

for archivo in glob.glob(ARCHIVO_GLOB):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            raw = json.load(f)

        data = raw.get("data", raw)

        for lado in ["home", "away"]:
            equipo = data.get(lado, {})
            jugadores = equipo.get("starters", [])

            for jugador in jugadores:
                nombre = jugador.get("name", "")

                for objetivo in objetivos:
                    if nombre.lower() == objetivo.lower():
                        resultados[objetivo].append({
                            "name": nombre,
                            "position_id": jugador.get("position_id"),
                            "pitch_x": jugador.get("pitch_x"),
                            "pitch_y": jugador.get("pitch_y"),
                            "match_id": data.get("match_id"),
                            "team": equipo.get("name"),
                        })

    except Exception:
        pass


for nombre in objetivos:
    print()
    print("=" * 70)
    print(nombre)
    print("=" * 70)

    for r in resultados[nombre][-10:]:
        print(
            f"position_id={r['position_id']:>3} | "
            f"x={str(r['pitch_x']):>5} | "
            f"y={str(r['pitch_y']):>5} | "
            f"equipo={r['team']} | "
            f"match={r['match_id']}"
        )