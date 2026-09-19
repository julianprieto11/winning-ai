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
# 1. CARGAR SOFASCORE
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


# ============================================================
# 2. PRIMERA PASADA:
#    OBTENER TODOS LOS POSITION_ID Y SUS POSICIONES
# ============================================================

datos_position_id = defaultdict(list)

archivos = glob.glob(
    os.path.join(CARPETA_LINEUPS, "*_lineups.json")
)

for archivo in archivos:

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            contenido = json.load(f)
    except Exception:
        continue

    datos = contenido.get("data")

    if not isinstance(datos, dict):
        continue

    for lado in ["home", "away"]:

        equipo = datos.get(lado)

        if not isinstance(equipo, dict):
            continue

        jugadores = equipo.get("starters")

        if not isinstance(jugadores, list):
            continue

        for jugador in jugadores:

            nombre = jugador.get("name")
            position_id = jugador.get("position_id")

            if not nombre or position_id is None:
                continue

            posiciones = sofascore_por_nombre.get(
                normalizar(nombre)
            )

            if not posiciones:
                continue

            if len(posiciones) != 1:
                continue

            posicion = next(iter(posiciones))

            x = jugador.get("pitch_x")
            y = jugador.get("pitch_y")

            if x is None or y is None:
                continue

            try:
                x = float(x)
                y = float(y)
            except (ValueError, TypeError):
                continue

            datos_position_id[position_id].append(
                {
                    "posicion": posicion,
                    "x": x,
                    "y": y,
                    "nombre": nombre,
                }
            )


# ============================================================
# 3. IDENTIFICAR POSITION_ID AMBIGUOS
# ============================================================

ambiguos = {}

for position_id, registros in datos_position_id.items():

    posiciones = Counter(
        r["posicion"]
        for r in registros
    )

    if len(posiciones) > 1:
        ambiguos[position_id] = registros


# ============================================================
# 4. RESUMEN
# ============================================================

print()
print("=" * 110)
print("POSITION_ID AMBIGUOS")
print("=" * 110)

print(
    f"POSITION_ID totales: {len(datos_position_id)}"
)

print(
    f"POSITION_ID ambiguos: {len(ambiguos)}"
)

print()


# ============================================================
# 5. ANALIZAR CADA POSITION_ID
# ============================================================

for position_id, registros in sorted(
    ambiguos.items(),
    key=lambda x: len(x[1]),
    reverse=True
):

    conteo = Counter(
        r["posicion"]
        for r in registros
    )

    total = len(registros)

    print()
    print("=" * 110)
    print(
        f"POSITION_ID {position_id} "
        f"| TOTAL: {total}"
    )
    print("=" * 110)

    print("Distribución:")

    for posicion, cantidad in conteo.most_common():

        porcentaje = cantidad / total * 100

        print(
            f"  {posicion:<5} "
            f"{cantidad:>5} "
            f"({porcentaje:>6.2f}%)"
        )


    # --------------------------------------------------------
    # Coordenadas promedio por posición
    # --------------------------------------------------------

    print()
    print(
        f"{'POSICIÓN':<10}"
        f"{'N':>8}"
        f"{'X PROM':>12}"
        f"{'Y PROM':>12}"
        f"{'Y MIN':>12}"
        f"{'Y MAX':>12}"
    )

    print("-" * 70)

    for posicion in ["ARQ", "DEF", "VOL", "DEL"]:

        lista = [
            r
            for r in registros
            if r["posicion"] == posicion
        ]

        if not lista:
            continue

        xs = [r["x"] for r in lista]
        ys = [r["y"] for r in lista]

        print(
            f"{posicion:<10}"
            f"{len(lista):>8}"
            f"{sum(xs)/len(xs):>12.3f}"
            f"{sum(ys)/len(ys):>12.3f}"
            f"{min(ys):>12.3f}"
            f"{max(ys):>12.3f}"
        )


    # --------------------------------------------------------
    # Distribución por zonas verticales
    # --------------------------------------------------------

    print()
    print("DISTRIBUCIÓN POR ZONA Y")

    zonas = {
        "0.00-0.20": lambda y: 0.00 <= y < 0.20,
        "0.20-0.40": lambda y: 0.20 <= y < 0.40,
        "0.40-0.60": lambda y: 0.40 <= y < 0.60,
        "0.60-0.80": lambda y: 0.60 <= y < 0.80,
        "0.80-1.00": lambda y: 0.80 <= y <= 1.00,
    }

    print(
        f"{'ZONA Y':<12}"
        f"{'ARQ':>8}"
        f"{'DEF':>8}"
        f"{'VOL':>8}"
        f"{'DEL':>8}"
        f"{'TOTAL':>8}"
    )

    print("-" * 60)

    for nombre_zona, funcion in zonas.items():

        conteo_zona = Counter()

        for registro in registros:

            if funcion(registro["y"]):
                conteo_zona[registro["posicion"]] += 1

        total_zona = sum(conteo_zona.values())

        if total_zona == 0:
            continue

        print(
            f"{nombre_zona:<12}"
            f"{conteo_zona.get('ARQ', 0):>8}"
            f"{conteo_zona.get('DEF', 0):>8}"
            f"{conteo_zona.get('VOL', 0):>8}"
            f"{conteo_zona.get('DEL', 0):>8}"
            f"{total_zona:>8}"
        )


print()
print("=" * 110)
print("FIN DEL ANÁLISIS")
print("=" * 110)