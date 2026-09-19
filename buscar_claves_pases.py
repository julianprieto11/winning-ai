import json
import glob
from collections import Counter

claves = Counter()

def recorrer(obj):
    if isinstance(obj, dict):
        for clave, valor in obj.items():
            clave_lower = clave.lower()

            if any(palabra in clave_lower for palabra in [
                "pass",
                "cross",
                "third",
                "forward",
                "half"
            ]):
                claves[clave] += 1

            recorrer(valor)

    elif isinstance(obj, list):
        for elemento in obj:
            recorrer(elemento)


for archivo in glob.glob("datos/partidos/*.json"):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)

        recorrer(datos)

    except Exception:
        pass


print("=" * 70)
print("CLAVES RELACIONADAS CON PASES")
print("=" * 70)

for clave, cantidad in claves.most_common():
    print(f"{clave:45} {cantidad}")