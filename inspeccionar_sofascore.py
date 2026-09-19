import json
import glob
import collections

contador = collections.Counter()

archivos = glob.glob("datos/partidos/*.json")

partidos = 0
registros_jugadores = 0

for archivo in archivos:
    with open(archivo, encoding="utf-8") as f:
        datos = json.load(f)

    partidos += 1

    for lado in ["home", "away"]:
        jugadores = datos["lineups"].get(lado, {}).get("players", [])

        for jugador in jugadores:
            registros_jugadores += 1

            estadisticas = jugador.get("statistics")

            if isinstance(estadisticas, dict):
                contador.update(estadisticas.keys())

print(f"PARTIDOS: {partidos}")
print(f"REGISTROS DE JUGADORES: {registros_jugadores}")
print(f"CAMPOS INDIVIDUALES: {len(contador)}")
print()

print("CAMPOS ENCONTRADOS:")
print("-" * 50)

for campo, cantidad in sorted(contador.items()):
    print(f"{campo}: {cantidad}")