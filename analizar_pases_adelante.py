import json
import glob
from collections import Counter

pases = []

for archivo in glob.glob("datos/partidos/*.json"):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)

        def recorrer(obj):
            if isinstance(obj, dict):

                if (
                    obj.get("eventType") == "pass"
                    and "playerCoordinates" in obj
                    and "passEndCoordinates" in obj
                    and "isHome" in obj
                ):
                    origen = obj["playerCoordinates"]
                    destino = obj["passEndCoordinates"]

                    if (
                        isinstance(origen, dict)
                        and isinstance(destino, dict)
                        and "x" in origen
                        and "x" in destino
                    ):
                        if obj["isHome"]:
                            avance = destino["x"] - origen["x"]
                        else:
                            avance = origen["x"] - destino["x"]

                        pases.append(avance)

                for valor in obj.values():
                    recorrer(valor)

            elif isinstance(obj, list):
                for elemento in obj:
                    recorrer(elemento)

        recorrer(datos)

    except Exception:
        pass


print("=" * 70)
print("PASES HACIA ADELANTE")
print("=" * 70)

print("Pases normales con coordenadas:", len(pases))

adelante = [x for x in pases if x > 0]
atras = [x for x in pases if x < 0]
neutros = [x for x in pases if x == 0]

print("Hacia adelante:", len(adelante))
print("Hacia atrás:", len(atras))
print("Neutros:", len(neutros))

print()
print("Porcentaje hacia adelante:",
      round(len(adelante) / len(pases) * 100, 2), "%")

print()
print("Distribución del avance:")

rangos = [
    ("0 a 5", 0, 5),
    ("5 a 10", 5, 10),
    ("10 a 20", 10, 20),
    ("20 a 30", 20, 30),
    ("30+", 30, 999)
]

for nombre, minimo, maximo in rangos:
    cantidad = sum(
        1 for x in adelante
        if minimo < x <= maximo
    )
    print(f"{nombre:10} {cantidad}")