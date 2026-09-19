import json
import glob
import collections
import os

BASE = "datos/pitchapi/lineups"

files = glob.glob(os.path.join(BASE, "*_lineups.json"))

print("=" * 70)
print("AUDITORÍA COMPLETA DE POSITION_ID - PITCHAPI")
print("=" * 70)

print("Archivos de lineups:", len(files))

conteo = collections.Counter()
titulares = collections.Counter()
suplentes = collections.Counter()

jugadores = collections.defaultdict(set)
ejemplos = collections.defaultdict(list)

partidos = 0

for archivo in files:

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        continue

    root = data.get("data", {})

    if not isinstance(root, dict):
        continue

    partidos += 1

    for lado in ("home", "away"):

        equipo = root.get(lado, {})

        if not isinstance(equipo, dict):
            continue

        for grupo in ("starters", "subs"):

            lista = equipo.get(grupo, [])

            if not isinstance(lista, list):
                continue

            for jugador in lista:

                if not isinstance(jugador, dict):
                    continue

                position_id = jugador.get("position_id")

                if position_id is None:
                    continue

                position_id = str(position_id)

                nombre = jugador.get("name", "SIN NOMBRE")

                conteo[position_id] += 1
                jugadores[position_id].add(nombre)

                if grupo == "starters":
                    titulares[position_id] += 1
                else:
                    suplentes[position_id] += 1

                if len(ejemplos[position_id]) < 10:

                    ejemplo = (
                        f"{nombre} "
                        f"({'TIT' if grupo == 'starters' else 'SUP'})"
                    )

                    if ejemplo not in ejemplos[position_id]:
                        ejemplos[position_id].append(ejemplo)


print()
print("Partidos procesados:", partidos)
print("Position IDs distintos:", len(conteo))

print()
print("-" * 70)
print("RESUMEN DE POSITION IDs")
print("-" * 70)

for position_id, cantidad in sorted(
    conteo.items(),
    key=lambda x: int(x[0])
):

    print()
    print(f"POSITION_ID: {position_id}")
    print(f"  Total       : {cantidad}")
    print(f"  Titulares   : {titulares[position_id]}")
    print(f"  Suplentes   : {suplentes[position_id]}")
    print(f"  Jugadores   : {len(jugadores[position_id])}")
    print(
        "  Ejemplos    : "
        + ", ".join(ejemplos[position_id])
    )

print()
print("=" * 70)
print("FIN DE AUDITORÍA")
print("=" * 70)