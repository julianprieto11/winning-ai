import json
import glob
import pandas as pd
from collections import defaultdict
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


# ==========================================================
# 1. POSICIONES SOFASCORE
# ==========================================================

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

                posicion = mapa.get(posicion)

                if not posicion:
                    continue

                equipo_data = item.get("team", {})

                if not isinstance(equipo_data, dict):
                    equipo_data = {}

                equipo = equipo_data.get("name")

                clave = (
                    normalizar_nombre(nombre),
                    normalizar_equipo(equipo),
                )

                sofa_posiciones[clave] = posicion

    except Exception:
        pass


# ==========================================================
# 2. PITCHAPI + POSICIÓN SOFASCORE
# ==========================================================

registros = []


for archivo in glob.glob(LINEUPS_GLOB):

    try:

        with open(archivo, "r", encoding="utf-8") as f:
            raw = json.load(f)

        data = raw.get("data", raw)

        match_id = data.get("match_id")

        for lado in ["home", "away"]:

            equipo = data.get(lado, {})

            jugadores = equipo.get("starters", [])

            for jugador in jugadores:

                nombre = jugador.get("name")
                x = jugador.get("pitch_x")
                y = jugador.get("pitch_y")

                if not nombre or x is None or y is None:
                    continue

                # Buscamos el jugador por nombre.
                posibles = []

                nombre_norm = normalizar_nombre(nombre)

                for clave, posicion in sofa_posiciones.items():

                    nombre_sofa, equipo_sofa = clave

                    if nombre_sofa == nombre_norm:
                        posibles.append(posicion)

                if len(posibles) == 0:
                    continue

                # Si hay más de una posición histórica,
                # usamos la primera para este análisis.
                posicion_sofa = posibles[0]

                registros.append({
                    "match_id": match_id,
                    "player_name": nombre,
                    "position_sofa": posicion_sofa,
                    "pitch_x": float(x),
                    "pitch_y": float(y),
                })

    except Exception:
        pass


df = pd.DataFrame(registros)

print("Registros cruzados:", len(df))
print("Jugadores únicos:", df["player_name"].nunique())


# ==========================================================
# 3. MOSTRAR JUGADORES CON POSICIONES MIXTAS
# ==========================================================

print()
print("=" * 90)
print("JUGADORES QUE APARECEN EN MÁS DE UNA POSICIÓN SOFASCORE")
print("=" * 90)

conteo = (
    df.groupby("player_name")["position_sofa"]
    .nunique()
    .sort_values(ascending=False)
)

mixtos = conteo[conteo > 1]

print("Jugadores con múltiples posiciones:", len(mixtos))

print()

for jugador in mixtos.head(30).index:

    sub = df[df["player_name"] == jugador]

    print()
    print("-" * 70)
    print(jugador)

    print(
        sub["position_sofa"]
        .value_counts()
        .to_string()
    )