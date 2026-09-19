import json

match_id = "15269907"

archivo = f"datos/partidos/{match_id}.json"

with open(archivo, "r", encoding="utf-8") as f:
    datos = json.load(f)

incidentes = datos["incidents"]["incidents"]

print()
print("=" * 100)
print(f"SUSTITUCIONES DEL PARTIDO {match_id}")
print("=" * 100)

for incidente in incidentes:

    if incidente.get("incidentType") != "substitution":
        continue

    print()
    print("MINUTO:", incidente.get("time"))
    print("CLASE:", incidente.get("incidentClass"))
    print("ID:", incidente.get("id"))
    print("INCIDENTE COMPLETO:")
    print(incidente)

print()
print("=" * 100)