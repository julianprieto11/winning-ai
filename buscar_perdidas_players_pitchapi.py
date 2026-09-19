import json
from pathlib import Path

BASE = Path("datos/pitchapi")

archivos = [
    archivo
    for archivo in BASE.glob("*_players.json")
    if not archivo.name.endswith("_advanced_players.json")
]

palabras = [
    "loss",
    "lost",
    "turnover",
    "turnovers",
    "dispossessed",
    "possession lost",
    "possession_loss",
    "miscontrol",
    "miscontrols",
    "bad touch",
    "bad_touch",
    "possession",
]

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

                key = dato.get("key", "")

                texto = (
                    f"{grupo_key} "
                    f"{nombre_campo} "
                    f"{key}"
                ).lower()

                if any(palabra in texto for palabra in palabras):

                    clave = (
                        grupo_key,
                        nombre_campo,
                        key
                    )

                    if clave not in campos_encontrados:

                        campos_encontrados[clave] = {
                            "archivo": archivo.name,
                            "jugador": jugador.get(
                                "player", {}
                            ).get("name"),
                            "valor": dato.get(
                                "stat", {}
                            ).get("value"),
                        }


print("=" * 100)
print("BÚSQUEDA DE CAMPOS DE PÉRDIDAS - PITCHAPI PLAYERS")
print("=" * 100)

print(f"Archivos: {len(archivos)}")
print()

if not campos_encontrados:

    print("NO SE ENCONTRARON CAMPOS.")

else:

    for clave, ejemplo in campos_encontrados.items():

        grupo, campo, key = clave

        print(f"Grupo:       {grupo}")
        print(f"Campo:       {campo}")
        print(f"Key:         {key}")
        print(f"Ejemplo:     {ejemplo['jugador']}")
        print(f"Valor:       {ejemplo['valor']}")
        print(f"Archivo:     {ejemplo['archivo']}")
        print("-" * 100)

print()
print("=" * 100)
print("FIN")
print("=" * 100)