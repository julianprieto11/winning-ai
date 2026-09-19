import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

terminos = [
    "danger",
    "dangerous",
    "penalty",
    "penalties",
    "penal",
    "offside",
    "offside pass",
    "offside_pass",
    "pass offside",
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

        info = jugador.get("player", {})

        if isinstance(info, dict):
            nombre_jugador = info.get("name", "Desconocido")
        else:
            nombre_jugador = str(info)

        for grupo in jugador.get("stats", []):

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
                            "jugador": nombre_jugador,
                            "valor": valor
                        }


print()
print("=" * 90)
print("ACCIONES WINNING PENDIENTES")
print("=" * 90)
print()

for (grupo, nombre, clave), ejemplo in sorted(encontrados.items()):

    print(f"Grupo   : {grupo}")
    print(f"Campo   : {nombre}")
    print(f"Key     : {clave}")
    print(f"Ejemplo : {ejemplo['jugador']} -> {ejemplo['valor']}")
    print(f"Archivo : {ejemplo['archivo']}")
    print("-" * 90)

print()
print(f"Campos encontrados: {len(encontrados)}")