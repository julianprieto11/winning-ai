import pandas as pd
import numpy as np
import os

REVISION = "datos/revision_matchup_nan.csv"
DATASET = "datos/dataset_winning_pitchapi.csv"
SALIDA = "datos/diagnostico_transferencias_matchup.csv"

print("=" * 60)
print("DIAGNOSTICO DE TRANSFERENCIAS - CASOS SIN MATCHUP")
print("=" * 60)

revision = pd.read_csv(REVISION, low_memory=False)

if "estado" not in revision.columns:
    raise ValueError("revision_matchup_nan.csv no contiene la columna estado")

casos = revision[
    revision["estado"] == "REVISAR_JUGO"
].copy()

print(f"Casos REVISAR_JUGO: {len(casos)}")

if casos.empty:
    print("No hay casos para analizar.")
    raise SystemExit(0)

df = pd.read_csv(DATASET, low_memory=False)

# ------------------------------------------------------------
# Detectar columnas disponibles
# ------------------------------------------------------------

def elegir_columna(df, opciones, obligatoria=True):
    for col in opciones:
        if col in df.columns:
            return col
    if obligatoria:
        raise ValueError(
            f"No se encontró ninguna de estas columnas: {opciones}"
        )
    return None

COL_NOMBRE = elegir_columna(
    df,
    ["player_name", "nombre", "player", "name"],
)

COL_EQUIPO = elegir_columna(
    df,
    ["team_name", "equipo", "team"],
)

COL_FECHA = elegir_columna(
    df,
    ["date", "fecha", "pitchapi_fecha"],
)

df["_nombre_norm"] = (
    df[COL_NOMBRE]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.casefold()
)

df["_equipo_norm"] = (
    df[COL_EQUIPO]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.casefold()
)

df["_fecha"] = pd.to_datetime(
    df[COL_FECHA],
    errors="coerce",
).dt.normalize()

casos["_nombre_norm"] = (
    casos["player_name"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.casefold()
)

casos["_equipo_norm"] = (
    casos["team_name"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.casefold()
)

casos["_fecha"] = pd.to_datetime(
    casos["date"],
    errors="coerce",
).dt.normalize()

# ------------------------------------------------------------
# Para cada caso buscamos el último registro histórico del
# jugador ANTES del partido.
#
# Esto permite distinguir:
#   - ya estaba en el mismo equipo
#   - llegó desde otro equipo
#   - no existe historial previo con ese nombre
# ------------------------------------------------------------

resultados = []

for _, caso in casos.iterrows():

    nombre = caso["_nombre_norm"]
    equipo_actual = caso["_equipo_norm"]
    fecha = caso["_fecha"]

    historico = df[
        (df["_nombre_norm"] == nombre)
        & (df["_fecha"] < fecha)
    ].copy()

    if historico.empty:
        ultimo_equipo = None
        fecha_ultimo = pd.NaT
        equipos_previos = []
        filas_equipo_actual = 0
    else:
        historico = historico.sort_values("_fecha")

        ultimo = historico.iloc[-1]
        ultimo_equipo = ultimo["_equipo_norm"]
        fecha_ultimo = ultimo["_fecha"]

        equipos_previos = sorted(
            set(
                historico["_equipo_norm"]
                .dropna()
                .loc[lambda s: s != ""]
                .tolist()
            )
        )

        filas_equipo_actual = int(
            (
                historico["_equipo_norm"]
                == equipo_actual
            ).sum()
        )

    transferido = (
        ultimo_equipo is not None
        and ultimo_equipo != equipo_actual
    )

    dias_desde_ultimo_registro = np.nan
    if pd.notna(fecha_ultimo) and pd.notna(fecha):
        dias_desde_ultimo_registro = (
            fecha - fecha_ultimo
        ).days

    resultados.append({
        "date": caso["date"],
        "player_name": caso["player_name"],
        "team_name": caso["team_name"],
        "rival_team_name": caso["rival_team_name"],
        "position": caso["position"],
        "match_id": caso["match_id"],
        "minutos": caso["minutos"],
        "matchup_score": caso["matchup_score"],
        "ultimo_equipo_historico": ultimo_equipo,
        "fecha_ultimo_registro": fecha_ultimo,
        "dias_desde_ultimo_registro": dias_desde_ultimo_registro,
        "transferido_desde_otro_equipo": transferido,
        "equipos_historicos_previos": " | ".join(equipos_previos),
        "registros_previos_mismo_equipo": filas_equipo_actual,
    })

salida = pd.DataFrame(resultados)

# ------------------------------------------------------------
# Clasificación útil para detectar el patrón.
# ------------------------------------------------------------

salida["tipo_caso"] = np.select(
    [
        salida["transferido_desde_otro_equipo"].eq(True),
        salida["registros_previos_mismo_equipo"].eq(0),
        salida["registros_previos_mismo_equipo"].gt(0),
    ],
    [
        "TRANSFERIDO_RECIENTE",
        "SIN_HISTORIAL_PREVIO_EN_EQUIPO",
        "YA_ESTABA_EN_EL_EQUIPO",
    ],
    default="SIN_HISTORIAL_JUGADOR",
)

salida = salida.sort_values(
    ["tipo_caso", "date", "team_name", "player_name"]
)

os.makedirs("datos", exist_ok=True)

salida.to_csv(
    SALIDA,
    index=False,
    encoding="utf-8-sig",
)

print()
print("RESUMEN POR TIPO DE CASO:")
print(
    salida["tipo_caso"]
    .value_counts()
    .to_string()
)

print()
print("TRANSFERIDOS RECIENTES:")
transferidos = salida[
    salida["tipo_caso"] == "TRANSFERIDO_RECIENTE"
]

print(f"Total: {len(transferidos)}")

if not transferidos.empty:
    print(
        transferidos[
            [
                "date",
                "player_name",
                "ultimo_equipo_historico",
                "team_name",
                "dias_desde_ultimo_registro",
                "registros_previos_mismo_equipo",
            ]
        ]
        .head(100)
        .to_string(index=False)
    )

print()
print("YA ESTABAN EN EL EQUIPO:")
mismos = salida[
    salida["tipo_caso"] == "YA_ESTABA_EN_EL_EQUIPO"
]

print(f"Total: {len(mismos)}")

if not mismos.empty:
    print(
        mismos[
            [
                "date",
                "player_name",
                "team_name",
                "registros_previos_mismo_equipo",
            ]
        ]
        .head(30)
        .to_string(index=False)
    )

print()
print(f"ARCHIVO: {SALIDA}")
