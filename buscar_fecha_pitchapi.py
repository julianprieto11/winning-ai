import json
import glob
import os

BASE = "datos/pitchapi"

print("=" * 70)
print("BUSCANDO FECHA DE PARTIDOS EN PITCHAPI")
print("=" * 70)

encontrados = 0

for archivo in glob.glob(
    os.path.join(BASE, "**", "*.json"),
    recursive=True
):

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        continue

    root = data.get("data", data)

    if not isinstance(root, dict):
        continue

    # Buscamos campos que puedan contener fecha/hora
    campos = []

    for key, value in root.items():

        key_lower = str(key).lower()

        if any(
            palabra in key_lower
            for palabra in [
                "date",
                "time",
                "timestamp",
                "start",
                "kickoff"
            ]
        ):

            campos.append((key, value))

    if campos:

        print()
        print("ARCHIVO:", archivo)

        for key, value in campos:

            print(
                f"  {key}: {value}"
            )

        encontrados += 1

        if encontrados >= 20:
            break


print()
print("=" * 70)
print("Archivos con posibles campos de fecha:", encontrados)
print("=" * 70)