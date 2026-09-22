import json
import glob

archivos = glob.glob("datos/pitchapi/*_players.json")

print("ARCHIVOS:", len(archivos))

r = 0
claves = set()

for f in archivos[:20]:
    with open(f, encoding="utf-8") as archivo:
        d = json.load(archivo)

    data = d.get("data", d)

    if isinstance(data, list):
        for x in data:
            r += 1
            p = x.get("player", {})
            claves.update(p.keys())

print("JUGADORES REVISADOS:", r)
print("CLAVES PLAYER:")
for clave in sorted(claves):
    print("-", clave)
