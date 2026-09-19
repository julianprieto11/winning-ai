import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

CAMPOS = {
    "big_chance_created_team_title",
    "big_chance_missed_title",
    "chances_created",
    "assists",
}

archivos = sorted(CARPETA.glob("*_players.json"))

encontrados = {}

for archivo in archivos:

    try:
        data = json.loads(archivo.read_text(encoding="utf-8"))
    except Exception:
        continue

    jugadores = data.get("data", [])

    if not isinstance(jugadores, list):
        continue

    jugadores_partido = []

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

                if clave not in CAMPOS:
                    continue

                stat = contenido.get("stat", {})

                if isinstance(stat, dict):
                    valores[clave] = stat.get("value")

        if valores:
            jugadores_partido.append({
                "nombre": nombre,
                "valores": valores
            })

    if jugadores_partido:

        encontrados[archivo.name] = jugadores_partido


print()
print("=" * 100)
print("AUDITORÍA DETALLADA — PELIGRO OFENSIVO")
print("=" * 100)

print()
print(f"Partidos con alguno de los campos: {len(encontrados)}")
print()

# Mostrar los primeros partidos encontrados
contador = 0

for archivo, jugadores in encontrados.items():

    print("=" * 100)
    print(f"ARCHIVO: {archivo}")
    print("=" * 100)

    for jugador in jugadores:

        valores = jugador["valores"]

        print(f"\n{jugador['nombre']}")

        for campo in CAMPOS:

            if campo in valores:
                print(f"  {campo}: {valores[campo]}")

    contador += 1

    if contador >= 5:
        break

print()
print("=" * 100)
print("FIN")
print("=" * 100)