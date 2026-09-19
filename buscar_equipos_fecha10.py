import json
import glob


buscar = [
    "cordoba",
    "gimnasia",
    "union",
    "independiente",
    "instituto",
    "talleres",
    "lanus",
    "estudiantes",
    "riestra",
    "defensa",
    "banfield",
]


equipos = set()

for archivo in glob.glob("datos/pitchapi/matches/*.json"):

    with open(archivo, encoding="utf-8") as f:
        data = json.load(f)

    partido = data["data"]

    equipos.add(partido["home_team"]["name"])
    equipos.add(partido["away_team"]["name"])


print()
print("NOMBRES DE EQUIPOS EN PITCHAPI")
print("=" * 60)

for equipo in sorted(equipos):

    nombre = equipo.lower()

    if any(palabra in nombre for palabra in buscar):
        print(equipo)

print()
print("=" * 60)