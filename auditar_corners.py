import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

archivos = sorted(CARPETA.glob("*_players.json"))

encontrados = []

for archivo in archivos:

    try:
        data = json.loads(archivo.read_text(encoding="utf-8"))
    except Exception:
        continue

    jugadores = data.get("data", [])

    if not isinstance(jugadores, list):
        continue

    for jugador in jugadores:

        if not isinstance(jugador, dict):
            continue

        info = jugador.get("player", {})

        if not isinstance(info, dict):
            continue

        nombre = info.get("name", "Desconocido")

        valores = {}

        for grupo in jugador.get("stats", []):

            if not isinstance(grupo, dict):
                continue

            stats = grupo.get("stats", {})

            if not isinstance(stats, dict):
                continue

            for nombre_stat, contenido in stats.items():

                if not isinstance(contenido, dict):
                    continue

                clave = contenido.get("key")

                if clave not in {
                    "corners",
                    "chances_created",
                    "assists",
                    "dribbles_succeeded",
                    "Offsides",
                }:
                    continue

                stat = contenido.get("stat", {})

                if isinstance(stat, dict):
                    valores[clave] = stat.get("value")

        if "corners" in valores:
            encontrados.append({
                "archivo": archivo.name,
                "jugador": nombre,
                "valores": valores
            })


print()
print("=" * 100)
print("AUDITORÍA DE CORNERS")
print("=" * 100)
print()

print(f"Registros con corners: {len(encontrados)}")
print()

# Mostrar ejemplos donde el jugador tenga más de 0 corners
mostrados = 0

for item in encontrados:

    if item["valores"].get("corners", 0) <= 0:
        continue

    print(f"Archivo : {item['archivo']}")
    print(f"Jugador : {item['jugador']}")

    for campo, valor in item["valores"].items():
        print(f"  {campo}: {valor}")

    print("-" * 100)

    mostrados += 1

    if mostrados >= 30:
        break

print()
print("=" * 100)
print("FIN")
print("=" * 100)