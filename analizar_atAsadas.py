import json
import glob
from collections import Counter

archivos = glob.glob("datos/partidos/*.json")

campos = Counter()
ejemplos = {}

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

        if stats.get("minutesPlayed") is None:
            continue

        # Solo nos interesan arqueros que tuvieron al menos una atajada
        if stats.get("saves", 0) <= 0:
            continue

        for campo, valor in stats.items():

            nombre = campo.lower()

            if any(x in nombre for x in [
                "save",
                "shot",
                "goalkeeper",
                "keeper",
                "penalty",
                "one",
                "duel",
                "danger"
            ]):
                campos[campo] += 1

                if campo not in ejemplos:
                    ejemplos[campo] = (
                        jugador["player"]["name"],
                        valor
                    )

print("=== CAMPOS RELACIONADOS CON ATAJADAS ===\n")

for campo, cantidad in campos.most_common():
    print(f"{campo}: {cantidad}")
    print(f"  Ejemplo: {ejemplos[campo]}")