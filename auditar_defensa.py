import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

terminos = [
    "tackle",
    "interception",
    "block",
    "clearance",
    "duel",
    "aerial",
    "defend",
    "recover",
    "ball recovery",
    "foul",
]

encontrados = {}

archivos = sorted(CARPETA.glob("*_advanced_players.json"))

for archivo in archivos:

    try:
        data = json.loads(archivo.read_text(encoding="utf-8"))
    except Exception:
        continue

    jugadores = data.get("data", {}).get("players", [])

    if not isinstance(jugadores, list):
        continue

    for jugador in jugadores:

        if not isinstance(jugador, dict):
            continue

        info = jugador.get("player", {})

        if not isinstance(info, dict):
            continue

        nombre_jugador = info.get("name", "Desconocido")

        for grupo_nombre, grupo in jugador.items():

            if not isinstance(grupo, dict):
                continue

            for nombre_stat, valor in grupo.items():

                texto = (
                    f"{grupo_nombre} "
                    f"{nombre_stat}"
                ).lower()

                if not any(t in texto for t in terminos):
                    continue

                identificador = (
                    grupo_nombre,
                    nombre_stat
                )

                if identificador not in encontrados:

                    encontrados[identificador] = {
                        "archivo": archivo.name,
                        "jugador": nombre_jugador,
                        "valor": valor
                    }


print()
print("=" * 90)
print("CAMPOS DEFENSIVOS — PITCHAPI")
print("=" * 90)
print()

for (grupo, nombre), ejemplo in sorted(encontrados.items()):

    print(f"Grupo   : {grupo}")
    print(f"Campo   : {nombre}")
    print(f"Ejemplo : {ejemplo['jugador']} -> {ejemplo['valor']}")
    print(f"Archivo : {ejemplo['archivo']}")
    print("-" * 90)

print()
print(f"Campos encontrados: {len(encontrados)}")