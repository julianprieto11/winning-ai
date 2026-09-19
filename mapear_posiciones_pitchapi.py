import json
import glob
import pandas as pd
from collections import defaultdict, Counter
import re


LINEUPS_GLOB = "datos/pitchapi/lineups/*_lineups.json"
SOFASCORE_GLOB = "datos/partidos/*.json"


def normalizar_nombre(nombre):
    if not nombre:
        return ""

    nombre = str(nombre).lower().strip()

    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }

    for a, b in reemplazos.items():
        nombre = nombre.replace(a, b)

    nombre = re.sub(r"[^a-z0-9\s]", "", nombre)
    nombre = re.sub(r"\s+", " ", nombre)

    return nombre


def normalizar_equipo(nombre):
    if not nombre:
        return ""

    nombre = str(nombre).lower().strip()

    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }

    for a, b in reemplazos.items():
        nombre = nombre.replace(a, b)

    aliases = {
        "club atletico belgrano": "belgrano",
        "belgrano": "belgrano",

        "central cordoba": "central cordoba de santiago",
        "central cordoba de santiago": "central cordoba de santiago",

        "estudiantes de la plata": "estudiantes",
        "estudiantes": "estudiantes",

        "gimnasia y esgrima": "gimnasia lp",
        "gimnasia lp": "gimnasia lp",

        "gimnasia y esgrima mendoza": "gimnasia mendoza",
        "gimnasia mendoza": "gimnasia mendoza",

        "ca independiente": "independiente",
        "independiente": "independiente",

        "ca lanus": "lanus",
        "lanus": "lanus",

        "ca talleres": "talleres",
        "talleres": "talleres",

        "instituto de cordoba": "instituto",
        "instituto": "instituto",

        "club atletico union de santa fe": "union",
        "union": "union",
    }

    return aliases.get(nombre, nombre)


# =========================================================
# 1. CARGAR POSICIONES DE SOFASCORE
# =========================================================

sofa_posiciones = {}

for archivo in glob.glob(SOFASCORE_GLOB):

    try:

        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)

        lineups = data.get("lineups", {})

        for lado in ["home", "away"]:

            jugadores = lineups.get(lado, [])

            if isinstance(jugadores, dict):
                jugadores = jugadores.get("players", [])

            for item in jugadores:

                jugador = item.get("player", item)

                nombre = jugador.get("name")
                posicion = jugador.get("position")

                if not nombre or not posicion:
                    continue

                mapa = {
                    "G": "ARQ",
                    "D": "DEF",
                    "M": "VOL",
                    "F": "DEL",
                }

                posicion_norm = mapa.get(posicion)

                if not posicion_norm:
                    continue

                # Intentamos obtener equipo
                equipo = (
                    item.get("team", {})
                    if isinstance(item.get("team"), dict)
                    else {}
                )

                equipo_nombre = equipo.get("name")

                clave = (
                    normalizar_nombre(nombre),
                    normalizar_equipo(equipo_nombre),
                )

                sofa_posiciones[clave] = posicion_norm

    except Exception:
        pass


print("Jugadores SofaScore con posición:", len(sofa_posiciones))


# =========================================================
# 2. ANALIZAR PITCHAPI
# =========================================================

conteo = defaultdict(Counter)

total = 0
coincidencias = 0


for archivo in glob.glob(LINEUPS_GLOB):

    try:

        with open(archivo, "r", encoding="utf-8") as f:
            raw = json.load(f)

        data = raw.get("data", raw)

        for lado in ["home", "away"]:

            equipo = data.get(lado, {})

            # PitchAPI devuelve el equipo como dict
            equipo_data = (
                equipo.get("team", {})
                if isinstance(equipo.get("team"), dict)
                else {}
            )

            equipo_nombre = equipo_data.get("name")

            # Algunos archivos pueden tener el nombre en otro nivel
            if not equipo_nombre:
                equipo_nombre = equipo.get("name")

            jugadores = equipo.get("starters", [])

            for jugador in jugadores:

                nombre = jugador.get("name")

                x = jugador.get("pitch_x")
                y = jugador.get("pitch_y")

                if not nombre or x is None or y is None:
                    continue

                total += 1

                clave = (
                    normalizar_nombre(nombre),
                    normalizar_equipo(equipo_nombre),
                )

                posicion = sofa_posiciones.get(clave)

                if not posicion:
                    continue

                coincidencias += 1

                x_r = round(float(x), 3)
                y_r = round(float(y), 3)

                conteo[(x_r, y_r)][posicion] += 1

    except Exception:
        pass


print("Registros PitchAPI analizados:", total)
print("Coincidencias nombre + equipo:", coincidencias)


# =========================================================
# 3. MAPA
# =========================================================

print()
print("=" * 90)
print("MAPA PITCH_X / PITCH_Y → POSICIÓN SOFASCORE")
print("=" * 90)


filas = []

for (x, y), contador in conteo.items():

    total_zona = sum(contador.values())

    filas.append({
        "pitch_x": x,
        "pitch_y": y,
        "total": total_zona,
        "ARQ": contador["ARQ"],
        "DEF": contador["DEF"],
        "VOL": contador["VOL"],
        "DEL": contador["DEL"],
    })


df = pd.DataFrame(filas)

if not df.empty:

    df = df.sort_values(
        ["pitch_x", "pitch_y"]
    )

    print(df.to_string(index=False))

    df.to_csv(
        "datos/mapa_posiciones_pitchapi.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print()
    print("GUARDADO:")
    print("datos/mapa_posiciones_pitchapi.csv")

else:

    print("No se encontraron coincidencias.")