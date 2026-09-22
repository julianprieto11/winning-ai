import json
import glob
import os
import re
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

RUTA_DATASET = "datos/dataset_winning_pitchapi.csv"
RUTA_PITCHAPI_MATCHES = "datos/pitchapi/matches"
RUTA_SOFASCORE = "datos/partidos"
RUTA_SALIDA = "datos/contexto_equipos.csv"


# ============================================================
# ESTADÍSTICAS SOFASCORE
# ============================================================

SOFASCORE_STATS = [
    "ballPossession",
    "totalShotsOnGoal",
    "shotsOnGoal",
    "shotsOffGoal",
    "blockedScoringAttempt",
    "totalShotsInsideBox",
    "totalShotsOutsideBox",
    "expectedGoals",
    "expectedGoalsOnTarget",
    "bigChanceCreated",
    "bigChanceMissed",
    "touchesInOppBox",
    "finalThirdEntries",
    "fouledFinalThird",
    "cornerKicks",
    "fouls",
    "passes",
    "accuratePasses",
    "accurateCross",
    "accurateLongBalls",
    "duelWonPercent",
    "dispossessed",
    "groundDuelsPercentage",
    "aerialDuelsPercentage",
    "dribblesPercentage",
    "wonTacklePercent",
    "totalTackle",
    "interceptionWon",
    "ballRecovery",
    "totalClearance",
    "goalkeeperSaves",
    "freeKicks",
    "offsides",
    "yellowCards",
    "errorsLeadToShot",
    "errorsLeadToGoal",
]


# ============================================================
# NORMALIZACIÓN DE NOMBRES
# ============================================================

def normalizar_nombre(nombre):
    if nombre is None:
        return ""

    nombre = str(nombre).strip().lower()

    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }

    for origen, destino in reemplazos.items():
        nombre = nombre.replace(origen, destino)

    nombre = re.sub(r"[^a-z0-9]+", " ", nombre)
    nombre = re.sub(r"\s+", " ", nombre).strip()

    return nombre


# ============================================================
# NORMALIZACIÓN DE IDS
# ============================================================

def normalizar_id(valor):
    """
    Convierte un ID a string limpio.

    Esto evita problemas por:
    - espacios
    - valores numéricos
    - NaN
    - diferencias de formato
    """

    if valor is None:
        return ""

    try:
        if pd.isna(valor):
            return ""
    except Exception:
        pass

    return str(valor).strip()


# ============================================================
# FUNCIONES PITCHAPI
# ============================================================

def cargar_match_pitchapi(ruta):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def extraer_datos_match_pitchapi(contenido):
    """
    Extrae del JSON real de PitchAPI:

    - match_id
    - fecha
    - home_team_id
    - home_team
    - away_team_id
    - away_team
    """

    if not isinstance(contenido, dict):
        return None

    data = contenido.get("data", contenido)

    if not isinstance(data, dict):
        return None

    # --------------------------------------------------------
    # MATCH ID
    # --------------------------------------------------------

    match_id = (
        data.get("match_id")
        or data.get("id")
        or contenido.get("match_id")
        or contenido.get("id")
    )

    # --------------------------------------------------------
    # FECHA
    # --------------------------------------------------------

    fecha = (
        data.get("date")
        or data.get("match_date")
        or data.get("start_time")
        or data.get("startTime")
        or data.get("timestamp")
    )

    # --------------------------------------------------------
    # EQUIPO LOCAL
    # --------------------------------------------------------

    home = data.get("home_team")

    home_team_id = None
    home_team = None

    if isinstance(home, dict):

        home_team_id = (
            home.get("id")
            or home.get("team_id")
        )

        home_team = (
            home.get("name")
            or home.get("team_name")
            or home.get("short_name")
        )

    elif isinstance(home, str):

        home_team = home

    # --------------------------------------------------------
    # EQUIPO VISITANTE
    # --------------------------------------------------------

    away = data.get("away_team")

    away_team_id = None
    away_team = None

    if isinstance(away, dict):

        away_team_id = (
            away.get("id")
            or away.get("team_id")
        )

        away_team = (
            away.get("name")
            or away.get("team_name")
            or away.get("short_name")
        )

    elif isinstance(away, str):

        away_team = away

    # --------------------------------------------------------
    # FALLBACKS DE NOMBRES
    # --------------------------------------------------------

    if not home_team:

        home_team = (
            data.get("home_team_name")
            or data.get("homeTeamName")
            or data.get("home")
        )

    if not away_team:

        away_team = (
            data.get("away_team_name")
            or data.get("awayTeamName")
            or data.get("away")
        )

    # --------------------------------------------------------
    # FALLBACKS DE IDS
    # --------------------------------------------------------

    if not home_team_id:

        home_team_id = (
            data.get("home_team_id")
            or data.get("homeTeamId")
        )

    if not away_team_id:

        away_team_id = (
            data.get("away_team_id")
            or data.get("awayTeamId")
        )

    return {
        "match_id": match_id,
        "fecha": fecha,

        "home_team_id": normalizar_id(home_team_id),
        "home_team": home_team,

        "away_team_id": normalizar_id(away_team_id),
        "away_team": away_team,
    }


# ============================================================
# FUNCIONES SOFASCORE
# ============================================================

def cargar_sofascore(ruta):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def extraer_evento_sofascore(contenido):
    """
    La estructura real de SofaScore es:

    {
        "event": {
            "event": {
                ...
            }
        },
        "statistics": {
            "statistics": [...]
        }
    }
    """

    if not isinstance(contenido, dict):
        return None

    bloque_event = contenido.get("event", {})

    if not isinstance(bloque_event, dict):
        return None

    event = bloque_event.get("event", {})

    if not isinstance(event, dict):
        return None

    return event


def extraer_datos_evento_sofascore(contenido):

    event = extraer_evento_sofascore(contenido)

    if not event:
        return None

    home = event.get("homeTeam", {})
    away = event.get("awayTeam", {})

    if not isinstance(home, dict):
        home = {}

    if not isinstance(away, dict):
        away = {}

    return {
        "event_id": event.get("id"),
        "timestamp": event.get("startTimestamp"),
        "home_team": home.get("name"),
        "away_team": away.get("name"),
    }


# ============================================================
# BUSCAR PERÍODO ALL
# ============================================================

def encontrar_bloque_statistics(contenido):
    """
    Devuelve el período ALL, que representa
    las estadísticas del partido completo.
    """

    bloque = contenido.get("statistics", {})

    if not isinstance(bloque, dict):
        return None

    periodos = bloque.get("statistics", [])

    if not isinstance(periodos, list):
        return None

    for periodo in periodos:

        if not isinstance(periodo, dict):
            continue

        if periodo.get("period") == "ALL":
            return periodo

    return None


# ============================================================
# EXTRAER ITEMS DE STATISTICS
# ============================================================

def extraer_items_statistics(bloque):
    """
    Convierte todos los statisticsItems del período ALL
    en una lista plana.
    """

    if not isinstance(bloque, dict):
        return []

    grupos = bloque.get("groups", [])

    if not isinstance(grupos, list):
        return []

    items = []

    for grupo in grupos:

        if not isinstance(grupo, dict):
            continue

        statistics_items = grupo.get(
            "statisticsItems",
            []
        )

        if not isinstance(statistics_items, list):
            continue

        for item in statistics_items:

            if isinstance(item, dict):
                items.append(item)

    return items


# ============================================================
# VALOR DE UNA ESTADÍSTICA
# ============================================================

def convertir_valor(valor):
    """
    Convierte valores numéricos a int/float.

    Mantiene None cuando realmente no existe el dato.

    Ejemplos:
        "45%"       -> 45
        "34/72"     -> 34
        "1.76"      -> 1.76
        0           -> 0
        None        -> None
    """

    if valor is None:
        return None

    if isinstance(valor, (int, float)):
        return valor

    texto = str(valor).strip()

    if texto == "":
        return None

    # --------------------------------------------------------
    # Porcentajes
    # --------------------------------------------------------

    if texto.endswith("%"):
        texto = texto[:-1].strip()

    # --------------------------------------------------------
    # Valores tipo "34/72 (47%)"
    # --------------------------------------------------------

    if "/" in texto:

        primera_parte = texto.split("/")[0].strip()

        try:
            return float(primera_parte)

        except ValueError:
            return None

    # --------------------------------------------------------
    # Número normal
    # --------------------------------------------------------

    try:

        numero = float(texto)

        if numero.is_integer():
            return int(numero)

        return numero

    except ValueError:

        return None


def valor_estadistica(item, lado):
    """
    lado = home / away

    Prioriza:
        homeValue / awayValue

    porque son los valores oficiales
    entregados por SofaScore.
    """

    if not isinstance(item, dict):
        return None

    campo = f"{lado}Value"

    if campo in item:
        return convertir_valor(
            item.get(campo)
        )

    # Fallback
    if lado in item:
        return convertir_valor(
            item.get(lado)
        )

    return None


# ============================================================
# EXTRAER ESTADÍSTICAS DE UN PARTIDO
# ============================================================

def extraer_estadisticas_partido(contenido):
    """
    Devuelve:

    {
        "home": {
            "ballPossession": ...,
            ...
        },
        "away": {
            ...
        }
    }

    Solo utiliza period = ALL.
    """

    resultado = {
        "home": {},
        "away": {},
    }

    bloque = encontrar_bloque_statistics(
        contenido
    )

    if bloque is None:
        return resultado

    items = extraer_items_statistics(
        bloque
    )

    for item in items:

        key = item.get("key")

        if key not in SOFASCORE_STATS:
            continue

        resultado["home"][key] = valor_estadistica(
            item,
            "home"
        )

        resultado["away"][key] = valor_estadistica(
            item,
            "away"
        )

    return resultado


# ============================================================
# CARGAR TODOS LOS PARTIDOS SOFASCORE
# ============================================================

def cargar_todos_sofascore():

    archivos = glob.glob(
        os.path.join(
            RUTA_SOFASCORE,
            "*.json"
        )
    )

    print(
        f"Archivos SofaScore encontrados: {len(archivos)}"
    )

    partidos = []

    for ruta in archivos:

        contenido = cargar_sofascore(ruta)

        if contenido is None:
            continue

        datos_evento = extraer_datos_evento_sofascore(
            contenido
        )

        if not datos_evento:
            continue

        estadisticas = extraer_estadisticas_partido(
            contenido
        )

        datos_evento["estadisticas"] = estadisticas
        datos_evento["ruta"] = ruta

        partidos.append(
            datos_evento
        )

    print(
        f"Partidos SofaScore cargados: {len(partidos)}"
    )

    return partidos


# ============================================================
# FECHA
# ============================================================

def convertir_fecha(valor):

    if valor is None:
        return pd.NaT

    if isinstance(valor, (int, float)):

        try:
            return pd.to_datetime(
                valor,
                unit="s"
            )

        except Exception:
            pass

    try:
        return pd.to_datetime(valor)

    except Exception:
        return pd.NaT


# ============================================================
# BUSCAR PARTIDO SOFASCORE
# ============================================================

def buscar_sofascore(
    home_team,
    away_team,
    fecha,
    partidos_sofascore
):
    """
    Busca coincidencia por:

    - equipo local
    - equipo visitante
    - fecha aproximada

    Se permite una diferencia máxima de 2 días.
    """

    home_norm = normalizar_nombre(
        home_team
    )

    away_norm = normalizar_nombre(
        away_team
    )

    fecha_pitch = convertir_fecha(
        fecha
    )

    candidatos = []

    for partido in partidos_sofascore:

        sf_home = normalizar_nombre(
            partido.get("home_team")
        )

        sf_away = normalizar_nombre(
            partido.get("away_team")
        )

        if sf_home != home_norm:
            continue

        if sf_away != away_norm:
            continue

        fecha_sf = convertir_fecha(
            partido.get("timestamp")
        )

        if pd.isna(fecha_pitch) or pd.isna(fecha_sf):

            diferencia = 0

        else:

            diferencia = abs(
                (
                    fecha_sf - fecha_pitch
                ).total_seconds()
            )

        if diferencia <= 2 * 24 * 60 * 60:

            candidatos.append(
                (
                    diferencia,
                    partido
                )
            )

    if not candidatos:
        return None

    candidatos.sort(
        key=lambda x: x[0]
    )

    return candidatos[0][1]


# ============================================================
# CARGAR DATASET WINNING
# ============================================================

def cargar_dataset():

    if not os.path.exists(RUTA_DATASET):

        raise FileNotFoundError(
            f"No existe el archivo: {RUTA_DATASET}"
        )

    df = pd.read_csv(
        RUTA_DATASET
    )

    print(
        f"Registros PitchAPI: {len(df)}"
    )

    return df


# ============================================================
# CARGAR PARTIDOS PITCHAPI
# ============================================================

def cargar_partidos_pitchapi():

    archivos = glob.glob(
        os.path.join(
            RUTA_PITCHAPI_MATCHES,
            "*.json"
        )
    )

    partidos = {}

    for ruta in archivos:

        contenido = cargar_match_pitchapi(
            ruta
        )

        if contenido is None:
            continue

        datos = extraer_datos_match_pitchapi(
            contenido
        )

        if not datos:
            continue

        match_id = datos.get(
            "match_id"
        )

        if match_id is None:
            continue

        partidos[
            str(match_id)
        ] = datos

    print(
        f"Partidos PitchAPI cargados: {len(partidos)}"
    )

    return partidos


# ============================================================
# ENCONTRAR COLUMNAS DEL DATASET
# ============================================================

def encontrar_columna(
    df,
    opciones
):

    columnas_normalizadas = {
        normalizar_nombre(col): col
        for col in df.columns
    }

    for opcion in opciones:

        opcion_norm = normalizar_nombre(
            opcion
        )

        if opcion_norm in columnas_normalizadas:

            return columnas_normalizadas[
                opcion_norm
            ]

    return None


# ============================================================
# PREPARAR FILAS
# ============================================================

def construir_contexto(
    df,
    partidos_pitchapi,
    partidos_sofascore
):

    columna_match = encontrar_columna(
        df,
        [
            "match_id",
            "matchId",
            "id_match",
        ]
    )

    columna_team = encontrar_columna(
        df,
        [
            "team_id",
            "teamId",
        ]
    )

    if columna_match is None:

        raise ValueError(
            "No se encontró la columna match_id "
            "en dataset_winning_pitchapi.csv"
        )

    if columna_team is None:

        raise ValueError(
            "No se encontró la columna team_id "
            "en dataset_winning_pitchapi.csv"
        )

    filas = []

    partidos_con_sofascore = 0
    partidos_sin_sofascore = 0

    filas_locales = 0
    filas_visitantes = 0
    filas_sin_lado = 0

    cache_sofascore = {}

    for _, fila in df.iterrows():

        match_id = fila[
            columna_match
        ]

        team_id = fila[
            columna_team
        ]

        match_id_str = normalizar_id(
            match_id
        )

        team_id_str = normalizar_id(
            team_id
        )

        # ----------------------------------------------------
        # BUSCAR PARTIDO PITCHAPI
        # ----------------------------------------------------

        partido_pitch = partidos_pitchapi.get(
            match_id_str
        )

        if partido_pitch is None:

            # Intentar también como entero
            try:

                match_id_alt = str(
                    int(
                        float(match_id)
                    )
                )

                partido_pitch = partidos_pitchapi.get(
                    match_id_alt
                )

            except Exception:

                partido_pitch = None

        if partido_pitch is None:
            continue

        # ----------------------------------------------------
        # DATOS DEL PARTIDO
        # ----------------------------------------------------

        home_team = partido_pitch.get(
            "home_team"
        )

        away_team = partido_pitch.get(
            "away_team"
        )

        home_team_id = normalizar_id(
            partido_pitch.get(
                "home_team_id"
            )
        )

        away_team_id = normalizar_id(
            partido_pitch.get(
                "away_team_id"
            )
        )

        fecha = partido_pitch.get(
            "fecha"
        )

        # ----------------------------------------------------
        # DETERMINAR LOCAL / VISITANTE
        #
        # AHORA SE HACE EXCLUSIVAMENTE MEDIANTE TEAM_ID
        # ----------------------------------------------------

        if (
            team_id_str != ""
            and team_id_str == home_team_id
        ):

            es_local = True
            filas_locales += 1

        elif (
            team_id_str != ""
            and team_id_str == away_team_id
        ):

            es_local = False
            filas_visitantes += 1

        else:

            es_local = None
            filas_sin_lado += 1

        # ----------------------------------------------------
        # BUSCAR SOFASCORE
        # ----------------------------------------------------

        cache_key = (
            normalizar_nombre(home_team),
            normalizar_nombre(away_team),
            str(fecha)
        )

        if cache_key not in cache_sofascore:

            sf = buscar_sofascore(
                home_team,
                away_team,
                fecha,
                partidos_sofascore
            )

            cache_sofascore[
                cache_key
            ] = sf

        else:

            sf = cache_sofascore[
                cache_key
            ]

        # ----------------------------------------------------
        # CREAR FILA
        # ----------------------------------------------------

        nueva_fila = fila.to_dict()

        nueva_fila[
            "pitchapi_home_team"
        ] = home_team

        nueva_fila[
            "pitchapi_home_team_id"
        ] = home_team_id

        nueva_fila[
            "pitchapi_away_team"
        ] = away_team

        nueva_fila[
            "pitchapi_away_team_id"
        ] = away_team_id

        nueva_fila[
            "pitchapi_fecha"
        ] = fecha

        nueva_fila[
            "pitchapi_es_local"
        ] = es_local

        # ----------------------------------------------------
        # SOFASCORE
        # ----------------------------------------------------

        if sf is None:

            nueva_fila[
                "sofascore_event_id"
            ] = None

            nueva_fila[
                "sofascore_match"
            ] = False

            for stat in SOFASCORE_STATS:

                nueva_fila[
                    f"sofascore_{stat}"
                ] = None

                nueva_fila[
                    f"rival_{stat}"
                ] = None

            partidos_sin_sofascore += 1

        else:

            nueva_fila[
                "sofascore_event_id"
            ] = sf.get(
                "event_id"
            )

            nueva_fila[
                "sofascore_match"
            ] = True

            partidos_con_sofascore += 1

            estadisticas = sf.get(
                "estadisticas",
                {
                    "home": {},
                    "away": {},
                }
            )

            stats_home = estadisticas.get(
                "home",
                {}
            )

            stats_away = estadisticas.get(
                "away",
                {}
            )

            # ------------------------------------------------
            # ASIGNAR ESTADÍSTICAS PROPIAS / RIVAL
            # ------------------------------------------------

            if es_local is True:

                stats_propias = stats_home
                stats_rival = stats_away

            elif es_local is False:

                stats_propias = stats_away
                stats_rival = stats_home

            else:

                # No inventamos el lado.
                stats_propias = {}
                stats_rival = {}

            # ------------------------------------------------
            # GUARDAR ESTADÍSTICAS
            # ------------------------------------------------

            for stat in SOFASCORE_STATS:

                nueva_fila[
                    f"sofascore_{stat}"
                ] = stats_propias.get(
                    stat
                )

                nueva_fila[
                    f"rival_{stat}"
                ] = stats_rival.get(
                    stat
                )

        filas.append(
            nueva_fila
        )

    print(
        f"Partidos con SofaScore: "
        f"{partidos_con_sofascore}"
    )

    print(
        f"Partidos sin SofaScore: "
        f"{partidos_sin_sofascore}"
    )

    print(
        f"Filas identificadas como LOCAL: "
        f"{filas_locales}"
    )

    print(
        f"Filas identificadas como VISITANTE: "
        f"{filas_visitantes}"
    )

    print(
        f"Filas sin poder determinar LOCAL/VISITANTE: "
        f"{filas_sin_lado}"
    )

    return pd.DataFrame(
        filas
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("CREANDO CONTEXTO DE EQUIPOS")
    print("=" * 60)

    # --------------------------------------------------------
    # Dataset PitchAPI
    # --------------------------------------------------------

    df = cargar_dataset()

    # --------------------------------------------------------
    # Partidos PitchAPI
    # --------------------------------------------------------

    partidos_pitchapi = cargar_partidos_pitchapi()

    # --------------------------------------------------------
    # Partidos SofaScore
    # --------------------------------------------------------

    partidos_sofascore = cargar_todos_sofascore()

    # --------------------------------------------------------
    # Construir contexto
    # --------------------------------------------------------

    contexto = construir_contexto(
        df,
        partidos_pitchapi,
        partidos_sofascore
    )

    # --------------------------------------------------------
    # Crear directorio si no existe
    # --------------------------------------------------------

    directorio_salida = os.path.dirname(
        RUTA_SALIDA
    )

    if directorio_salida:

        os.makedirs(
            directorio_salida,
            exist_ok=True
        )

    # --------------------------------------------------------
    # Guardar
    # --------------------------------------------------------

    contexto.to_csv(
        RUTA_SALIDA,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Resumen
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("CONTEXTO CREADO")
    print("=" * 60)

    print(
        f"FILAS: {len(contexto)}"
    )

    print(
        f"COLUMNAS: {len(contexto.columns)}"
    )

    print(
        f"ARCHIVO: {RUTA_SALIDA}"
    )

    # --------------------------------------------------------
    # COMPROBACIÓN RÁPIDA
    # --------------------------------------------------------

    columnas_prueba = [
        "sofascore_ballPossession",
        "sofascore_totalShotsOnGoal",
        "sofascore_shotsOnGoal",
        "sofascore_expectedGoals",
        "sofascore_bigChanceCreated",
        "sofascore_touchesInOppBox",
        "rival_totalShotsOnGoal",
        "rival_expectedGoals",
        "rival_fouls",
        "rival_fouledFinalThird",
    ]

    columnas_existentes = [
        c
        for c in columnas_prueba
        if c in contexto.columns
    ]

    if columnas_existentes:

        print()
        print(
            "MUESTRA DE ESTADÍSTICAS:"
        )

        print(
            contexto[
                columnas_existentes
            ]
            .head(5)
            .to_string(index=False)
        )

    # --------------------------------------------------------
    # COMPROBACIÓN DE LOCAL/VISITANTE
    # --------------------------------------------------------

    columnas_lado = [
        "match_id",
        "team_id",
        "team_name",
        "pitchapi_home_team",
        "pitchapi_away_team",
        "pitchapi_es_local",
        "sofascore_ballPossession",
        "rival_ballPossession",
    ]

    columnas_lado_existentes = [
        c
        for c in columnas_lado
        if c in contexto.columns
    ]

    if columnas_lado_existentes:

        print()
        print(
            "MUESTRA LOCAL/VISITANTE:"
        )

        print(
            contexto[
                columnas_lado_existentes
            ]
            .head(10)
            .to_string(index=False)
        )

    print()
    print("LISTO.")


if __name__ == "__main__":
    main()