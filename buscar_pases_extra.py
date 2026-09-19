import json
import glob
from collections import Counter

buscados = [
    "forward",
    "final",
    "third",
    "ownHalf",
    "oppositionHalf",
    "longPass",
    "cross",
]

encontrados = Counter()

for archivo in glob.glob("datos/partidos/*.json"):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)

        texto = json.dumps(datos, ensure_ascii=False)

        for palabra in buscados:
            if palabra.lower() in texto.lower():
                encontrados[palabra] += 1

    except Exception:
        pass

print("=" * 70)
print("BÚSQUEDA DE ESTADÍSTICAS EXTRA DE PASE")
print("=" * 70)

for palabra, cantidad in encontrados.items():
    print(f"{palabra:20} aparece en {cantidad} partidos")