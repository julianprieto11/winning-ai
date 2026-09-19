import json
import glob
import os
from collections import defaultdict, Counter


CARPETA_PARTIDOS = "datos/partidos"
CARPETA_LINEUPS = "datos/pitchapi/lineups"


def normalizar(texto):
    if texto is None:
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
    }

    for viejo, nuevo in reemplazos.items():
        texto = texto.replace(viejo, nuevo)

    return texto


def posicion_sofascore(player):
    posicion = player.get("position")

    if not posicion:
        return None

    mapa = {
        "G": "ARQ",
        "D": "DEF",
        "M": "VOL",
        "F": "DEL",
    }

    return mapa.get(str(posicion).upper())


# ============================================================
# 1. SOFASCORE
# ============================================================

print("Cargando posiciones SofaScore...")

sofascore_por_nombre = defaultdict(set)

for archivo in glob.glob(os.path.join(CARPETA_PARTIDOS, "*.json")):

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except Exception:
        continue

    lineups = datos.get("lineups")

    if not isinstance(lineups, dict):
        continue

    for lado in ["home", "away"]:

        equipo = lineups.get(lado)

        if not isinstance(equipo, dict):
            continue

        jugadores = equipo.get("players", [])

        if not isinstance(jugadores, list):
            continue

        for item in jugadores:

            player = item.get("player", {})

            if not isinstance(player, dict):
                continue

            nombre = player.get("name")
            posicion = posicion_sofascore(player)

            if not nombre or not posicion:
                continue

            sofascore_por_nombre[
                normalizar(nombre)
            ].add(posicion)


print(
    f"Jugadores SofaScore encontrados: "
    f"{len(sofascore_por_nombre)}"
)


# ============================================================
# 2. PITCHAPI
# ============================================================

print("Cargando lineups PitchAPI...")

archivos_pitchapi = glob.glob(
    os.path.join(CARPETA_LINEUPS, "*_lineups.json")
)

print(
    f"Archivos de lineups PitchAPI: "
    f"{len(archivos_pitchapi)}"
)


estadisticas = defaultdict(Counter)
coordenadas = defaultdict(list)

registros = 0
cruces = 0

archivos_con_jugadores = 0
archivos_sin_jugadores = 0


for archivo in archivos_pitchapi:

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            contenido = json.load(f)
    except Exception:
        continue

    # ========================================================
    # IMPORTANTE:
    # Los datos reales están dentro de "data".
    # ========================================================

    datos = contenido.get("data")

    if not isinstance(datos, dict):
        continue

    jugadores_archivo = 0

    for lado in ["home", "away"]:

        equipo = datos.get(lado)

        if not isinstance(equipo, dict):
            continue

        jugadores = equipo.get("starters")

        if not isinstance(jugadores, list):
            continue

        for jugador in jugadores:

            if not isinstance(jugador, dict):
                continue

            nombre = jugador.get("name")
            position_id = jugador.get("position_id")

            if not nombre:
                continue

            if position_id is None:
                continue

            registros += 1
            jugadores_archivo += 1

            clave = normalizar(nombre)

            posiciones = sofascore_por_nombre.get(clave)

            if not posiciones:
                continue

            if len(posiciones) != 1:
                continue

            posicion = next(iter(posiciones))

            cruces += 1

            estadisticas[position_id][posicion] += 1

            x = jugador.get("pitch_x")
            y = jugador.get("pitch_y")

            if x is not None and y is not None:

                try:
                    coordenadas[position_id].append(
                        (float(x), float(y))
                    )
                except (ValueError, TypeError):
                    pass

    if jugadores_archivo > 0:
        archivos_con_jugadores += 1
    else:
        archivos_sin_jugadores += 1


# ============================================================
# 3. RESUMEN
# ============================================================

print()
print("=" * 100)
print("RESUMEN")
print("=" * 100)

print(f"Archivos PitchAPI: {len(archivos_pitchapi)}")
print(f"Archivos con starters: {archivos_con_jugadores}")
print(f"Archivos sin starters: {archivos_sin_jugadores}")
print(f"Registros PitchAPI analizados: {registros}")
print(f"Registros cruzados con SofaScore: {cruces}")
print(f"POSITION_ID diferentes: {len(estadisticas)}")


# ============================================================
# 4. POSITION_ID
# ============================================================

print()
print("=" * 100)
print("ANÁLISIS POSITION_ID PITCHAPI")
print("=" * 100)

print(
    f"{'POSITION_ID':<14}"
    f"{'TOTAL':>8}"
    f"{'ARQ':>8}"
    f"{'DEF':>8}"
    f"{'VOL':>8}"
    f"{'DEL':>8}"
    f"{'DOMINANTE':>14}"
    f"{'% DOM':>10}"
)

print("=" * 100)


ordenados = sorted(
    estadisticas.items(),
    key=lambda x: sum(x[1].values()),
    reverse=True
)


for position_id, conteo in ordenados:

    total = sum(conteo.values())

    arq = conteo.get("ARQ", 0)
    deff = conteo.get("DEF", 0)
    vol = conteo.get("VOL", 0)
    del_ = conteo.get("DEL", 0)

    dominante, cantidad = conteo.most_common(1)[0]

    porcentaje = cantidad / total * 100

    print(
        f"{str(position_id):<14}"
        f"{total:>8}"
        f"{arq:>8}"
        f"{deff:>8}"
        f"{vol:>8}"
        f"{del_:>8}"
        f"{dominante:>14}"
        f"{porcentaje:>9.2f}%"
    )


# ============================================================
# 5. COORDENADAS
# ============================================================

print()
print("=" * 100)
print("COORDENADAS PROMEDIO POR POSITION_ID")
print("=" * 100)

print(
    f"{'POSITION_ID':<14}"
    f"{'REGISTROS':>12}"
    f"{'X PROM':>12}"
    f"{'Y PROM':>12}"
)

orden_coordenadas = sorted(
    coordenadas.items(),
    key=lambda x: len(x[1]),
    reverse=True
)


for position_id, lista in orden_coordenadas:

    if not lista:
        continue

    promedio_x = sum(x for x, y in lista) / len(lista)
    promedio_y = sum(y for x, y in lista) / len(lista)

    print(
        f"{str(position_id):<14}"
        f"{len(lista):>12}"
        f"{promedio_x:>12.3f}"
        f"{promedio_y:>12.3f}"
    )


print()
print("=" * 100)
print("FIN DEL ANÁLISIS")
print("=" * 100)