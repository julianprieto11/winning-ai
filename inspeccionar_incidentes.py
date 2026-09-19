import json
import glob
import collections

contador_tipo = collections.Counter()
contador_clase = collections.Counter()

archivos = glob.glob("datos/partidos/*.json")

partidos = 0
incidentes = 0

for archivo in archivos:
    with open(archivo, encoding="utf-8") as f:
        datos = json.load(f)

    partidos += 1

    lista = datos["incidents"].get("incidents", [])

    for incidente in lista:
        incidentes += 1

        tipo = incidente.get("incidentType")
        clase = incidente.get("incidentClass")

        if tipo:
            contador_tipo[tipo] += 1

        if clase:
            contador_clase[clase] += 1

print(f"PARTIDOS: {partidos}")
print(f"INCIDENTES: {incidentes}")
print()

print("=" * 60)
print("INCIDENT TYPES")
print("=" * 60)

for tipo, cantidad in sorted(contador_tipo.items()):
    print(f"{tipo}: {cantidad}")

print()
print("=" * 60)
print("INCIDENT CLASSES")
print("=" * 60)

for clase, cantidad in sorted(contador_clase.items()):
    print(f"{clase}: {cantidad}")