import json


def recorrer(obj, ruta=""):
    if isinstance(obj, dict):
        for clave, valor in obj.items():
            nueva_ruta = f"{ruta}.{clave}" if ruta else clave

            if isinstance(valor, dict):
                print(f"[OBJETO] {nueva_ruta}")
                recorrer(valor, nueva_ruta)

            elif isinstance(valor, list):
                print(f"[LISTA]  {nueva_ruta} -> {len(valor)} elementos")

                if valor and isinstance(valor[0], dict):
                    recorrer(valor[0], nueva_ruta + "[0]")

            else:
                print(f"[CAMPO]  {nueva_ruta} -> {valor!r}")

    elif isinstance(obj, list):
        print(f"[LISTA]  {ruta} -> {len(obj)} elementos")


def inspeccionar(nombre):
    print()
    print("=" * 90)
    print(f"ARCHIVO: {nombre}")
    print("=" * 90)
    print()

    with open(nombre, "r", encoding="utf-8") as f:
        data = json.load(f)

    recorrer(data)


inspeccionar("pitchapi_players.json")
inspeccionar("pitchapi_advanced_players.json")

print()
print("=" * 90)
print("FIN")
print("=" * 90)