import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================

INPUT = "datos/contexto_matchup.csv"
OUTPUT = "datos/contexto_equipos_historico.csv"

# ============================================================
# CARGAR DATOS
# ============================================================

df = pd.read_csv(INPUT)

df["date"] = pd.to_datetime(df["date"], errors="coerce")

# ============================================================
# ESTADÍSTICAS SOFASCORE
# ============================================================

estadisticas = [
    "ballPossession",
    "totalShotsOnGoal",
    "shotsOnGoal",
    "shotsOffGoal",
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
    "blockedScoringAttempt",
]

# ============================================================
# MAPA EQUIPO -> ID
# ============================================================

mapa_equipos = (
    df[["team_name", "team_id"]]
    .dropna()
    .drop_duplicates()
)

mapa_equipos = dict(
    zip(
        mapa_equipos["team_name"],
        mapa_equipos["team_id"]
    )
)

# ============================================================
# CONSTRUIR TABLA PARTIDO-EQUIPO
# ============================================================

columnas = [
    "sofascore_event_id",
    "date",
    "team_id",
    "team_name",
    "rival_team_name",
]

for stat in estadisticas:
    columnas.append(f"sofascore_{stat}")
    columnas.append(f"rival_{stat}")

disponibles = [c for c in columnas if c in df.columns]

partidos = (
    df[disponibles]
    .drop_duplicates(
        subset=[
            "date",
            "team_id",
            "team_name",
            "rival_team_name",
        ]
    )
    .copy()
)

# ID del rival
partidos["rival_team_id"] = (
    partidos["rival_team_name"]
    .map(mapa_equipos)
)

# ============================================================
# ORDEN CRONOLÓGICO
# ============================================================

partidos = (
    partidos
    .sort_values(
        [
            "date",
            "team_id",
        ]
    )
    .reset_index(drop=True)
)

# ============================================================
# HISTÓRICO PROPIO DE CADA EQUIPO
#
# shift(1) garantiza que el partido actual
# NUNCA entre en su propio histórico.
# ============================================================

for stat in estadisticas:

    columna = f"sofascore_{stat}"

    if columna not in partidos.columns:
        continue

    partidos[f"historico_{stat}"] = (
        partidos
        .groupby("team_id")[columna]
        .transform(
            lambda s:
                s.shift(1)
                 .expanding()
                 .mean()
        )
    )

# Cantidad de partidos previos del equipo
partidos["partidos_historicos_equipo"] = (
    partidos
    .groupby("team_id")
    .cumcount()
)

# ============================================================
# HISTÓRICO GENERAL DE CADA EQUIPO
#
# Se calcula independientemente de quién sea el rival.
# ============================================================

historico_equipo = partidos[
    [
        "date",
        "team_id",
    ]
    + [
        f"sofascore_{stat}"
        for stat in estadisticas
        if f"sofascore_{stat}" in partidos.columns
    ]
].copy()

historico_equipo = (
    historico_equipo
    .sort_values(
        [
            "team_id",
            "date",
        ]
    )
    .reset_index(drop=True)
)

# Crear columnas históricas del equipo
for stat in estadisticas:

    columna = f"sofascore_{stat}"

    if columna not in historico_equipo.columns:
        continue

    historico_equipo[f"historico_{stat}"] = (
        historico_equipo
        .groupby("team_id")[columna]
        .transform(
            lambda s:
                s.shift(1)
                 .expanding()
                 .mean()
        )
    )

# ============================================================
# PREPARAR HISTÓRICO DEL RIVAL
# ============================================================

columnas_rival = [
    "date",
    "team_id",
]

for stat in estadisticas:

    historico_col = f"historico_{stat}"

    if historico_col in historico_equipo.columns:
        columnas_rival.append(historico_col)

historico_rival = historico_equipo[
    columnas_rival
].copy()

historico_rival = historico_rival.rename(
    columns={
        "team_id": "rival_team_id"
    }
)

for stat in estadisticas:

    historico_col = f"historico_{stat}"

    if historico_col in historico_rival.columns:

        historico_rival = historico_rival.rename(
            columns={
                historico_col:
                    f"rival_historico_{stat}"
            }
        )

# ============================================================
# UNIR HISTÓRICO DEL RIVAL
#
# Se busca el histórico del rival según:
#
# date + rival_team_id
#
# Esto representa cómo venía jugando ese rival
# antes del partido actual.
# ============================================================

partidos = partidos.merge(
    historico_rival,
    on=[
        "date",
        "rival_team_id",
    ],
    how="left",
)

# ============================================================
# CANTIDAD DE PARTIDOS HISTÓRICOS DEL RIVAL
# ============================================================

cantidad_rival = (
    historico_equipo[
        [
            "date",
            "team_id",
        ]
    ]
    .copy()
)

cantidad_rival["partidos_historicos_rival"] = (
    cantidad_rival
    .groupby("team_id")
    .cumcount()
)

cantidad_rival = cantidad_rival.rename(
    columns={
        "team_id": "rival_team_id"
    }
)

partidos = partidos.merge(
    cantidad_rival,
    on=[
        "date",
        "rival_team_id",
    ],
    how="left",
)

# ============================================================
# GUARDAR
# ============================================================

partidos.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

# ============================================================
# RESUMEN
# ============================================================

print()
print("============================================")
print("HISTÓRICO DE EQUIPOS GENERADO")
print("============================================")
print(f"Archivo: {OUTPUT}")
print(f"Filas: {len(partidos):,}")
print(f"Columnas: {len(partidos.columns)}")
print(f"Equipos: {partidos['team_id'].nunique()}")

print()
print("Primeros registros:")

print(
    partidos[
        [
            "date",
            "team_name",
            "rival_team_name",
            "partidos_historicos_equipo",
            "partidos_historicos_rival",
        ]
    ]
    .head(20)
    .to_string(index=False)
)