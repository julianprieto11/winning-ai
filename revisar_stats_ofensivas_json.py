import json
import glob
from collections import Counter

campos = [
    "onTargetScoringAttempt",
    "bigChanceCreated",
    "bigChanceMissed",
    "keyPass",
    "hitWoodwork",
    "totalOffside",
    "penaltyMiss"
]

contador = Counter()

for archivo in glob.glob("datos/partidos/*.json"):

    datos = json.load(open(archivo, encoding="utf-8"))

    for equipo in ["home", "away"]:

        for jugador in datos["lineups"][equipo]["players"]:

            stats = jugador.get("statistics", {})

            for campo in campos:

                if campo in stats:
                    contador[campo] += 1

print("=" * 65)
print("COBERTURA REAL EN LOS JSON ORIGINALES")
print("=" * 65)

for campo in campos:
    print(f"{campo:30} {contador[campo]}")