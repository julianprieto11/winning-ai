import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

terminos = [
    "dangerous",
    "danger",
    "shot",
    "corner",
    "offside",
    "pass",
]

encontrados = {}

for archivo in CARPETA.glob("*.json"):

    try:
        data = json.loads(archivo.read_text(encoding="utf-8"))
    except Exception:
        continue

    def recorrer(obj, ruta=""):
        if isinstance(obj, dict):

            for clave, valor in obj.items():

                texto = str(clave).lower()

                if any(termino in texto for termino in terminos):
                    identificador = (ruta, clave)

                    if identificador not in encontrados:
                        encontrados[identificador] = {
                            "archivo": archivo.name,
                            "ruta": ruta,
                            "clave": clave,
                            "valor": valor
                        }

                recorrer(valor, f"{ruta}.{clave}")

        elif isinstance(obj, list):

            for i, elemento in enumerate(obj):
                recorrer(elemento, f"{ruta}[{i}]")

    recorrer(data)


print()
print("=" * 100)
print("BÚSQUEDA SIMPLE — ACCIONES PENDIENTES")
print("=" * 100)
print()

for item in encontrados.values():

    print(f"Archivo : {item['archivo']}")
    print(f"Ruta    : {item['ruta']}")
    print(f"Campo   : {item['clave']}")

    valor = item["valor"]

    if isinstance(valor, (dict, list)):
        print(f"Valor   : {str(valor)[:500]}")
    else:
        print(f"Valor   : {valor}")

    print("-" * 100)

print()
print(f"Coincidencias encontradas: {len(encontrados)}")