import json
import glob
import os
import re
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime, timezone

import pandas as pd


# ============================================================
# CARPETAS
# ============================================================

SOFASCORE_DIR = "datos/partidos"
PITCHAPI_MATCHES_DIR = "datos/pitchapi/matches"
PITCHAPI_ADVANCED_DIR = "datos/pitchapi"

SALIDA = "datos/cruce_sofascore_pitchapi.csv"


# ============================================================
# NORMALIZACIÓN DE TEXTO
# ============================================================

def normalizar(texto):

    if texto is None:
        return ""

    texto = str(texto).lower().strip()

    # Sacar acentos
    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        c
        for c in texto
        if unicodedata.category(c) != "Mn"
    )

    # Reemplazos habituales
    texto = texto.replace("&", " y ")

    # Sacar palabras que suelen variar entre fuentes
    reemplazos = [
        "club atletico",
        "club",
        "atletico",
        "athletic",
        "ca ",
        "c.a. ",
        "deportivo ",
        "club deportivo ",
        "club atletico ",
        "gimnasia y esgrima ",
        "newell's old boys",
        "newells old boys",
    ]

    for palabra in reemplazos:
        texto = texto.replace(palabra, "")

    # Solo letras y números
    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    ).strip()

    return texto


# ============================================================
# SIMILITUD
# ============================================================

def similitud(a, b):

    a = normalizar(a)
    b = normalizar(b)

    if not a or not b:
        return 0

    if a == b:
        return 1.0

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


# ============================================================
# FECHA DE SOFASCORE
# ============================================================

def fecha_sofascore(event):

    timestamp = event.get("startTimestamp")

    if timestamp is None:
        return None

    try:

        return datetime.fromtimestamp(
            int(timestamp),
            tz=timezone.utc
        ).strftime("%Y-%m-%d")

    except Exception:

        return None


# ============================================================
# CARGAR PARTIDOS PITCHAPI
# ============================================================

print()
print("=" * 100)
print("CARGANDO PARTIDOS PITCHAPI")
print("=" * 100)
print()


pitch_matches = []

archivos_matches = glob.glob(
    os.path.join(
        PITCHAPI_MATCHES_DIR,
        "*.json"
    )
)


for archivo in archivos_matches:

    try:

        with open(
            archivo,
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        partido = data.get("data", {})

        if not partido:
            continue

        pitch_matches.append({
            "pitch_match_id": partido.get("id"),
            "date": partido.get("date"),
            "home_team": partido.get("home_team", {}).get("name"),
            "away_team": partido.get("away_team", {}).get("name"),
        })

    except Exception:
        continue


print(
    f"Partidos PitchAPI cargados: {len(pitch_matches)}"
)


# ============================================================
# FUNCIÓN PARA ENCONTRAR PARTIDO PITCHAPI
# ============================================================

def encontrar_partido_pitchapi(
    fecha,
    local,
    visitante
):

    candidatos = [
        p
        for p in pitch_matches
        if p["date"] == fecha
    ]

    if not candidatos:
        return None, 0

    mejor = None
    mejor_score = 0

    for partido in candidatos:

        local_score = similitud(
            local,
            partido["home_team"]
        )

        visitante_score = similitud(
            visitante,
            partido["away_team"]
        )

        score_directo = (
            local_score + visitante_score
        ) / 2

        # También probamos invertirlos por seguridad
        local_invertido = similitud(
            local,
            partido["away_team"]
        )

        visitante_invertido = similitud(
            visitante,
            partido["home_team"]
        )

        score_invertido = (
            local_invertido
            + visitante_invertido
        ) / 2

        score = max(
            score_directo,
            score_invertido
        )

        if score > mejor_score:

            mejor_score = score
            mejor = partido

    # No aceptamos coincidencias débiles
    if mejor_score < 0.70:
        return None, mejor_score

    return mejor, mejor_score


# ============================================================
# CARGAR PARTIDOS SOFASCORE
# ============================================================

print()
print("=" * 100)
print("CRUZANDO PARTIDOS")
print("=" * 100)
print()


cruces_partidos = []

archivos_sofascore = glob.glob(
    os.path.join(
        SOFASCORE_DIR,
        "*.json"
    )
)


for archivo in archivos_sofascore:

    try:

        with open(
            archivo,
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        event = data["event"]["event"]

        sofascore_id = str(
            event.get("id")
        )

        fecha = fecha_sofascore(
            event
        )

        local = event.get(
            "homeTeam",
            {}
        ).get(
            "name"
        )

        visitante = event.get(
            "awayTeam",
            {}
        ).get(
            "name"
        )

        partido_pitch, score = encontrar_partido_pitchapi(
            fecha,
            local,
            visitante
        )

        if partido_pitch is None:

            continue

        cruces_partidos.append({
            "sofascore_match_id": sofascore_id,
            "pitchapi_match_id": partido_pitch["pitch_match_id"],
            "fecha": fecha,
            "sofascore_local": local,
            "sofascore_visitante": visitante,
            "pitchapi_local": partido_pitch["home_team"],
            "pitchapi_visitante": partido_pitch["away_team"],
            "similitud_partido": round(
                score,
                3
            ),
            "archivo_sofascore": archivo,
        })

    except Exception:
        continue


print(
    f"Partidos SofaScore encontrados: "
    f"{len(archivos_sofascore)}"
)

print(
    f"Partidos cruzados: "
    f"{len(cruces_partidos)}"
)


# ============================================================
# CREAR ÍNDICE PITCHAPI AVANZADO
# ============================================================

print()
print("=" * 100)
print("CARGANDO JUGADORES PITCHAPI")
print("=" * 100)
print()


pitch_players = {}


archivos_advanced = glob.glob(
    os.path.join(
        PITCHAPI_ADVANCED_DIR,
        "*_advanced_players.json"
    )
)


for archivo in archivos_advanced:

    try:

        with open(
            archivo,
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        contenido = data.get(
            "data",
            {}
        )

        players = contenido.get(
            "players",
            []
        )

        match_id = contenido.get(
            "match_id"
        )

        if not match_id:
            nombre = os.path.basename(
                archivo
            )

            match_id = nombre.replace(
                "_advanced_players.json",
                ""
            )

        pitch_players[str(match_id)] = players

    except Exception:
        continue


print(
    f"Partidos PitchAPI con advanced: "
    f"{len(pitch_players)}"
)


# ============================================================
# CRUZAR JUGADORES
# ============================================================

print()
print("=" * 100)
print("CRUZANDO JUGADORES")
print("=" * 100)
print()


resultados = []

partidos_con_jugadores = 0
partidos_sin_jugadores = 0

jugadores_cruzados = 0
jugadores_no_cruzados = 0


for cruce in cruces_partidos:

    sofascore_archivo = cruce[
        "archivo_sofascore"
    ]

    pitch_match_id = str(
        cruce["pitchapi_match_id"]
    )

    try:

        with open(
            sofascore_archivo,
            encoding="utf-8"
        ) as f:

            sofa_data = json.load(f)

    except Exception:
        continue


    jugadores_pitch = pitch_players.get(
        pitch_match_id,
        []
    )


    if not jugadores_pitch:

        partidos_sin_jugadores += 1
        continue


    partidos_con_jugadores += 1


    # --------------------------------------------------------
    # Índice PitchAPI por nombre
    # --------------------------------------------------------

    indice_pitch = []

    for p in jugadores_pitch:

        jugador = p.get(
            "player",
            {}
        )

        nombre = jugador.get(
            "name"
        )

        if not nombre:
            continue

        indice_pitch.append({
            "player": p,
            "name": nombre,
            "normalized": normalizar(
                nombre
            ),
            "team_id": p.get(
                "team_id"
            ),
        })


    # --------------------------------------------------------
    # Jugadores SofaScore
    # --------------------------------------------------------

    for lado in [
        "home",
        "away"
    ]:

        equipo_sofa = sofa_data[
            "event"
        ][
            "event"
        ][
            f"{lado}Team"
        ][
            "name"
        ]

        jugadores_sofa = sofa_data[
            "lineups"
        ][
            lado
        ][
            "players"
        ]


        for registro in jugadores_sofa:

            player_info = registro.get(
                "player",
                {}
            )

            sofa_nombre = player_info.get(
                "name"
            )

            sofa_id = player_info.get(
                "id"
            )

            if not sofa_nombre:
                continue


            # ------------------------------------------------
            # Buscar coincidencia exacta
            # ------------------------------------------------

            nombre_normalizado = normalizar(
                sofa_nombre
            )

            exactos = [
                p
                for p in indice_pitch
                if p["normalized"] == nombre_normalizado
            ]


            match_player = None
            match_score = 0
            match_tipo = "NO"


            if len(exactos) == 1:

                match_player = exactos[0]
                match_score = 1.0
                match_tipo = "EXACTO"


            else:

                # --------------------------------------------
                # Buscar mejor coincidencia aproximada
                # --------------------------------------------

                mejor = None
                mejor_score = 0

                for p in indice_pitch:

                    score = similitud(
                        sofa_nombre,
                        p["name"]
                    )

                    if score > mejor_score:

                        mejor_score = score
                        mejor = p


                if (
                    mejor is not None
                    and mejor_score >= 0.85
                ):

                    match_player = mejor
                    match_score = mejor_score
                    match_tipo = "APROXIMADO"


            # ------------------------------------------------
            # Resultado
            # ------------------------------------------------

            if match_player is not None:

                jugadores_cruzados += 1

                pitch = match_player["player"]

                jugador_pitch = pitch.get(
                    "player",
                    {}
                )

                resultados.append({

                    "sofascore_match_id":
                        cruce["sofascore_match_id"],

                    "pitchapi_match_id":
                        pitch_match_id,

                    "fecha":
                        cruce["fecha"],

                    "equipo_sofascore":
                        equipo_sofa,

                    "jugador_sofascore":
                        sofa_nombre,

                    "sofascore_player_id":
                        sofa_id,

                    "jugador_pitchapi":
                        jugador_pitch.get(
                            "name"
                        ),

                    "pitchapi_player_id":
                        jugador_pitch.get(
                            "id"
                        ),

                    "team_id_pitchapi":
                        pitch.get(
                            "team_id"
                        ),

                    "match_position_sofascore":
                        registro.get(
                            "position"
                        ),

                    "minutes_sofascore":
                        registro.get(
                            "statistics",
                            {}
                        ).get(
                            "minutesPlayed"
                        ),

                    "minutes_pitchapi":
                        pitch.get(
                            "minutes_played"
                        ),

                    "match_score":
                        cruce[
                            "similitud_partido"
                        ],

                    "player_score":
                        round(
                            match_score,
                            3
                        ),

                    "tipo_cruce":
                        match_tipo,

                })

            else:

                jugadores_no_cruzados += 1

                resultados.append({

                    "sofascore_match_id":
                        cruce["sofascore_match_id"],

                    "pitchapi_match_id":
                        pitch_match_id,

                    "fecha":
                        cruce["fecha"],

                    "equipo_sofascore":
                        equipo_sofa,

                    "jugador_sofascore":
                        sofa_nombre,

                    "sofascore_player_id":
                        sofa_id,

                    "jugador_pitchapi":
                        None,

                    "pitchapi_player_id":
                        None,

                    "team_id_pitchapi":
                        None,

                    "match_position_sofascore":
                        registro.get(
                            "position"
                        ),

                    "minutes_sofascore":
                        registro.get(
                            "statistics",
                            {}
                        ).get(
                            "minutesPlayed"
                        ),

                    "minutes_pitchapi":
                        None,

                    "match_score":
                        cruce[
                            "similitud_partido"
                        ],

                    "player_score":
                        0,

                    "tipo_cruce":
                        "NO",

                })


# ============================================================
# GUARDAR
# ============================================================

df = pd.DataFrame(
    resultados
)


df.to_csv(
    SALIDA,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# RESUMEN
# ============================================================

print()
print("=" * 100)
print("RESULTADO DEL CRUCE")
print("=" * 100)
print()

print(
    f"Partidos SofaScore:             "
    f"{len(archivos_sofascore)}"
)

print(
    f"Partidos cruzados:               "
    f"{len(cruces_partidos)}"
)

print(
    f"Partidos con jugadores PitchAPI: "
    f"{partidos_con_jugadores}"
)

print(
    f"Partidos sin jugadores PitchAPI:  "
    f"{partidos_sin_jugadores}"
)

print()

print(
    f"Jugadores cruzados:              "
    f"{jugadores_cruzados}"
)

print(
    f"Jugadores sin cruce:             "
    f"{jugadores_no_cruzados}"
)


# ============================================================
# TIPOS DE CRUCE
# ============================================================

if not df.empty:

    print()
    print("TIPOS DE CRUCE:")
    print("-" * 100)

    print(
        df["tipo_cruce"]
        .value_counts(
            dropna=False
        )
    )


# ============================================================
# MOSTRAR ALGUNOS CRUCES
# ============================================================

if not df.empty:

    print()
    print("EJEMPLOS DE CRUCES:")
    print("-" * 100)

    columnas = [
        "fecha",
        "jugador_sofascore",
        "jugador_pitchapi",
        "equipo_sofascore",
        "minutes_sofascore",
        "minutes_pitchapi",
        "tipo_cruce",
        "player_score",
    ]

    print(
        df[
            columnas
        ]
        .head(30)
        .to_string(
            index=False
        )
    )


# ============================================================
# JUGADORES NO CRUZADOS
# ============================================================

no_cruzados = df[
    df["tipo_cruce"] == "NO"
]


if not no_cruzados.empty:

    print()
    print("PRIMEROS JUGADORES SIN CRUCE:")
    print("-" * 100)

    columnas = [
        "fecha",
        "jugador_sofascore",
        "equipo_sofascore",
        "sofascore_match_id",
        "pitchapi_match_id",
    ]

    print(
        no_cruzados[
            columnas
        ]
        .head(30)
        .to_string(
            index=False
        )
    )


print()
print(
    f"Archivo generado: {SALIDA}"
)
print()