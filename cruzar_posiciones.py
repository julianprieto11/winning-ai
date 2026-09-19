import json
import csv
import glob
import os
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURACIÓN
# ============================================================

SOFASCORE_DIR = "datos/partidos"
PITCHAPI_MATCHES_DIR = "datos/pitchapi/matches"

DATASET_INPUT = "datos/dataset_winning_pitchapi.csv"
DATASET_OUTPUT = "datos/dataset_winning_pitchapi_posiciones.csv"

ARG_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalizar(texto):

    if not texto:
        return ""

    texto = str(texto).strip().lower()

    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
        "’": "'",
    }

    for viejo, nuevo in reemplazos.items():
        texto = texto.replace(viejo, nuevo)

    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def normalizar_equipo(nombre):

    nombre = normalizar(nombre)

    aliases = {
        "def y justicia": "defensa y justicia",

        "newells": "newells old boys",
        "newells old boys": "newells old boys",

        "gimnasia lp": "gimnasia y esgrima",
        "gimnasia y esgrima": "gimnasia y esgrima",

        "independiente r": "independiente rivadavia",

        "atletico tucuman": "atletico tucuman",

        "estudiantes de rio cuarto": "estudiantes de rio cuarto",
    }

    return aliases.get(nombre, nombre)


# ============================================================
# FECHA DESDE TIMESTAMP
# ============================================================

def fecha_desde_timestamp(timestamp):

    if timestamp is None:
        return None

    try:

        dt = datetime.fromtimestamp(
            int(timestamp),
            tz=timezone.utc
        ).astimezone(ARG_TZ)

        return dt.strftime("%Y-%m-%d")

    except Exception:
        return None


# ============================================================
# INDEXAR SOFASCORE
# ============================================================

print("=" * 100)
print("INDEXANDO SOFASCORE")
print("=" * 100)

archivos_sofascore = glob.glob(
    os.path.join(SOFASCORE_DIR, "*.json")
)

print(f"\nArchivos SofaScore encontrados: {len(archivos_sofascore)}")

sofascore_partidos = {}
sofascore_jugadores = {}

for archivo in archivos_sofascore:

    try:

        with open(
            archivo,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

    except Exception:

        continue

    # ========================================================
    # ESTRUCTURA REAL
    #
    # data
    #   └── event
    #       └── event
    # ========================================================

    event_wrapper = data.get("event")

    if not isinstance(event_wrapper, dict):
        continue

    event = event_wrapper.get("event")

    if not isinstance(event, dict):
        continue

    home_team = event.get("homeTeam", {})
    away_team = event.get("awayTeam", {})

    if not isinstance(home_team, dict):
        continue

    if not isinstance(away_team, dict):
        continue

    home_name = home_team.get("name")
    away_name = away_team.get("name")

    timestamp = event.get("startTimestamp")

    fecha = fecha_desde_timestamp(timestamp)

    if not home_name or not away_name or not fecha:
        continue

    clave_partido = (
        fecha,
        normalizar_equipo(home_name),
        normalizar_equipo(away_name),
    )

    sofascore_partidos[clave_partido] = {
        "archivo": archivo,
        "event_id": event.get("id"),
        "home_name": home_name,
        "away_name": away_name,
        "fecha": fecha,
    }

    # ========================================================
    # LINEUPS
    # ========================================================

    lineups = data.get("lineups", {})

    if not isinstance(lineups, dict):
        continue

    for lado in ["home", "away"]:

        bloque = lineups.get(lado)

        if not isinstance(bloque, dict):
            continue

        jugadores = bloque.get("players", [])

        if not isinstance(jugadores, list):
            continue

        for registro in jugadores:

            if not isinstance(registro, dict):
                continue

            player = registro.get("player", {})

            if not isinstance(player, dict):
                continue

            player_id = player.get("id")
            player_name = player.get("name")

            if player_id is None or not player_name:
                continue

            posicion = registro.get("position")

            clave_jugador = (
                clave_partido,
                normalizar(player_name)
            )

            sofascore_jugadores[clave_jugador] = {
                "player_id": player_id,
                "player_name": player_name,
                "position": posicion,
                "substitute": registro.get("substitute"),
                "team_side": lado,
                "event_id": event.get("id"),
            }


print(f"Partidos SofaScore indexados: {len(sofascore_partidos)}")
print(f"Registros de jugadores SofaScore: {len(sofascore_jugadores)}")


# ============================================================
# CARGAR DATASET PITCHAPI
# ============================================================

print("\n" + "=" * 100)
print("CARGANDO DATASET PITCHAPI")
print("=" * 100)

with open(
    DATASET_INPUT,
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(f)

    filas = list(reader)

print(f"\nRegistros PitchAPI: {len(filas)}")


# ============================================================
# INDEXAR PARTIDOS PITCHAPI
# ============================================================

print("\n" + "=" * 100)
print("INDEXANDO PARTIDOS PITCHAPI")
print("=" * 100)

pitchapi_partidos = {}

archivos_pitchapi = glob.glob(
    os.path.join(
        PITCHAPI_MATCHES_DIR,
        "*.json"
    )
)

for archivo in archivos_pitchapi:

    try:

        with open(
            archivo,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

    except Exception:

        continue

    partido = data.get("data")

    if not isinstance(partido, dict):
        continue

    match_id = partido.get("id")

    if not match_id:
        continue

    fecha = partido.get("date")

    home_team = partido.get("home_team", {})
    away_team = partido.get("away_team", {})

    home_name = (
        home_team.get("name")
        if isinstance(home_team, dict)
        else None
    )

    away_name = (
        away_team.get("name")
        if isinstance(away_team, dict)
        else None
    )

    pitchapi_partidos[match_id] = {
        "id": match_id,
        "fecha": fecha,
        "home_name": home_name,
        "away_name": away_name,
        "archivo": archivo,
    }


print(f"\nPartidos PitchAPI indexados: {len(pitchapi_partidos)}")


# ============================================================
# CRUZAR POSICIONES
# ============================================================

print("\n" + "=" * 100)
print("CRUZANDO POSICIONES")
print("=" * 100)

posicion_encontrada = 0
partido_no_encontrado = 0
jugador_no_encontrado = 0

conteo_posiciones = {
    "G": 0,
    "D": 0,
    "M": 0,
    "F": 0,
}

# Para diagnóstico
ejemplos_cruce = []


# ============================================================
# RECORRER DATASET
# ============================================================

for fila in filas:

    match_id = fila.get("match_id")
    player_name = fila.get("player_name")

    fila["posicion_sofascore"] = ""
    fila["sofascore_player_id"] = ""

    # --------------------------------------------------------
    # Buscar partido PitchAPI directamente por match_id
    # --------------------------------------------------------

    pitch_match = pitchapi_partidos.get(match_id)

    if pitch_match is None:

        partido_no_encontrado += 1
        continue

    fecha = pitch_match.get("fecha")
    home_name = pitch_match.get("home_name")
    away_name = pitch_match.get("away_name")

    if not fecha or not home_name or not away_name:

        partido_no_encontrado += 1
        continue

    # --------------------------------------------------------
    # Construir clave exacta del partido SofaScore
    # --------------------------------------------------------

    clave_sofa = (
        fecha,
        normalizar_equipo(home_name),
        normalizar_equipo(away_name),
    )

    partido_sofa = sofascore_partidos.get(clave_sofa)

    # --------------------------------------------------------
    # Si no aparece, intentamos mostrar diagnóstico
    # --------------------------------------------------------

    if partido_sofa is None:

        partido_no_encontrado += 1

        if len(ejemplos_cruce) < 5:

            ejemplos_cruce.append({
                "match_id": match_id,
                "fecha": fecha,
                "pitch_home": home_name,
                "pitch_away": away_name,
                "clave_sofa_buscada": clave_sofa,
            })

        continue

    # --------------------------------------------------------
    # Buscar jugador por partido + nombre
    # --------------------------------------------------------

    clave_jugador = (
        clave_sofa,
        normalizar(player_name),
    )

    registro_sofa = sofascore_jugadores.get(clave_jugador)

    if registro_sofa is None:

        jugador_no_encontrado += 1

        continue

    # --------------------------------------------------------
    # Posición encontrada
    # --------------------------------------------------------

    posicion = registro_sofa.get("position")

    fila["posicion_sofascore"] = posicion or ""
    fila["sofascore_player_id"] = (
        registro_sofa.get("player_id", "")
    )

    if posicion in conteo_posiciones:

        conteo_posiciones[posicion] += 1
        posicion_encontrada += 1


# ============================================================
# RESULTADO
# ============================================================

print("\n" + "=" * 100)
print("RESULTADO DEL CRUCE")
print("=" * 100)

print(f"\nRegistros totales: {len(filas)}")
print(f"Posición encontrada: {posicion_encontrada}")
print(f"Partido no encontrado: {partido_no_encontrado}")
print(f"Jugador no encontrado: {jugador_no_encontrado}")

print("\nPOSICIONES ENCONTRADAS:\n")

print(f"G  ARQ: {conteo_posiciones['G']}")
print(f"D  DEF: {conteo_posiciones['D']}")
print(f"M  VOL: {conteo_posiciones['M']}")
print(f"F  DEL: {conteo_posiciones['F']}")


# ============================================================
# DIAGNÓSTICO SI TODAVÍA HAY PARTIDOS SIN ENCONTRAR
# ============================================================

if ejemplos_cruce:

    print("\n" + "=" * 100)
    print("EJEMPLOS DE PARTIDOS QUE NO COINCIDIERON")
    print("=" * 100)

    for ejemplo in ejemplos_cruce:

        print()
        print(f"Match ID: {ejemplo['match_id']}")
        print(f"Fecha:    {ejemplo['fecha']}")
        print(f"PitchAPI: {ejemplo['pitch_home']} vs {ejemplo['pitch_away']}")
        print(f"Clave:    {ejemplo['clave_sofa_buscada']}")


# ============================================================
# GUARDAR DATASET
# ============================================================

campos = list(filas[0].keys())

with open(
    DATASET_OUTPUT,
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=campos
    )

    writer.writeheader()
    writer.writerows(filas)


print("\nArchivo generado:")
print(os.path.abspath(DATASET_OUTPUT))

print("\n" + "=" * 100)
print("FIN")
print("=" * 100)