import json


def cargar_archivo(nombre):
    with open(nombre, "r", encoding="utf-8") as f:
        return json.load(f)


def encontrar_listas(obj):
    """
    Busca recursivamente todas las listas dentro del JSON.
    """
    listas = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, list):
                listas.append((key, value))
            elif isinstance(value, dict):
                listas.extend(encontrar_listas(value))

    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                listas.extend(encontrar_listas(item))

    return listas


def catalogar(nombre_archivo):
    data = cargar_archivo(nombre_archivo)

    print()
    print("=" * 80)
    print(f"ARCHIVO: {nombre_archivo}")
    print("=" * 80)

    listas = encontrar_listas(data)

    for nombre, lista in listas:

        if not lista:
            continue

        print()
        print(f"LISTA: {nombre}")
        print(f"ELEMENTOS: {len(lista)}")

        # Buscar todas las claves presentes en los objetos
        campos = set()

        for item in lista:
            if isinstance(item, dict):
                campos.update(item.keys())

        print(f"CAMPOS: {len(campos)}")

        for campo in sorted(campos):
            print(f"  - {campo}")


catalogar("pitchapi_players.json")
catalogar("pitchapi_advanced_players.json")

print()
print("=" * 80)
print("FIN DEL CATÁLOGO")
print("=" * 80)