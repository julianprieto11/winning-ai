import json
import glob
from collections import Counter


ARCHIVOS = glob.glob("datos/partidos/*.json")

contador = Counter()
tarjetas_jugadores = 0
tarjetas_entrenadores = 0
anuladas = 0


for archivo in ARCHIVOS:

    with open(archivo, encoding="utf-8") as f:
        datos = json.load(f)

    incidentes = datos["incidents"]["incidents"]

    for incidente in incidentes:

        if incidente.get("incidentType") != "card":
            continue

        if incidente.get("rescinded") is True:
            anuladas += 1
            continue

        jugador = incidente.get("player")

        if not jugador:
            tarjetas_entrenadores += 1
            continue

        clase = incidente.get("incidentClass")

        if clase not in ["yellow", "red", "yellowRed"]:
            continue

        tarjetas_jugadores += 1
        contador[clase] += 1


print("=" * 60)
print("ANÁLISIS DE TARJETAS")
print("=" * 60)

print("Partidos analizados:", len(ARCHIVOS))
print("Tarjetas de jugadores:", tarjetas_jugadores)
print("Tarjetas de entrenadores:", tarjetas_entrenadores)
print("Tarjetas anuladas:", anuladas)

print()
print("Tipos:")
print("Amarillas:", contador["yellow"])
print("Rojas directas:", contador["red"])
print("Segundas amarillas:", contador["yellowRed"])