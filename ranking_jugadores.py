import pandas as pd
from pathlib import Path

INPUT = Path("datos/dataset_winning_pitchapi.csv")
OUTPUT = Path("datos/rankings_jugadores.csv")

MIN_MINUTES = 450

METRICAS = {
    "pases_precisos": {"col": "accurate_passes", "posiciones": ["VOL", "DEL", "DEF"]},
    "pases_progresivos": {"col": "progressive_passes", "posiciones": ["VOL", "DEF", "DEL"]},
    "pases_ultimo_tercio": {"col": "passes_into_final_third", "posiciones": ["VOL", "DEF", "DEL"]},
    "conducciones_progresivas": {"col": "progressive_carries", "posiciones": ["VOL", "DEL", "DEF"]},
    "ocasiones_creadas": {"col": "chances_created", "posiciones": ["DEL", "VOL"]},
    "tiros_al_arco": {"col": "shots_on_target", "posiciones": ["DEF", "VOL", "DEL"]},
    "duelos_ganados": {"col": "duels_won", "posiciones": ["DEF", "VOL", "DEL"]},
    "intercepciones": {"col": "interceptions", "posiciones": ["DEF", "VOL"]},
    "tackles": {"col": "tackles", "posiciones": ["DEF", "VOL"]},
    "recuperaciones": {"col": "recoveries", "posiciones": ["DEF", "VOL", "DEL"]},
    "despejes": {"col": "clearances", "posiciones": ["DEF"]},
    "bloqueos": {"col": "blocks", "posiciones": ["DEF"]},
    "regates_exitosos": {"col": "take_ons_won", "posiciones": ["VOL", "DEL"]},
    "centros_precisos": {"col": "accurate_crosses", "posiciones": ["DEF", "VOL", "DEL"]},
    "balones_largos_precisos": {"col": "long_balls_accurate", "posiciones": ["ARQ", "DEF", "VOL"]},
    "asistencias": {"col": "assists", "posiciones": ["DEF", "VOL", "DEL"]},
    "goles": {"col": "goals", "posiciones": ["DEF", "VOL", "DEL"]},
    "atajadas": {"col": "saves", "posiciones": ["ARQ"]},
}

def encontrar_columna(df, candidatos):
    for c in candidatos:
        if c in df.columns:
            return c
    return None

def preparar(df):
    col_player = encontrar_columna(df, ["player_id"])
    col_name = encontrar_columna(df, ["player_name", "nombre_jugador", "name"])
    col_pos = encontrar_columna(df, ["posicion", "position", "position_group", "perfil"])
    col_minutes = encontrar_columna(df, ["minutes_played", "minutes"])

    faltantes = [x for x, c in {
        "player_id": col_player,
        "nombre": col_name,
        "posición": col_pos,
        "minutos": col_minutes,
    }.items() if c is None]

    if faltantes:
        raise ValueError("Faltan columnas obligatorias: " + ", ".join(faltantes))

    df = df.copy()
    df[col_minutes] = pd.to_numeric(df[col_minutes], errors="coerce").fillna(0)
    df["_metric_minutes"] = df[col_minutes]

    for met in METRICAS.values():
        df[met["col"]] = pd.to_numeric(df[met["col"]], errors="coerce").fillna(0)

    return df, col_player, col_name, col_pos, col_minutes

def generar_ranking(df, metrica, col_player, col_name, col_pos, col_minutes, posicion=None):
    cfg = METRICAS[metrica]
    trabajo = df[df[col_minutes] >= MIN_MINUTES].copy()

    if posicion is not None:
        trabajo = trabajo[trabajo[col_pos].astype(str).str.upper() == posicion]

    # Agregamos por jugador para obtener total de temporada y minutos.
    agrupado = (
        trabajo.groupby([col_player, col_name, col_pos], as_index=False)
        .agg(
            minutos=(col_minutes, "sum"),
            total=(cfg["col"], "sum"),
        )
    )

    agrupado = agrupado[agrupado["minutos"] >= MIN_MINUTES].copy()
    agrupado["por_90"] = agrupado["total"] / agrupado["minutos"] * 90

    # El ranking se ordena por rendimiento por 90, no por volumen bruto.
    agrupado = agrupado.sort_values(
        ["por_90", "total", "minutos"],
        ascending=[False, False, False],
    ).head(5).copy()

    agrupado.insert(0, "ranking", range(1, len(agrupado) + 1))
    agrupado["metrica"] = metrica
    agrupado["grupo"] = "GENERAL" if posicion is None else posicion

    return agrupado[
        ["metrica", "grupo", "ranking", col_player, col_name, col_pos,
         "minutos", "total", "por_90"]
    ]

def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"No existe {INPUT}")

    df = pd.read_csv(INPUT)
    df, col_player, col_name, col_pos, col_minutes = preparar(df)

    resultados = []

    for metrica, cfg in METRICAS.items():
        resultados.append(
            generar_ranking(
                df, metrica, col_player, col_name, col_pos, col_minutes
            )
        )
        for posicion in cfg["posiciones"]:
            resultados.append(
                generar_ranking(
                    df, metrica, col_player, col_name, col_pos, col_minutes,
                    posicion,
                )
            )

    salida = pd.concat(resultados, ignore_index=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

    print(f"Archivo generado: {OUTPUT}")
    print(f"Filas de ranking: {len(salida)}")
    print(f"Jugadores únicos: {df[col_player].nunique()}")
    print(f"Mínimo de minutos: {MIN_MINUTES}")
    print()
    print("Rankings generados:")
    for metrica, cfg in METRICAS.items():
        grupos = ["GENERAL"] + cfg["posiciones"]
        print(f"  {metrica}: {', '.join(grupos)}")

if __name__ == "__main__":
    main()
