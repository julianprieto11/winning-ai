import json
import glob
from collections import Counter

archivos = glob.glob("datos/partidos/*.json")

campos = [
    "saves",
    "savedShotsFromInsideTheBox",
    "punches",
    "keeperSaveValue",
    "goalkeeperValueNormalized"
]

totales = Counter()
positivos = Counter()
ejemplos = {}

arqueros = 0

for archivo in archivos:
    with open(archivo, encoding="utf-8") as f:
        data = json.load(f)

    jugadores = (
        data["lineups"]["home"]["players"]
        + data["lineups"]["away"]["players"]
    )

    for jugador in jugadores:

        if jugador.get("position") != "G":
            continue

        stats = jugador.get("statistics", {})
        
        # Solo arqueros que realmente jugaron
        if stats.get("minutesPlayed") is None:
            continue

        arqueros += 1

        for campo in campos:
            if campo in stats:
                totales[campo] += 1

                valor = stats[campo]

                if valor not in [None, 0]:
                    positivos[campo] += 1

                    if campo not in ejemplos:
                        ejemplos[campo] = (
                            jugador["player"]["name"],
                            valor
                        )

print(f"Arqueros participantes: {arqueros}")
print()

for campo in campos:
    cobertura = (
        positivos[campo] / arqueros * 100
        if arqueros else 0
    )

    print(f"--- {campo} ---")
    print(f"Registros con campo: {totales[campo]}")
    print(f"Registros > 0: {positivos[campo]}")
    print(f"Cobertura positiva: {cobertura:.1f}%")

    if campo in ejemplos:
        print(f"Ejemplo: {ejemplos[campo]}")

    print()