import json
import glob

total = 0
con_campo = 0
positivos = 0

for f in glob.glob("datos/partidos/*.json"):
    with open(f, encoding="utf-8") as archivo:
        d = json.load(archivo)

    for lado in ["home", "away"]:
        for p in d["lineups"].get(lado, {}).get("players", []):
            total += 1

            stats = p.get("statistics", {})

            if "penaltyWon" in stats:
                con_campo += 1

                if stats["penaltyWon"] > 0:
                    positivos += 1

print("Total registros:", total)
print("Con penaltyWon:", con_campo)
print("Sin penaltyWon:", total - con_campo)
print("PenaltyWon > 0:", positivos)
print("Cobertura:", round(con_campo / total * 100, 2), "%")