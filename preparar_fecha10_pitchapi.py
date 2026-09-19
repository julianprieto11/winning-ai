import json
import glob
import os
import re
import unicodedata
import pandas as pd


SOFASCORE_DIR = "datos/partidos"
PITCHAPI_MATCHES_DIR = "datos/pitchapi/matches"
PITCHAPI_PLAYERS_DIR = "datos/pitchapi"

SALIDA = "datos/candidatos_fecha10_pitchapi.csv"


# ============================================================
# NORMALIZAR NOMBRES
# ============================================================

def normalizar(texto):
    if texto is None:
        return ""

    texto = str(texto).lower().strip()

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


# ============================================================
# FECHA 10 - SOFASCORE
# ============================================================

ARCHIVOS_FECHA10 = [
    "16667329",
    "16667338",
    "16667328",
    "16667336",
    "16667325",
    "16667327",
    "16667333",
    "16667340",
    "16667330",
    "16667332",
    "16667326",
    "16671623",
    "16667335",
    "16667331",
    "16667337",
]


# ============================================================
# MAPEO SOFASCORE -> PITCHAPI
# ============================================================

MAPEO_PARTIDOS = {
    "16667338": "m_1ABSM7",
    "16667328": "m_1rGQaB",
    "16667336": "m_11PYwu",
    "16667325": "m_17fjdr",
    "16667327": "m_0Z63wJ",
    "16667333": "m_0BTFn7",
    "16667340": "m_0jdOYm",
    "16667330": "m_2EhjDn",
    "16667332": "m_0sbdux",
    "16667326": "m_0MCwqI",
    "16671623": "m_0el541",
    "16667335": "m_0bU15M",
    "16667331": "m_0MXtuT",
    "16667337": "m_0Feldm",
}


# ============================================================
# CARGAR CANDIDATOS SOFASCORE
# ============================================================

print()
print("=" * 90)
print("CARGANDO CANDIDATOS FECHA 10")
print("=" * 90)
print()


candidatos = []


for sofascore_id in ARCHIVOS_FECHA10:

    archivo = os.path.join(
        SOFASCORE_DIR,
        f"{sofascore_id}.json"
    )

    if not os.path.exists(archivo):
        print(
            f"AVISO: falta archivo SofaScore {sofascore_id}"
        )
        continue

    with open(
        archivo,
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    event = data["event"]["event"]

    local = event["homeTeam"]["name"]
    visitante = event["awayTeam"]["name"]

    pitchapi_id = MAPEO_PARTIDOS.get(
        sofascore_id
    )

    for lado in ["home", "away"]:

        equipo = (
            local
            if lado == "home"
            else visitante
        )

        registros = data["lineups"][lado]["players"]

        for registro in registros:

            jugador = registro.get(
                "player",
                {}
            )

            nombre = jugador.get("name")

            if not nombre:
                continue

            candidatos.append({
                "sofascore_match_id": sofascore_id,
                "pitchapi_match_id": pitchapi_id,
                "equipo": equipo,
                "jugador": nombre,
                "player_id_sofascore": jugador.get("id"),
                "position_sofascore": registro.get("position"),
                "substitute": registro.get("substitute"),
                "minutes_sofascore": registro.get(
                    "statistics",
                    {}
                ).get("minutesPlayed"),
            })


df_candidatos = pd.DataFrame(candidatos)


print(
    f"Candidatos Fecha 10: {len(df_candidatos)}"
)

print(
    f"Jugadores únicos: "
    f"{df_candidatos['player_id_sofascore'].nunique()}"
)


# ============================================================
# CARGAR TODOS LOS JUGADORES HISTÓRICOS PITCHAPI
# ============================================================

print()
print("=" * 90)
print("CARGANDO HISTORIAL PITCHAPI")
print("=" * 90)
print()


historico = []


archivos = glob.glob(
    os.path.join(
        PITCHAPI_PLAYERS_DIR,
        "*_players.json"
    )
)


for archivo in archivos:

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

        match_id = contenido.get(
            "match_id"
        )

        players = contenido.get(
            "players",
            []
        )

        if not match_id:
            nombre_archivo = os.path.basename(
                archivo
            )

            match_id = nombre_archivo.replace(
                "_players.json",
                ""
            )

        for jugador in players:

            player_info = jugador.get(
                "player",
                {}
            )

            nombre = player_info.get(
                "name"
            )

            if not nombre:
                continue

            historico.append({
                "pitchapi_match_id": match_id,
                "jugador_pitchapi": nombre,
                "jugador_pitchapi_norm": normalizar(nombre),
                "pitchapi_player_id": player_info.get("id"),
                "team_id": jugador.get("team_id"),
                "minutes_pitchapi": jugador.get(
                    "minutes_played"
                ),
            })

    except Exception:
        continue


df_hist = pd.DataFrame(historico)


print(
    f"Registros históricos PitchAPI: "
    f"{len(df_hist)}"
)

print(
    f"Jugadores PitchAPI únicos: "
    f"{df_hist['pitchapi_player_id'].nunique()}"
)


# ============================================================
# NORMALIZAR CANDIDATOS
# ============================================================

df_candidatos[
    "jugador_norm"
] = df_candidatos[
    "jugador"
].apply(normalizar)


# ============================================================
# MAPEAR JUGADORES
# ============================================================

pitch_por_nombre = {}


for _, fila in df_hist.iterrows():

    nombre_norm = fila[
        "jugador_pitchapi_norm"
    ]

    if not nombre_norm:
        continue

    pitch_por_nombre.setdefault(
        nombre_norm,
        []
    ).append(fila)


resultados = []


for _, candidato in df_candidatos.iterrows():

    nombre_norm = candidato[
        "jugador_norm"
    ]

    coincidencias = pitch_por_nombre.get(
        nombre_norm,
        []
    )

    if coincidencias:

        # Todos los registros históricos del jugador
        jugador_pitch = coincidencias[0]

        partidos_historicos = len(
            coincidencias
        )

        minutos_historicos = pd.to_numeric(
            [
                x["minutes_pitchapi"]
                for x in coincidencias
                if x["minutes_pitchapi"] is not None
            ],
            errors="coerce"
        )

        minutos_historicos = (
            minutos_historicos.sum()
            if len(minutos_historicos) > 0
            else 0
        )

        resultados.append({
            **candidato.to_dict(),
            "pitchapi_encontrado": True,
            "pitchapi_player_id": jugador_pitch[
                "pitchapi_player_id"
            ],
            "nombre_pitchapi": jugador_pitch[
                "jugador_pitchapi"
            ],
            "partidos_historicos_pitchapi":
                partidos_historicos,
            "minutos_historicos_pitchapi":
                minutos_historicos,
        })

    else:

        resultados.append({
            **candidato.to_dict(),
            "pitchapi_encontrado": False,
            "pitchapi_player_id": None,
            "nombre_pitchapi": None,
            "partidos_historicos_pitchapi": 0,
            "minutos_historicos_pitchapi": 0,
        })


df_resultado = pd.DataFrame(resultados)


# ============================================================
# GUARDAR
# ============================================================

df_resultado.to_csv(
    SALIDA,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# RESUMEN
# ============================================================

encontrados = df_resultado[
    df_resultado["pitchapi_encontrado"]
]

no_encontrados = df_resultado[
    ~df_resultado["pitchapi_encontrado"]
]


print()
print("=" * 90)
print("RESULTADO")
print("=" * 90)
print()

print(
    f"Candidatos Fecha 10:        "
    f"{len(df_resultado)}"
)

print(
    f"Encontrados en PitchAPI:    "
    f"{len(encontrados)}"
)

print(
    f"No encontrados:             "
    f"{len(no_encontrados)}"
)


print()
print("CANDIDATOS POR POSICIÓN")
print("-" * 90)

print(
    df_resultado[
        "position_sofascore"
    ].value_counts()
)


print()
print("ENCONTRADOS POR POSICIÓN")
print("-" * 90)

print(
    encontrados[
        "position_sofascore"
    ].value_counts()
)


# ============================================================
# MOSTRAR LOS QUE NO APARECEN
# ============================================================

if not no_encontrados.empty:

    print()
    print("NO ENCONTRADOS EN PITCHAPI")
    print("-" * 90)

    print(
        no_encontrados[
            [
                "jugador",
                "equipo",
                "position_sofascore"
            ]
        ]
        .sort_values("jugador")
        .to_string(index=False)
    )


# ============================================================
# EJEMPLOS
# ============================================================

print()
print("EJEMPLOS DE JUGADORES ENCONTRADOS")
print("-" * 90)

print(
    encontrados[
        [
            "jugador",
            "nombre_pitchapi",
            "equipo",
            "position_sofascore",
            "partidos_historicos_pitchapi",
            "minutos_historicos_pitchapi",
        ]
    ]
    .head(30)
    .to_string(index=False)
)


print()
print(f"Archivo generado: {SALIDA}")
print()