import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

campos = {}

archivos = sorted(CARPETA.glob("*_advanced_players.json"))

for archivo in archivos:

    try:
        data = json.loads(
            archivo.read_text(encoding="utf-8")
        )
    except Exception:
        continue

    jugadores = (
        data
        .get("data", {})
        .get("players", [])
    )

    if not isinstance(jugadores, list):
        continue

    for jugador in jugadores:

        goalkeeping = jugador.get("goalkeeping", {})

        if not isinstance(goalkeeping, dict):
            continue

        for key, valor in goalkeeping.items():

            if key not in campos:

                campos[key] = {
                    "ejemplo": valor,
                    "archivo": archivo.name,
                    "player": (
                        jugador
                        .get("player", {})
                        .get("name")
                    )
                }


print()
print("=" * 100)
print("ARQUEROS — ADVANCED PLAYERS — PITCHAPI")
print("=" * 100)
print()

print(f"Archivos analizados: {len(archivos)}")
print(f"Campos encontrados: {len(campos)}")
print()

for key, info in sorted(campos.items()):

    print(f"KEY: {key}")
    print(f"  Ejemplo:  {info['ejemplo']}")
    print(f"  Jugador:  {info['player']}")
    print(f"  Archivo:  {info['archivo']}")
    print("-" * 100)

print()
print("Fin.")