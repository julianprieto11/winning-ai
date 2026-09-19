import json
import glob


BUSCAR = [
    "córdoba",
    "cordoba",
    "defensa",
    "justicia",
    "platense",
    "newell",
]


equipos = set()

for archivo in glob.glob("datos/pitchapi/matches/*.json"):

    with open(archivo, encoding="utf-8") as f:
        data = json.load(f)

    partido = data["data"]

    equipos.add(partido["home_team"]["name"])
    equipos.add(partido["away_team"]["name"])


print()
print("EQUIPOS RELEVANTES EN PITCHAPI")
print("=" * 60)

for equipo in sorted(equipos):

    if any(palabra in equipo.lower() for palabra in BUSCAR):
        print(equipo)

print()