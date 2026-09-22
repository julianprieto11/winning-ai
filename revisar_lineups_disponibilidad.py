import json
import glob

archivos = glob.glob("datos/pitchapi/lineups/*_lineups.json")

print("ARCHIVOS:", len(archivos))

claves = set()
ejemplo = None

for f in archivos:
    with open(f, encoding="utf-8") as archivo:
        d = json.load(archivo)

    data = d.get("data", d)

    for lado in ["home", "away"]:
        equipo = data.get(lado, {})
        for grupo in ["starters", "subs"]:
            jugadores = equipo.get(grupo) or []

            for jugador in jugadores:
                claves.update(jugador.keys())

                if ejemplo is None:
                    ejemplo = jugador

print("CLAVES DE LOS JUGADORES:")
for clave in sorted(claves):
    print("-", clave)

print("\nEJEMPLO:")
print(ejemplo)
