import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

campos = {}

archivos = sorted(CARPETA.glob("*_players.json"))

for archivo in archivos:

    try:
        data = json.loads(
            archivo.read_text(encoding="utf-8")
        )
    except Exception:
        continue

    jugadores = data.get("data", [])

    if not isinstance(jugadores, list):
        continue

    for jugador in jugadores:

        stats = jugador.get("stats", [])

        if not isinstance(stats, list):
            continue

        for grupo in stats:

            grupo_key = grupo.get("key")
            grupo_stats = grupo.get("stats", {})

            if not isinstance(grupo_stats, dict):
                continue

            for nombre, info in grupo_stats.items():

                if not isinstance(info, dict):
                    continue

                key = info.get("key")

                if not key:
                    continue

                texto = (
                    f"{grupo_key}.{nombre}"
                )

                if any(
                    palabra in texto.lower()
                    for palabra in [
                        "pass",
                        "pase",
                        "cross",
                        "assist",
                        "through",
                        "key",
                        "switch"
                    ]
                ):

                    if key not in campos:

                        valor = (
                            info
                            .get("stat", {})
                            .get("value")
                        )

                        campos[key] = {
                            "grupo": grupo_key,
                            "nombre": nombre,
                            "ejemplo": valor,
                            "archivo": archivo.name,
                            "player": jugador.get(
                                "player", {}
                            ).get("name")
                        }


print()
print("=" * 100)
print("CAMPOS DE PASES — PITCHAPI")
print("=" * 100)
print()

print(f"Archivos analizados: {len(archivos)}")
print(f"Campos encontrados: {len(campos)}")
print()

for key, info in sorted(
    campos.items(),
    key=lambda x: (
        str(x[1]["grupo"]),
        str(x[0])
    )
):

    print(f"KEY: {key}")
    print(f"  Grupo:    {info['grupo']}")
    print(f"  Nombre:   {info['nombre']}")
    print(f"  Ejemplo:  {info['ejemplo']}")
    print(f"  Jugador:  {info['player']}")
    print(f"  Archivo:  {info['archivo']}")
    print("-" * 100)

print()
print("Fin.")