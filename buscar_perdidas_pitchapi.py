import json
from pathlib import Path

BASE = Path("datos/pitchapi")

archivos = list(BASE.glob("*_advanced_players.json"))

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
]

campos_encontrados = {}

for archivo in archivos:

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        continue

    jugadores = data.get("data", {}).get("players", [])

    for jugador in jugadores:

        for grupo_nombre in [
            "carrying",
            "passing",
            "creation",
            "defending",
            "goalkeeping",
            "possession_value",
        ]:

            grupo = jugador.get(grupo_nombre, {})

            if not isinstance(grupo, dict):
                continue

            for nombre_campo, valor in grupo.items():

                texto = (
                    f"{grupo_nombre} "
                    f"{nombre_campo}"
                ).lower()

                if any(palabra in texto for palabra in palabras):

                    clave = (
                        grupo_nombre,
                        nombre_campo
                    )

                    if clave not in campos_encontrados:

                        campos_encontrados[clave] = {
                            "archivo": archivo.name,
                            "jugador": jugador.get(
                                "player", {}
                            ).get("name"),
                            "valor": valor,
                        }


print("=" * 100)
print("BÚSQUEDA DE CAMPOS RELACIONADOS CON PÉRDIDAS DE BALÓN")
print("=" * 100)

print(f"Archivos avanzados: {len(archivos)}")
print()

if not campos_encontrados:

    print("NO SE ENCONTRARON CAMPOS.")

else:

    for clave, ejemplo in campos_encontrados.items():

        grupo, campo = clave

        print(f"Grupo:       {grupo}")
        print(f"Campo:       {campo}")
        print(f"Ejemplo:     {ejemplo['jugador']}")
        print(f"Valor:       {ejemplo['valor']}")
        print(f"Archivo:     {ejemplo['archivo']}")
        print("-" * 100)

print()
print("=" * 100)
print("FIN")
print("=" * 100)