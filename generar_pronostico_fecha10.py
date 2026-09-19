import csv
import json
import glob
import os
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher


# ============================================================
# CONFIGURACIÓN
# ============================================================

DATASET = "datos/dataset_winning_pitchapi.csv"
SOFASCORE_DIR = "datos/partidos"

FECHA_OBJETIVO = 10

SALIDA_CANDIDATOS = "datos/candidatos_fecha10_pitchapi.csv"
SALIDA_PRONOSTICO = "datos/pronostico_fecha10_pitchapi.csv"


# ============================================================
# NORMALIZACIÓN DE TEXTO
# ============================================================

def normalizar_texto(texto):

    if texto is None:
        return ""

    texto = str(texto).strip().lower()

    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


# ============================================================
# EQUIVALENCIAS DE EQUIPOS
# ============================================================

ALIAS_EQUIPOS = {

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


def normalizar_equipo(nombre):

    nombre_normalizado = normalizar_texto(nombre)

    return ALIAS_EQUIPOS.get(
        nombre_normalizado,
        nombre_normalizado
    )


# ============================================================
# POSICIONES SOFASCORE
# ============================================================

MAPA_POSICIONES = {
    "G": "ARQ",
    "D": "DEF",
    "M": "VOL",
    "F": "DEL",
}


def extraer_posicion_sofascore(jugador):

    posibles = [

        jugador.get("position"),

        jugador.get("positionCode"),

        jugador.get("positionName"),

    ]

    for valor in posibles:

        if not valor:
            continue

        valor = str(valor).upper().strip()

        if valor in MAPA_POSICIONES:
            return MAPA_POSICIONES[valor]

        if valor in (
            "GK",
            "GOALKEEPER",
        ):
            return "ARQ"

        if "DEF" in valor:
            return "DEF"

        if (
            "MID" in valor
            or "MIDDLE" in valor
        ):
            return "VOL"

        if (
            "ATT" in valor
            or "FORWARD" in valor
        ):
            return "DEL"

    return None


# ============================================================
# CARGAR POSICIONES SOFASCORE
# ============================================================

def cargar_posiciones_sofascore():

    posiciones = {}

    archivos = glob.glob(
        os.path.join(
            SOFASCORE_DIR,
            "*.json"
        )
    )

    print(
        f"Archivos SofaScore encontrados: "
        f"{len(archivos)}"
    )

    for archivo in archivos:

        try:

            with open(
                archivo,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

        except Exception:
            continue

        lineups = data.get("lineups")

        if not lineups:
            continue

        event = data.get(
            "event",
            {}
        ).get(
            "event",
            {}
        )

        for lado in (
            "home",
            "away"
        ):

            jugadores = (
                lineups
                .get(lado, {})
                .get("players", [])
            )

            equipo_evento = event.get(
                "homeTeam"
                if lado == "home"
                else "awayTeam",
                {}
            ).get("name")

            for item in jugadores:

                jugador = item.get(
                    "player",
                    {}
                )

                nombre = (
                    jugador.get("name")
                    or jugador.get("shortName")
                    or ""
                )

                if not nombre:
                    continue

                posicion = (
                    extraer_posicion_sofascore(
                        item
                    )
                )

                if not posicion:

                    posicion = (
                        extraer_posicion_sofascore(
                            jugador
                        )
                    )

                if not posicion:
                    continue

                equipo = (
                    item.get(
                        "team",
                        {}
                    ).get("name")
                    or equipo_evento
                )

                if not equipo:
                    continue

                clave = (
                    normalizar_texto(nombre),
                    normalizar_equipo(equipo)
                )

                posiciones[clave] = posicion

    print(
        f"Posiciones SofaScore recopiladas: "
        f"{len(posiciones)}"
    )

    return posiciones


# ============================================================
# ENCONTRAR POSICIÓN DE JUGADOR
# ============================================================

def encontrar_posicion(
    nombre,
    equipo,
    posiciones
):

    nombre_norm = normalizar_texto(
        nombre
    )

    equipo_norm = normalizar_equipo(
        equipo
    )

    # Coincidencia exacta

    clave = (
        nombre_norm,
        equipo_norm
    )

    if clave in posiciones:

        return (
            posiciones[clave],
            "exacta"
        )

    # Coincidencia aproximada

    mejores = []

    for (
        nombre_sofa,
        equipo_sofa
    ), posicion in posiciones.items():

        if equipo_sofa != equipo_norm:
            continue

        ratio = SequenceMatcher(
            None,
            nombre_norm,
            nombre_sofa
        ).ratio()

        if ratio >= 0.88:

            mejores.append(
                (
                    ratio,
                    posicion,
                    nombre_sofa
                )
            )

    if mejores:

        mejores.sort(
            reverse=True
        )

        ratio, posicion, nombre_encontrado = (
            mejores[0]
        )

        return (
            posicion,
            f"fuzzy:{ratio:.3f}"
        )

    return None, None


# ============================================================
# CARGAR DATASET PITCHAPI
# ============================================================

def cargar_dataset():

    if not os.path.exists(DATASET):

        raise FileNotFoundError(
            f"No existe el archivo:\n"
            f"{DATASET}"
        )

    with open(
        DATASET,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        rows = list(
            csv.DictReader(f)
        )

    print(
        f"Registros PitchAPI: "
        f"{len(rows)}"
    )

    return rows


# ============================================================
# DETECTAR COLUMNA WINNING
# ============================================================

def detectar_columna_puntaje(rows):

    if not rows:
        return None

    columnas = list(
        rows[0].keys()
    )

    # winning_total es nuestra columna real
    candidatos = [

        "winning_total",

        "winning_points",

        "winning_score",

        "puntaje_winning",

        "puntos_winning",

        "score_winning",

        "winning",

        "total_winning",

        "puntos",

        "puntaje",

    ]

    for candidato in candidatos:

        candidato_norm = normalizar_texto(
            candidato
        )

        for columna in columnas:

            if (
                normalizar_texto(
                    columna
                )
                == candidato_norm
            ):

                return columna

    # Búsqueda alternativa

    for columna in columnas:

        n = normalizar_texto(
            columna
        )

        if (
            "winning" in n
            and (
                "point" in n
                or "punto" in n
                or "score" in n
                or "puntaje" in n
                or "total" in n
            )
        ):

            return columna

    return None


# ============================================================
# OBTENER PARTIDOS FECHA 10
# ============================================================

def cargar_partidos_fecha10():

    partidos = []

    archivos = glob.glob(
        os.path.join(
            SOFASCORE_DIR,
            "*.json"
        )
    )

    for archivo in archivos:

        try:

            with open(
                archivo,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

        except Exception:
            continue

        event = (
            data
            .get("event", {})
            .get("event", {})
        )

        if not event:
            continue

        round_info = event.get(
            "roundInfo",
            {}
        )

        round_value = (
            round_info.get("round")
            or event.get("round")
        )

        try:

            round_value = int(
                round_value
            )

        except Exception:

            continue

        if round_value != FECHA_OBJETIVO:
            continue

        home = (
            event
            .get("homeTeam", {})
            .get("name")
        )

        away = (
            event
            .get("awayTeam", {})
            .get("name")
        )

        if not home or not away:
            continue

        event_id = event.get("id")

        home_norm = normalizar_equipo(
            home
        )

        away_norm = normalizar_equipo(
            away
        )

        # ----------------------------------------------------
        # CLAVE DEL PARTIDO
        # ----------------------------------------------------
        #
        # Evita:
        #
        # Aldosivi vs Atlético Tucumán
        #
        # Atlético Tucumán vs Aldosivi
        #
        # como duplicados.
        # ----------------------------------------------------

        clave = tuple(
            sorted([
                home_norm,
                away_norm
            ])
        )

        partidos.append({

            "event_id": event_id,

            "home": home,

            "away": away,

            "home_norm": home_norm,

            "away_norm": away_norm,

            "clave": clave,

        })

    # --------------------------------------------------------
    # ELIMINAR DUPLICADOS
    # --------------------------------------------------------

    unicos = {}

    for partido in partidos:

        clave = partido["clave"]

        if clave not in unicos:

            unicos[clave] = partido

    partidos = list(
        unicos.values()
    )

    print()
    print(
        "=== PARTIDOS FECHA 10 ==="
    )

    for partido in sorted(
        partidos,
        key=lambda x: (
            x["home_norm"],
            x["away_norm"]
        )
    ):

        print(
            f"{partido['home']} vs "
            f"{partido['away']}"
        )

    print(
        f"Total partidos Fecha 10: "
        f"{len(partidos)}"
    )

    return partidos


# ============================================================
# OBTENER JUGADORES FECHA 10
# ============================================================

def obtener_jugadores_fecha10(
    partidos
):

    equipos = set()

    for partido in partidos:

        equipos.add(
            partido["home_norm"]
        )

        equipos.add(
            partido["away_norm"]
        )

    candidatos = []

    archivos = glob.glob(
        os.path.join(
            SOFASCORE_DIR,
            "*.json"
        )
    )

    for archivo in archivos:

        try:

            with open(
                archivo,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

        except Exception:
            continue

        event = (
            data
            .get("event", {})
            .get("event", {})
        )

        if not event:
            continue

        round_value = (
            event
            .get("roundInfo", {})
            .get("round")
            or event.get("round")
        )

        try:

            round_value = int(
                round_value
            )

        except Exception:

            continue

        if round_value != FECHA_OBJETIVO:
            continue

        lineups = data.get(
            "lineups",
            {}
        )

        for lado in (
            "home",
            "away"
        ):

            team = (
                event
                .get(
                    "homeTeam"
                    if lado == "home"
                    else "awayTeam",
                    {}
                )
                .get("name")
            )

            team_norm = normalizar_equipo(
                team
            )

            if team_norm not in equipos:
                continue

            jugadores = (
                lineups
                .get(lado, {})
                .get("players", [])
            )

            for item in jugadores:

                jugador = item.get(
                    "player",
                    {}
                )

                nombre = (
                    jugador.get("name")
                    or jugador.get("shortName")
                    or ""
                )

                if not nombre:
                    continue

                posicion = (
                    extraer_posicion_sofascore(
                        item
                    )
                )

                if not posicion:

                    posicion = (
                        extraer_posicion_sofascore(
                            jugador
                        )
                    )

                if not posicion:
                    continue

                candidatos.append({

                    "player_id":
                        jugador.get("id"),

                    "player_name":
                        nombre,

                    "team_name":
                        team,

                    "team_norm":
                        team_norm,

                    "position":
                        posicion,

                    "event_id":
                        event.get("id"),

                })

    # --------------------------------------------------------
    # DEDUPLICAR
    # --------------------------------------------------------

    unicos = {}

    for jugador in candidatos:

        clave = (

            normalizar_texto(
                jugador["player_name"]
            ),

            jugador["team_norm"],

            jugador["position"],

        )

        unicos[clave] = jugador

    return list(
        unicos.values()
    )


# ============================================================
# CONSTRUIR HISTORIAL
# ============================================================

def construir_historial(
    rows,
    posiciones_sofascore
):

    columna_puntaje = (
        detectar_columna_puntaje(
            rows
        )
    )

    if not columna_puntaje:

        print()
        print(
            "NO SE ENCONTRÓ LA COLUMNA "
            "DE PUNTAJE WINNING."
        )

        print()
        print(
            "Columnas disponibles:"
        )

        for columna in rows[0].keys():

            print(
                " -",
                columna
            )

        raise RuntimeError(
            "No se pudo detectar la "
            "columna de puntaje Winning."
        )

    print()
    print(
        f"Columna utilizada como puntaje: "
        f"{columna_puntaje}"
    )

    historial = defaultdict(list)

    for row in rows:

        nombre = (
            row.get("player_name")
            or row.get("player")
            or row.get("nombre")
            or ""
        )

        equipo = (
            row.get("team_name")
            or row.get("team")
            or row.get("equipo")
            or ""
        )

        if not nombre or not equipo:
            continue

        posicion, metodo = (
            encontrar_posicion(
                nombre,
                equipo,
                posiciones_sofascore
            )
        )

        if not posicion:
            continue

        valor = row.get(
            columna_puntaje
        )

        try:

            valor = float(
                str(valor).replace(
                    ",",
                    "."
                )
            )

        except Exception:

            continue

        clave = (

            normalizar_texto(
                nombre
            ),

            normalizar_equipo(
                equipo
            ),

            posicion,

        )

        historial[clave].append(
            valor
        )

    return (
        historial,
        columna_puntaje
    )


# ============================================================
# ESTADÍSTICAS DEL HISTORIAL
# ============================================================

def estadistica_jugador(
    valores
):

    if not valores:
        return None

    cantidad = len(
        valores
    )

    promedio = (
        sum(valores)
        / cantidad
    )

    # --------------------------------------------------------
    # PROMEDIO PONDERADO
    # --------------------------------------------------------
    #
    # Se da más peso a los partidos recientes.
    # --------------------------------------------------------

    ponderado = 0
    peso_total = 0

    for i, valor in enumerate(
        reversed(valores),
        start=1
    ):

        peso = min(
            i,
            5
        )

        ponderado += (
            valor * peso
        )

        peso_total += peso

    promedio_ponderado = (
        ponderado / peso_total
        if peso_total
        else promedio
    )

    return {

        "partidos_historial":
            cantidad,

        "promedio":
            promedio,

        "promedio_ponderado":
            promedio_ponderado,

    }


# ============================================================
# GENERAR CANDIDATOS
# ============================================================

def generar_candidatos(
    jugadores_fecha10,
    historial
):

    salida = []

    for jugador in jugadores_fecha10:

        nombre = (
            jugador["player_name"]
        )

        equipo = (
            jugador["team_name"]
        )

        posicion = (
            jugador["position"]
        )

        clave = (

            normalizar_texto(
                nombre
            ),

            normalizar_equipo(
                equipo
            ),

            posicion,

        )

        valores = historial.get(
            clave,
            []
        )

        stats = (
            estadistica_jugador(
                valores
            )
        )

        if not stats:
            continue

        salida.append({

            "player_name":
                nombre,

            "team_name":
                equipo,

            "position":
                posicion,

            "partidos_historial":
                stats[
                    "partidos_historial"
                ],

            "promedio_winning":
                round(
                    stats["promedio"],
                    3
                ),

            "promedio_ponderado":
                round(
                    stats[
                        "promedio_ponderado"
                    ],
                    3
                ),

        })

    return salida


# ============================================================
# GUARDAR CSV
# ============================================================

def guardar_csv(
    archivo,
    rows
):

    if not rows:

        print(
            f"No hay datos para guardar "
            f"en {archivo}"
        )

        return

    directorio = os.path.dirname(
        archivo
    )

    if directorio:

        os.makedirs(
            directorio,
            exist_ok=True
        )

    with open(
        archivo,
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=rows[0].keys()
        )

        writer.writeheader()

        writer.writerows(
            rows
        )

    print(
        f"Guardado: {archivo}"
    )


# ============================================================
# ARMAR 11
# ============================================================

def armar_pronostico(
    candidatos
):

    posiciones = {

        "ARQ": 1,

        "DEF": 4,

        "VOL": 3,

        "DEL": 3,

    }

    seleccionados = []

    usados = set()

    clubes = defaultdict(int)

    candidatos = sorted(

        candidatos,

        key=lambda x: (

            x[
                "promedio_ponderado"
            ],

            x[
                "promedio_winning"
            ],

            x[
                "partidos_historial"
            ],

        ),

        reverse=True

    )

    for posicion, cantidad in (
        posiciones.items()
    ):

        disponibles = [

            x

            for x in candidatos

            if (
                x["position"]
                == posicion
            )

            and (
                x["player_name"]
                not in usados
            )

        ]

        cantidad_actual = 0

        for jugador in disponibles:

            if cantidad_actual >= cantidad:
                break

            equipo = jugador[
                "team_name"
            ]

            equipo_norm = (
                normalizar_equipo(
                    equipo
                )
            )

            if clubes[
                equipo_norm
            ] >= 3:

                continue

            seleccionados.append(
                jugador
            )

            usados.add(
                jugador[
                    "player_name"
                ]
            )

            clubes[
                equipo_norm
            ] += 1

            cantidad_actual += 1

    return seleccionados


# ============================================================
# FLEX
# ============================================================

def obtener_flex(
    candidatos,
    seleccionados
):

    usados = {

        x["player_name"]

        for x in seleccionados

    }

    resultado = {}

    for posicion in (
        "DEF",
        "VOL",
        "DEL"
    ):

        disponibles = [

            x

            for x in candidatos

            if (
                x["position"]
                == posicion
            )

            and (
                x["player_name"]
                not in usados
            )

        ]

        disponibles.sort(

            key=lambda x: (

                x[
                    "promedio_ponderado"
                ],

                x[
                    "promedio_winning"
                ],

                x[
                    "partidos_historial"
                ],

            ),

            reverse=True

        )

        resultado[
            posicion
        ] = disponibles[:5]

    return resultado


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 70
    )

    print(
        "WINNING AI - "
        "PRONÓSTICO FECHA 10"
    )

    print(
        "PitchAPI + posiciones SofaScore"
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # 1. POSICIONES SOFASCORE
    # --------------------------------------------------------

    posiciones_sofascore = (
        cargar_posiciones_sofascore()
    )

    # --------------------------------------------------------
    # 2. DATASET PITCHAPI
    # --------------------------------------------------------

    rows = cargar_dataset()

    # --------------------------------------------------------
    # 3. PARTIDOS FECHA 10
    # --------------------------------------------------------

    partidos = (
        cargar_partidos_fecha10()
    )

    if not partidos:

        raise RuntimeError(
            "No se encontraron partidos "
            "de Fecha 10."
        )

    # --------------------------------------------------------
    # 4. HISTORIAL
    # --------------------------------------------------------

    (
        historial,
        columna_puntaje
    ) = construir_historial(

        rows,

        posiciones_sofascore

    )

    # --------------------------------------------------------
    # 5. JUGADORES FECHA 10
    # --------------------------------------------------------

    jugadores_fecha10 = (
        obtener_jugadores_fecha10(
            partidos
        )
    )

    print()

    print(
        "Jugadores encontrados para "
        f"Fecha 10: "
        f"{len(jugadores_fecha10)}"
    )

    # --------------------------------------------------------
    # 6. CANDIDATOS
    # --------------------------------------------------------

    candidatos = (
        generar_candidatos(

            jugadores_fecha10,

            historial

        )
    )

    print()

    print(
        "Candidatos con historial "
        "PitchAPI + posición SofaScore: "
        f"{len(candidatos)}"
    )

    # --------------------------------------------------------
    # 7. GUARDAR CANDIDATOS
    # --------------------------------------------------------

    guardar_csv(

        SALIDA_CANDIDATOS,

        sorted(

            candidatos,

            key=lambda x: (

                x["position"],

                -x[
                    "promedio_ponderado"
                ]

            )

        )

    )

    # --------------------------------------------------------
    # 8. ARMAR 11
    # --------------------------------------------------------

    seleccionados = (
        armar_pronostico(
            candidatos
        )
    )

    # --------------------------------------------------------
    # 9. FLEX
    # --------------------------------------------------------

    flex = (
        obtener_flex(

            candidatos,

            seleccionados

        )
    )

    # --------------------------------------------------------
    # 10. MOSTRAR PRONÓSTICO
    # --------------------------------------------------------

    print()

    print(
        "=" * 70
    )

    print(
        "PRONÓSTICO FECHA 10"
    )

    print(
        "=" * 70
    )

    for posicion in (
        "ARQ",
        "DEF",
        "VOL",
        "DEL"
    ):

        print()

        print(
            f"--- {posicion} ---"
        )

        jugadores = [

            x

            for x in seleccionados

            if (
                x["position"]
                == posicion
            )

        ]

        for jugador in jugadores:

            print(

                f"{jugador['player_name']} | "

                f"{jugador['team_name']} | "

                f"Promedio: "
                f"{jugador['promedio_winning']:.3f} | "

                f"Ponderado: "
                f"{jugador['promedio_ponderado']:.3f} | "

                f"Historial: "
                f"{jugador['partidos_historial']}"

            )

    # --------------------------------------------------------
    # 11. FLEX
    # --------------------------------------------------------

    print()

    print(
        "=" * 70
    )

    print(
        "FLEX"
    )

    print(
        "=" * 70
    )

    for posicion in (
        "DEF",
        "VOL",
        "DEL"
    ):

        print()

        print(
            f"FLEX {posicion}"
        )

        for jugador in flex[
            posicion
        ][:3]:

            print(

                f"{jugador['player_name']} | "

                f"{jugador['team_name']} | "

                f"Ponderado: "
                f"{jugador['promedio_ponderado']:.3f} | "

                f"Historial: "
                f"{jugador['partidos_historial']}"

            )

    # --------------------------------------------------------
    # 12. GUARDAR PRONÓSTICO
    # --------------------------------------------------------

    guardar_csv(

        SALIDA_PRONOSTICO,

        seleccionados

    )

    print()

    print(
        "=" * 70
    )

    print(
        "Proceso terminado"
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":

    main()