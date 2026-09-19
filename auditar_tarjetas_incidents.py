import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

encontrados = {}

for archivo in sorted(CARPETA.glob("*.json")):

    if archivo.name.endswith("_players.json"):
        continue

    if archivo.name.endswith("_advanced_players.json"):
        continue

    try:
        data = json.loads(archivo.read_text(encoding="utf-8"))
    except Exception:
        continue

    # Por si el archivo contiene directamente una lista de incidents
    incidents = data.get("data", {}).get("incidents")

    if incidents is None:
        incidents = data.get("incidents")

    if not isinstance(incidents, list):
        continue

    for incidente in incidents:

        if not isinstance(incidente, dict):
            continue

        texto = json.dumps(
            incidente,
            ensure_ascii=False
        ).lower()

        palabras = [
            "yellow",
            "red",
            "card",
            "second yellow",
            "yellow card",
        ]

        if not any(p in texto for p in palabras):
            continue

        # Guardamos la estructura completa del primer ejemplo
        tipo = (
            incidente.get("incidentType")
            or incidente.get("incident_type")
            or incidente.get("type")
            or "desconocido"
        )

        clave = str(tipo)

        if clave not in encontrados:
            encontrados[clave] = {
                "archivo": archivo.name,
                "incidente": incidente
            }

print()
print("=" * 100)
print("TARJETAS / EXPULSIONES — INCIDENTS PITCHAPI")
print("=" * 100)
print()

for tipo, ejemplo in encontrados.items():

    print(f"Tipo: {tipo}")
    print(f"Archivo: {ejemplo['archivo']}")
    print("Incidente:")

    print(
        json.dumps(
            ejemplo["incidente"],
            ensure_ascii=False,
            indent=2
        )
    )

    print("-" * 100)

print()
print(f"Tipos encontrados: {len(encontrados)}")