import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

casos = []

archivos = sorted(CARPETA.glob("*_events.json"))

for archivo in archivos:

    try:
        data = json.loads(
            archivo.read_text(encoding="utf-8")
        )
    except Exception:
        continue

    events = data.get("data", {}).get("events", [])

    jugadores = {}

    for event in events:

        if not isinstance(event, dict):
            continue

        event_type = event.get("event_type")
        player = event.get("player")

        if not player:
            continue

        player_id = player.get("id")

        if not player_id:
            continue

        if player_id not in jugadores:
            jugadores[player_id] = {
                "name": player.get("name"),
                "yellowcard": [],
                "redcard": []
            }

        if event_type == "yellowcard":
            jugadores[player_id]["yellowcard"].append(event)

        elif event_type == "redcard":
            jugadores[player_id]["redcard"].append(event)

    for player_id, info in jugadores.items():

        if info["yellowcard"] and info["redcard"]:

            casos.append({
                "archivo": archivo.name,
                "player_id": player_id,
                "name": info["name"],
                "yellowcards": info["yellowcard"],
                "redcards": info["redcard"]
            })


print()
print("=" * 100)
print("SEGUNDA AMARILLA / ROJA — PITCHAPI")
print("=" * 100)
print()

print(f"Partidos analizados: {len(archivos)}")
print(f"Casos encontrados: {len(casos)}")
print()

for caso in casos:

    print("-" * 100)

    print(f"Archivo: {caso['archivo']}")
    print(f"Jugador: {caso['name']}")
    print(f"ID: {caso['player_id']}")

    print()
    print("AMARILLAS:")

    for evento in caso["yellowcards"]:
        print(
            f"  {evento.get('minute')}' "
            f"{evento.get('period')}"
        )

    print()
    print("ROJAS:")

    for evento in caso["redcards"]:
        print(
            f"  {evento.get('minute')}' "
            f"{evento.get('period')}"
        )

print()
print("=" * 100)
print("Fin.")