import pandas as pd
from collections import Counter


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO_DATASET = "datos/dataset_winning_pitchapi_posiciones.csv"
ARCHIVO_HISTORIAL = "datos/historial_posiciones_pitchapi.csv"

SALIDA = "datos/posiciones_finales_jugadores.csv"

# Si un position_id tiene una posición dominante igual o
# superior a este valor, consideramos que PitchAPI es claro.
UMBRAL_DOMINANCIA = 0.80


# ============================================================
# FUNCIONES
# ============================================================

def convertir_sofascore(posicion):

    if pd.isna(posicion):
        return None

    posicion = str(posicion).strip().upper()

    mapa = {
        "G": "ARQ",
        "D": "DEF",
        "M": "VOL",
        "F": "DEL",
    }

    return mapa.get(posicion)


# ============================================================
# 1. CARGAR ARCHIVOS
# ============================================================

print()
print("==============================================")
print(" CLASIFICACION FINAL DE POSICIONES")
print("==============================================")
print()

dataset = pd.read_csv(ARCHIVO_DATASET)
historial = pd.read_csv(ARCHIVO_HISTORIAL)

print(f"Registros dataset:   {len(dataset):,}")
print(f"Registros historial: {len(historial):,}")
print()


# ============================================================
# 2. OBTENER POSICIÓN SOFASCORE POR JUGADOR
# ============================================================

print("Construyendo posición SofaScore...")

dataset["posicion_sofascore_final"] = dataset[
    "posicion_sofascore"
].apply(convertir_sofascore)

posiciones_sofascore = {}

for player_id, grupo in dataset.groupby("player_id"):

    posiciones = (
        grupo["posicion_sofascore_final"]
        .dropna()
        .tolist()
    )

    if not posiciones:
        continue

    contador = Counter(posiciones)

    posicion, cantidad = contador.most_common(1)[0]

    posiciones_sofascore[str(player_id)] = posicion


print(
    f"Jugadores con posición SofaScore: "
    f"{len(posiciones_sofascore):,}"
)

print()


# ============================================================
# 3. PREPARAR HISTORIAL
# ============================================================

print("Analizando position_id de PitchAPI...")

historial["player_id"] = (
    historial["player_id"]
    .astype(str)
)

historial["posicion_sofascore"] = (
    historial["player_id"]
    .map(posiciones_sofascore)
)

historial_cruzado = historial[
    historial["posicion_sofascore"].notna()
].copy()

print(
    f"Registros cruzados: "
    f"{len(historial_cruzado):,}"
)

print()


# ============================================================
# 4. APRENDER QUÉ SIGNIFICA CADA POSITION_ID
# ============================================================

mapa_position_id = {}

for position_id, grupo in historial_cruzado.groupby(
    "position_id"
):

    posiciones = grupo[
        "posicion_sofascore"
    ].tolist()

    contador = Counter(posiciones)

    total = sum(contador.values())

    if total == 0:
        continue

    posicion_dominante, cantidad = (
        contador.most_common(1)[0]
    )

    dominancia = cantidad / total

    mapa_position_id[position_id] = {
        "posicion": posicion_dominante,
        "dominancia": dominancia,
        "total": total,
        "distribucion": dict(contador),
    }


# ============================================================
# 5. CLASIFICAR CADA JUGADOR
# ============================================================

print("Clasificando jugadores...")

resultados = []

for player_id, grupo in historial.groupby("player_id"):

    player_id = str(player_id)

    nombre = (
        grupo["player_name"]
        .dropna()
        .astype(str)
        .iloc[0]
    )

    # --------------------------------------------------------
    # POSICIÓN SOFASCORE
    # --------------------------------------------------------

    posicion_sofascore = posiciones_sofascore.get(
        player_id
    )

    # --------------------------------------------------------
    # POSICIONES PITCHAPI CLARAS
    # --------------------------------------------------------

    posiciones_pitchapi_claras = []

    for position_id in grupo["position_id"].dropna():

        try:
            position_id = int(position_id)
        except (ValueError, TypeError):
            continue

        info = mapa_position_id.get(position_id)

        if info is None:
            continue

        if info["dominancia"] >= UMBRAL_DOMINANCIA:

            posiciones_pitchapi_claras.append(
                info["posicion"]
            )

    # --------------------------------------------------------
    # POSICIÓN PITCHAPI CLARA
    # --------------------------------------------------------

    posicion_pitchapi = None
    dominancia_pitchapi = 0

    if posiciones_pitchapi_claras:

        contador = Counter(
            posiciones_pitchapi_claras
        )

        posicion_pitchapi, cantidad = (
            contador.most_common(1)[0]
        )

        dominancia_pitchapi = (
            cantidad /
            len(posiciones_pitchapi_claras)
        )

    # --------------------------------------------------------
    # DECISIÓN PRINCIPAL
    # --------------------------------------------------------

    # 1. PitchAPI claro
    if posicion_pitchapi is not None:

        posicion_final = posicion_pitchapi
        fuente = "PITCHAPI"

    # 2. PitchAPI ambiguo + SofaScore disponible
    elif posicion_sofascore is not None:

        posicion_final = posicion_sofascore
        fuente = "SOFASCORE"

    # 3. PitchAPI ambiguo + sin SofaScore
    #    Usamos la posición predominante.
    else:

        posiciones_todas = []

        for position_id in grupo["position_id"].dropna():

            try:
                position_id = int(position_id)
            except (ValueError, TypeError):
                continue

            info = mapa_position_id.get(position_id)

            if info is None:
                continue

            posiciones_todas.append(
                info["posicion"]
            )

        if posiciones_todas:

            contador = Counter(
                posiciones_todas
            )

            posicion_final, cantidad = (
                contador.most_common(1)[0]
            )

            fuente = "PITCHAPI_PREDOMINANTE"

        # 4. Sin ningún dato
        else:

            posicion_final = "REVISAR"
            fuente = "SIN_DATOS"

    # --------------------------------------------------------
    # GUARDAR RESULTADO
    # --------------------------------------------------------

    resultados.append({
        "player_id": player_id,
        "player_name": nombre,
        "posicion_pitchapi": posicion_pitchapi,
        "dominancia_pitchapi": round(
            dominancia_pitchapi * 100,
            2
        ),
        "posicion_sofascore": posicion_sofascore,
        "posicion_final": posicion_final,
        "fuente_posicion": fuente,
        "partidos_historicos": len(grupo),
    })


# ============================================================
# 6. CREAR DATAFRAME FINAL
# ============================================================

df = pd.DataFrame(resultados)

df = df.sort_values(
    ["posicion_final", "player_name"]
)


# ============================================================
# 7. GUARDAR
# ============================================================

df.to_csv(
    SALIDA,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 8. RESUMEN
# ============================================================

print()
print("==============================================")
print(" RESULTADO")
print("==============================================")
print()

print(
    f"Jugadores clasificados: "
    f"{len(df):,}"
)

print()

print("FUENTE UTILIZADA:")

print(
    df["fuente_posicion"]
    .value_counts()
    .to_string()
)

print()

print("POSICIÓN FINAL:")

print(
    df["posicion_final"]
    .value_counts()
    .to_string()
)

print()

revisar = df[
    df["posicion_final"] == "REVISAR"
]

print(
    f"Jugadores para revisar manualmente: "
    f"{len(revisar):,}"
)

print()

print(
    f"Archivo generado:\n"
    f"{SALIDA}"
)

print()