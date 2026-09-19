import json
import glob
from collections import Counter

tipos = Counter()
total = 0
ejemplos = {}

for archivo in glob.glob("datos/partidos/*.json"):

    datos = json.load(open(archivo, encoding="utf-8"))

    for incidente in datos["incidents"]["incidents"]:

        if incidente.get("incidentType") != "goal":
            continue

        # Buscamos la asistencia dentro del gol
        asistencia = incidente.get("assist1")

        if not asistencia:
            continue

        total += 1

        # Guardamos las claves que SofaScore nos está dando
        for clave, valor in asistencia.items():
            tipos[clave] += 1

            if clave not in ejemplos:
                ejemplos[clave] = valor

print("=" * 60)
print("ANÁLISIS DE ASISTENCIAS SOFASCORE")
print("=" * 60)

print()
print("Total de asistencias encontradas:", total)

print()
print("CAMPOS DISPONIBLES")
print("-" * 40)

for campo, cantidad in tipos.most_common():
    print(f"{campo}: {cantidad}")

print()
print("EJEMPLOS")
print("-" * 40)

for campo, valor in ejemplos.items():
    print(f"{campo}: {valor}")