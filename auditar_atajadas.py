import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

terminos = [
    "save",
    "saved",
    "saves",
    "shot",
    "goal",
    "conceded",
    "prevented"
]

encontrados = {}

archivos = sorted(CARPETA.glob("*.json"))

for archivo in archivos:

    try:
        data = json.loads(
            archivo.read_text(encoding="utf-8")
        )
    except Exception:
        continue

    def recorrer(obj, ruta=""):

        if isinstance(obj, dict):

            for key, value in obj.items():

                key_texto = str(key).lower()

                if any(
                    termino in key_texto
                    for termino in terminos
                ):

                    if key not in encontrados:

                        encontrados[key] = {
                            "ruta": ruta,
                            "ejemplo": value,
                            "archivo": archivo.name
                        }

                nueva_ruta = (
                    f"{ruta}.{key}"
                    if ruta
                    else str(key)
                )

                recorrer(value, nueva_ruta)

        elif isinstance(obj, list):

            for item in obj:
                recorrer(item, ruta)

    recorrer(data)


print()
print("=" * 100)
print("ATAJADAS / GOLES RECIBIDOS — PITCHAPI")
print("=" * 100)
print()

print(f"Archivos analizados: {len(archivos)}")
print(f"Campos encontrados: {len(encontrados)}")
print()

for key, info in sorted(encontrados.items()):

    print(f"KEY: {key}")
    print(f"  Ruta:     {info['ruta']}")
    print(f"  Ejemplo:  {info['ejemplo']}")
    print(f"  Archivo:  {info['archivo']}")
    print("-" * 100)

print()
print("Fin.")