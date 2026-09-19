import json
import glob
import pandas as pd

df = pd.read_csv("datos/dataset_jugadores.csv")

# Asistencias según el campo goalAssist del dataset
asistencias_csv = df["goalAssist"].fillna(0).sum()

# Asistencias encontradas en los incidentes
asistencias_incidentes = 0

for archivo in glob.glob("datos/partidos/*.json"):
    with open(archivo, "r", encoding="utf-8") as f:
        datos = json.load(f)

    incidentes = datos.get("incidents", {}).get("incidents", [])

    for incidente in incidentes:
        if incidente.get("incidentType") == "goal":
            asistencia = incidente.get("assist1")

            if asistencia:
                asistencias_incidentes += 1

print("=== COMPARACION DE ASISTENCIAS ===")
print()
print(f"Asistencias según goalAssist: {asistencias_csv:.0f}")
print(f"Asistencias según incidentes: {asistencias_incidentes}")
print()
print(f"Diferencia: {asistencias_csv - asistencias_incidentes:.0f}")