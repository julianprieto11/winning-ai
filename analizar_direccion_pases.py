import json
import glob
import math

pases = []

for archivo in glob.glob("datos/partidos/*.json"):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)

        def recorrer(obj):
            if isinstance(obj, dict):

                if (
                    "playerCoordinates" in obj
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
                        dx = destino["x"] - origen["x"]

                        pases.append({
                            "isHome": obj["isHome"],
                            "origen_x": origen["x"],
                            "destino_x": destino["x"],
                            "dx": dx,
                            "eventType": obj.get("eventType")
                        })

                for valor in obj.values():
                    recorrer(valor)

            elif isinstance(obj, list):
                for elemento in obj:
                    recorrer(elemento)

        recorrer(datos)

    except Exception:
        pass


print("=" * 70)
print("ANÁLISIS DE DIRECCIÓN DE PASES")
print("=" * 70)

print("Pases encontrados:", len(pases))

for condicion, nombre in [
    (True, "LOCAL"),
    (False, "VISITANTE")
]:
    datos = [p for p in pases if p["isHome"] == condicion]

    if not datos:
        continue

    positivos = sum(1 for p in datos if p["dx"] > 0)
    negativos = sum(1 for p in datos if p["dx"] < 0)

    print()
    print(nombre)
    print("-" * 40)
    print("Cantidad:", len(datos))
    print("dx positivo:", positivos)
    print("dx negativo:", negativos)
    print("dx promedio:", round(sum(p["dx"] for p in datos) / len(datos), 2))

print()
print("=" * 70)
print("EJEMPLOS")
print("=" * 70)

for p in pases[:20]:
    print(
        f"{p['eventType']:12} "
        f"home={str(p['isHome']):5} "
        f"{p['origen_x']:5.1f} -> {p['destino_x']:5.1f} "
        f"dx={p['dx']:6.1f}"
    )