import json
import glob
from collections import Counter

archivos = glob.glob("datos/partidos/*.json")

print(f"Partidos analizados: {len(archivos)}")
print()

# Buscamos claves relacionadas con gambetas y corners
palabras = [
    "dribble",
    "dribbleWon",
    "successfulDribble",
    "corner",
    "cornerWon"
]

encontradas = Counter()

for archivo in archivos:
    with open(archivo, "r", encoding="utf-8") as f:
        datos = json.load(f)

    def recorrer(obj):
        if isinstance(obj, dict):
            for clave, valor in obj.items():

                clave_lower = str(clave).lower()

                for palabra in palabras:
                    if palabra.lower() in clave_lower:
                        encontradas[clave] += 1

                recorrer(valor)

        elif isinstance(obj, list):
            for elemento in obj:
                recorrer(elemento)

    recorrer(datos)

print("=== CLAVES ENCONTRADAS ===")
print()

for clave, cantidad in encontradas.most_common():
    print(f"{clave}: {cantidad}")