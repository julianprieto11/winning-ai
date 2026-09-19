import json
from pathlib import Path

BASE = Path("datos/pitchapi")

archivos = [
    archivo
    for archivo in BASE.glob("*_players.json")
    if not archivo.name.endswith("_advanced_players.json")
]

print("=" * 100)
print("BÚSQUEDA DE CAMPOS RELACIONADOS CON ÚLTIMO TERCIO")
print("=" * 100)
print(f"Archivos: {len(archivos)}")
print()

campos_encontrados = {}

for archivo in archivos:

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        continue

    jugadores = data.get("data", [])

    for jugador in jugadores:

        for grupo in jugador.get("stats", []):

            grupo_key = grupo.get("key")
            stats = grupo.get("stats", {})

            if not isinstance(stats, dict):
                continue

            for nombre_campo, dato in stats.items():

                texto = (
                    f"{grupo_key} "
                    f"{nombre_campo} "
                    f"{dato.get('key', '')}"
                ).lower()

                palabras = [
                    "final third",
                    "final_third",
                    "last third",
                    "ultimo tercio",
                    "lastthird",
                    "third",
                ]

                if any(palabra in texto for palabra in palabras):

                    clave = (
                        grupo_key,
                        nombre_campo,
                        dato.get("key")
                    )

                    if clave not in campos_encontrados:
                        campos_encontrados[clave] = {
                            "archivo": archivo.name,
                            "jugador": jugador.get("player", {}).get("name"),
                            "valor": dato.get("stat", {}).get("value"),
                        }


print("=" * 100)
print("CAMPOS ENCONTRADOS")
print("=" * 100)
print()

if not campos_encontrados:
    print("NO SE ENCONTRARON CAMPOS RELACIONADOS CON 'FINAL THIRD'.")
else:

    for clave, ejemplo in campos_encontrados.items():

        grupo, nombre, key = clave

        print(f"Grupo:       {grupo}")
        print(f"Campo:       {nombre}")
        print(f"Key:         {key}")
        print(f"Ejemplo:     {ejemplo['jugador']}")
        print(f"Valor:       {ejemplo['valor']}")
        print(f"Archivo:     {ejemplo['archivo']}")
        print("-" * 100)

print()
print("=" * 100)
print("FIN")
print("=" * 100)