import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

terminos = [
    "shot",
    "remate",
    "danger",
    "dangerous",
    "xg",
    "expected",
]

encontrados = {}

archivos = sorted(CARPETA.glob("*_players.json"))

for archivo in archivos:
    try:
        data = json.loads(archivo.read_text(encoding="utf-8"))
    except Exception:
        continue

    jugadores = data.get("data", [])

    if not isinstance(jugadores, list):
        continue

    for jugador in jugadores:

        if not isinstance(jugador, dict):
            continue

        jugador_info = jugador.get("player", {})

        if isinstance(jugador_info, dict):
            nombre = jugador_info.get("name", "Desconocido")
        else:
            nombre = str(jugador_info)

        grupos = jugador.get("stats", [])

        if not isinstance(grupos, list):
            continue

        for grupo in grupos:

            if not isinstance(grupo, dict):
                continue

            grupo_nombre = grupo.get("key", "")
            stats = grupo.get("stats", {})

            if not isinstance(stats, dict):
                continue

            for nombre_stat, contenido in stats.items():

                if not isinstance(contenido, dict):
                    continue

                clave = contenido.get("key", "")

                stat = contenido.get("stat", {})

                if not isinstance(stat, dict):
                    continue

                valor = stat.get("value")

                texto = (
                    f"{grupo_nombre} "
                    f"{nombre_stat} "
                    f"{clave}"
                ).lower()

                if any(t in texto for t in terminos):

                    identificador = (
                        grupo_nombre,
                        nombre_stat,
                        clave
                    )

                    if identificador not in encontrados:
                        encontrados[identificador] = {
                            "archivo": archivo.name,
                            "jugador": nombre,
                            "valor": valor
                        }


print()
print("=" * 80)
print("CAMPOS RELACIONADOS CON REMATES / PELIGRO OFENSIVO")
print("=" * 80)
print()

for (grupo, nombre, clave), ejemplo in sorted(encontrados.items()):

    print(f"Grupo   : {grupo}")
    print(f"Campo   : {nombre}")
    print(f"Key     : {clave}")
    print(f"Ejemplo : {ejemplo['jugador']} -> {ejemplo['valor']}")
    print(f"Archivo : {ejemplo['archivo']}")
    print("-" * 80)

print()
print(f"Campos encontrados: {len(encontrados)}")