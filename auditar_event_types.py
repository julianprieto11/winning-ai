import json
from pathlib import Path
from collections import Counter

CARPETA = Path("datos/pitchapi")

contador = Counter()
ejemplos = {}

archivos = sorted(CARPETA.glob("*_events.json"))

for archivo in archivos:

    try:
        data = json.loads(
            archivo.read_text(encoding="utf-8")
        )
    except Exception:
        continue

    events = data.get("data", {}).get("events", [])

    if not isinstance(events, list):
        continue

    for event in events:

        if not isinstance(event, dict):
            continue

        event_type = event.get("event_type")

        if not event_type:
            continue

        contador[event_type] += 1

        if event_type not in ejemplos:
            ejemplos[event_type] = {
                "archivo": archivo.name,
                "evento": event
            }

print()
print("=" * 100)
print("EVENT TYPES — PITCHAPI")
print("=" * 100)
print()

print(f"Archivos analizados: {len(archivos)}")
print(f"Tipos diferentes: {len(contador)}")
print()

for event_type, cantidad in contador.most_common():

    print(f"{event_type:<30} {cantidad:>8}")

    ejemplo = ejemplos[event_type]

    print(
        "  Ejemplo:",
        json.dumps(
            ejemplo["evento"],
            ensure_ascii=False
        )
    )

    print("-" * 100)

print()
print("Fin.")