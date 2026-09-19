import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

terminos = [
    "recover",
    "recovery",
    "blocked pass",
    "pass blocked",
    "blocked cross",
    "cross blocked",
    "goal line",
    "goal-line",
    "dribbled past",
    "interception",
    "intercept",
]

encontrados = {}

for archivo in sorted(CARPETA.glob("*_players.json")):

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

        nombre = jugador.get("player", {}).get("name", "Desconocido")

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

                key = contenido.get("key", "")
                texto = f"{grupo_nombre} {nombre_stat} {key}".lower()

                if not any(t in texto for t in terminos):
                    continue

                identificador = (
                    grupo_nombre,
                    nombre_stat,
                    key
                )

                if identificador not in encontrados:

                    stat = contenido.get("stat", {})

                    encontrados[identificador] = {
                        "jugador": nombre,
                        "valor": stat.get("value"),
                        "archivo": archivo.name
                    }

print()
print("=" * 100)
print("ACCIONES DEFENSIVAS FALTANTES — PITCHAPI")
print("=" * 100)
print()

for (grupo, nombre, key), ejemplo in sorted(encontrados.items()):

    print(f"Grupo   : {grupo}")
    print(f"Campo   : {nombre}")
    print(f"Key     : {key}")
    print(f"Ejemplo : {ejemplo['jugador']} -> {ejemplo['valor']}")
    print(f"Archivo : {ejemplo['archivo']}")
    print("-" * 100)

print()
print(f"Campos encontrados: {len(encontrados)}")