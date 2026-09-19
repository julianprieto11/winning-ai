import json
import glob

archivo = glob.glob("datos/partidos/*.json")[0]

with open(archivo, encoding="utf-8") as f:
    data = json.load(f)

estadisticas = data["statistics"]["statistics"]

print("Cantidad de bloques:", len(estadisticas))
print()

for bloque in estadisticas:
    print("BLOQUE:")
    print(bloque)
    print()