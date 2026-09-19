import json
import glob

archivos = glob.glob("datos/partidos/*.json")

encontrados = 0

for archivo in archivos:
    with open(archivo, encoding="utf-8") as f:
        datos = json.load(f)

    incidentes = datos["incidents"].get("incidents", [])

    for incidente in incidentes:
        if incidente.get("incidentType") == "goal":
            print("=" * 80)
            print("ARCHIVO:", archivo)
            print("GOAL:")
            print(incidente)
            print()

            encontrados += 1

            if encontrados >= 10:
                break

    if encontrados >= 10:
        break

print("=" * 80)
print("GOLES MOSTRADOS:", encontrados)