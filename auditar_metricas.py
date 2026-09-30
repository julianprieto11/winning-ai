import os
import pandas as pd

# ============================================================
# AUDITORÍA DE MÉTRICAS DISPONIBLES
# ============================================================
#
# Lee el dataset histórico de PitchAPI y genera un inventario
# estadístico de las métricas que realmente tenemos disponibles.
#
# No modifica el dataset ni ningún archivo del modelo.
# ============================================================

DATASET = "datos/dataset_winning_pitchapi.csv"
SALIDA = "datos/auditoria_metricas.csv"

COLUMNAS_IDENTIFICACION = {
    "match_id",
    "date",
    "round_name",
    "player_id",
    "player_name",
    "team_id",
    "team_name",
    "position",
    "minutes_played",
    "participacion",
    "match_finished",
}

CATEGORIAS = {
    "PASES": [
        "accurate_passes",
        "passes",
        "progressive_passes",
        "precision_pases",
        "passes_into_final_third",
        "long_balls_accurate",
        "accurate_crosses",
    ],
    "CONDUCCION_1V1": [
        "progressive_carries",
        "take_ons",
        "take_ons_won",
        "failed_dribbles",
        "miscontrols",
        "dispossessed",
    ],
    "ATAQUE_CREACION": [
        "shots_on_target",
        "goals",
        "assists",
        "second_assists",
        "chances_created",
    ],
    "DEFENSA": [
        "duels_won",
        "duels_lost",
        "tackles",
        "interceptions",
        "recoveries",
        "clearances",
        "blocks",
        "dribbled_past",
    ],
    "ARQUERO": [
        "saves",
        "saved_penalties",
        "goals_conceded",
    ],
    "WINNING_DERIVADAS": [
        "area_rival",
        "ultimo_tercio",
        "carreras_progresivas",
        "duelos",
        "perdidas",
        "regates_fallidos",
        "exceso_perdidas",
        "pases",
        "peligro_creado",
        "defensa",
        "arquero",
        "goles_asistencias",
        "disciplina",
        "resultado_puntos",
        "bonus_resultado_jugador",
        "valla_invicta",
        "winning_total",
    ],
    "DISCIPLINA": [
        "yellow_cards",
        "second_yellow",
        "red_cards_direct",
    ],
}

# Campos que son métricas directas de PitchAPI.
# Los campos WINNING_DERIVADAS se mantienen separados para no
# confundir una estadística original con una variable calculada.
METRICAS_DIRECTAS = [
    columna
    for categoria, columnas in CATEGORIAS.items()
    if categoria != "WINNING_DERIVADAS"
    for columna in columnas
]


def categoria_de(columna):
    for categoria, columnas in CATEGORIAS.items():
        if columna in columnas:
            return categoria
    return "OTRAS"


def calcular_por_90(serie, minutos):
    minutos = pd.to_numeric(minutos, errors="coerce")
    valores = pd.to_numeric(serie, errors="coerce")
    return valores.where(minutos > 0) / minutos.where(minutos > 0) * 90


def main():
    if not os.path.exists(DATASET):
        raise FileNotFoundError(
            f"No se encontró el dataset: {DATASET}"
        )

    df = pd.read_csv(DATASET, low_memory=False)

    print("=" * 80)
    print("AUDITORÍA DE MÉTRICAS - PITCHAPI")
    print("=" * 80)
    print(f"Archivo: {DATASET}")
    print(f"Filas: {len(df):,}")
    print(f"Columnas: {len(df.columns)}")
    print()

    metricas = []
    for columna in df.columns:
        if columna in COLUMNAS_IDENTIFICACION:
            continue

        serie = pd.to_numeric(df[columna], errors="coerce")
        numericos = serie.dropna()

        fila = {
            "metrica": columna,
            "categoria": categoria_de(columna),
            "directa_pitchapi": columna in METRICAS_DIRECTAS,
            "registros": len(df),
            "con_dato": int(serie.notna().sum()),
            "sin_dato": int(serie.isna().sum()),
            "cero": int((serie == 0).sum()),
            "disponibilidad_pct": round(
                serie.notna().mean() * 100, 2
            ),
            "cero_pct_sobre_datos": round(
                ((serie == 0).sum() / len(numericos) * 100)
                if len(numericos)
                else 0,
                2,
            ),
            "promedio": round(numericos.mean(), 4)
            if len(numericos)
            else None,
            "mediana": round(numericos.median(), 4)
            if len(numericos)
            else None,
            "maximo": round(numericos.max(), 4)
            if len(numericos)
            else None,
        }

        if columna in METRICAS_DIRECTAS:
            por90 = calcular_por_90(
                df[columna],
                df["minutes_played"],
            )
            fila["promedio_por_90"] = round(
                por90.dropna().mean(), 4
            ) if por90.notna().any() else None
        else:
            fila["promedio_por_90"] = None

        metricas.append(fila)

    auditoria = pd.DataFrame(metricas)

    orden_categorias = [
        "PASES",
        "CONDUCCION_1V1",
        "ATAQUE_CREACION",
        "DEFENSA",
        "ARQUERO",
        "DISCIPLINA",
        "WINNING_DERIVADAS",
        "OTRAS",
    ]

    auditoria["orden_categoria"] = auditoria["categoria"].map(
        {x: i for i, x in enumerate(orden_categorias)}
    ).fillna(99)

    auditoria = auditoria.sort_values(
        ["orden_categoria", "metrica"]
    ).drop(columns=["orden_categoria"])

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    auditoria.to_csv(
        SALIDA,
        index=False,
        encoding="utf-8-sig",
    )

    pd.set_option("display.max_rows", 200)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.width", 220)

    print("MÉTRICAS ENCONTRADAS")
    print("-" * 80)
    print(
        auditoria[
            [
                "metrica",
                "categoria",
                "directa_pitchapi",
                "con_dato",
                "disponibilidad_pct",
                "promedio",
                "mediana",
                "maximo",
                "promedio_por_90",
            ]
        ].to_string(index=False)
    )

    print()
    print("=" * 80)
    print(f"Auditoría guardada en: {SALIDA}")
    print("=" * 80)


if __name__ == "__main__":
    main()
