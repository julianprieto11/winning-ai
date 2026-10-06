import os
import numpy as np
import pandas as pd

FECHA_INICIO = pd.Timestamp("2026-09-18")
FECHA_FIN = pd.Timestamp("2026-09-23")

ARCHIVOS = {
    "tapados": "datos/fecha10_tapados.csv",
    "candidatos": "datos/fecha10_pre_simulacion_candidatos.csv",
    "equipos": "datos/fecha10_pre_simulacion_equipos.csv",
    "reales": "datos/dataset_winning_pitchapi.csv",
}

def leer(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe: {path}")
    return pd.read_csv(path, low_memory=False)

def elegir(df, opciones):
    for c in opciones:
        if c in df.columns:
            return c
    return None

def normalizar_texto(s):
    return (
        s.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\\s+", " ", regex=True)
    )

def preparar_reales(df):
    fecha_col = elegir(df, ["date", "fecha", "match_date", "fecha_partido"])
    puntos_col = elegir(df, ["winning_total", "points_real", "puntos", "puntos_reales"])
    id_col = elegir(df, ["player_id", "id_player", "playerId"])
    nombre_col = elegir(df, ["player_name", "name", "jugador", "player"])
    equipo_col = elegir(df, ["team_name", "team", "equipo"])

    if not fecha_col or not puntos_col:
        raise ValueError(
            f"No pude identificar fecha/puntos en dataset real. "
            f"Columnas: {list(df.columns)}"
        )

    out = df.copy()
    out["_fecha"] = pd.to_datetime(out[fecha_col], errors="coerce")
    out = out[
        (out["_fecha"] >= FECHA_INICIO)
        & (out["_fecha"] < FECHA_FIN)
    ].copy()

    out["_puntos_reales"] = pd.to_numeric(out[puntos_col], errors="coerce")
    if id_col:
        out["_pid"] = out[id_col].astype(str).str.strip()
    if nombre_col:
        out["_nombre"] = normalizar_texto(out[nombre_col])
    if equipo_col:
        out["_equipo"] = normalizar_texto(out[equipo_col])

    columnas = ["_puntos_reales"]
    for c in ["_pid", "_nombre", "_equipo"]:
        if c in out.columns:
            columnas.append(c)

    out = out[columnas].dropna(subset=["_puntos_reales"]).copy()

    # Un jugador debe tener un único registro de partido en Fecha 10.
    claves = [c for c in ["_pid", "_nombre", "_equipo"] if c in out.columns]
    if claves:
        out = out.sort_values("_puntos_reales", ascending=False).drop_duplicates(claves)

    return out

def unir_reales(pred, reales):
    id_col = elegir(pred, ["player_id", "id_player", "playerId"])
    nombre_col = elegir(pred, ["player_name", "name", "jugador", "player"])
    equipo_col = elegir(pred, ["team_name", "team", "equipo"])

    out = pred.copy()
    if id_col and "_pid" in reales.columns:
        out["_pid"] = out[id_col].astype(str).str.strip()
        out = out.merge(
            reales[["_pid", "_puntos_reales"]].drop_duplicates("_pid"),
            on="_pid",
            how="left",
        )
    elif nombre_col and equipo_col and "_nombre" in reales.columns and "_equipo" in reales.columns:
        out["_nombre"] = normalizar_texto(out[nombre_col])
        out["_equipo"] = normalizar_texto(out[equipo_col])
        out = out.merge(
            reales[["_nombre", "_equipo", "_puntos_reales"]].drop_duplicates(["_nombre", "_equipo"]),
            on=["_nombre", "_equipo"],
            how="left",
        )
    else:
        raise ValueError("No pude encontrar claves para unir predicciones con datos reales.")

    return out

def main():
    tap = leer(ARCHIVOS["tapados"])
    cand = leer(ARCHIVOS["candidatos"])
    reales_raw = leer(ARCHIVOS["reales"])
    reales = preparar_reales(reales_raw)

    tap = unir_reales(tap, reales)
    cand = unir_reales(cand, reales)

    pred_col = elegir(
        tap,
        ["tapado_p90_aprendizaje", "pre_sim_p90_ajustada", "prediccion_final", "score_seleccion"]
    )
    nombre_col = elegir(tap, ["player_name", "name", "jugador", "player"])
    equipo_col = elegir(tap, ["team_name", "team", "equipo"])
    pos_col = elegir(tap, ["posicion_final", "position", "posicion", "perfil"])
    score_col = elegir(tap, ["score_tapado"])
    gap_col = elegir(tap, ["tapado_gap"])
    potencial_col = elegir(tap, ["tapado_potencial"])
    rol_col = elegir(tap, ["rol", "perfil_seleccion", "tipo"])

    if not pred_col:
        raise ValueError(f"No encontré columna de predicción en TAPADOS: {list(tap.columns)}")

    tap["_pred"] = pd.to_numeric(tap[pred_col], errors="coerce")
    tap["_real"] = pd.to_numeric(tap["_puntos_reales"], errors="coerce")
    tap["error_abs"] = (tap["_pred"] - tap["_real"]).abs()

    cand_pred_col = elegir(
        cand,
        ["pre_sim_p90_ajustada", "tapado_p90_aprendizaje", "prediccion_final", "score_seleccion"]
    )
    cand["_pred"] = pd.to_numeric(cand[cand_pred_col], errors="coerce")
    cand["_real"] = pd.to_numeric(cand["_puntos_reales"], errors="coerce")
    cand["error_abs"] = (cand["_pred"] - cand["_real"]).abs()

    tap_valid = tap.dropna(subset=["_pred", "_real"]).copy()
    cand_valid = cand.dropna(subset=["_pred", "_real"]).copy()

    print("=" * 78)
    print("AUDITORIA FECHA 10 — PREDICCION VS PUNTOS REALES")
    print("=" * 78)
    print(f"TAPADOS evaluables: {len(tap_valid)}")
    print(f"CANDIDATOS evaluables: {len(cand_valid)}")
    print(f"MAE TAPADOS: {tap_valid['error_abs'].mean():.3f}" if len(tap_valid) else "MAE TAPADOS: sin datos")
    print(f"MAE CANDIDATOS: {cand_valid['error_abs'].mean():.3f}" if len(cand_valid) else "MAE CANDIDATOS: sin datos")

    print("\n" + "=" * 78)
    print("TOP 15 TAPADOS POR PUNTOS REALES")
    print("=" * 78)
    cols = []
    for c in [nombre_col, equipo_col, pos_col, pred_col, score_col, potencial_col, gap_col]:
        if c and c in tap_valid.columns and c not in cols:
            cols.append(c)
    cols += ["_real", "error_abs"]
    print(
        tap_valid.sort_values("_real", ascending=False)[cols]
        .head(15)
        .to_string(index=False)
    )

    print("\n" + "=" * 78)
    print("TOP 15 FALSOS POSITIVOS TAPADOS (PREDICCION ALTA, REAL BAJO)")
    print("=" * 78)
    fp = tap_valid.sort_values("_pred", ascending=False).copy()
    print(fp[cols].head(15).to_string(index=False))

    print("\n" + "=" * 78)
    print("MEJORES RESCATES: TAPADOS CON >= 15 PUNTOS REALES")
    print("=" * 78)
    rescates = tap_valid[tap_valid["_real"] >= 15].sort_values("_real", ascending=False)
    print(rescates[cols].to_string(index=False) if not rescates.empty else "Ninguno")

    print("\n" + "=" * 78)
    print("COBERTURA DE TOP 10 REAL")
    print("=" * 78)
    top10 = cand_valid.sort_values("_real", ascending=False).head(10)
    tap_keys = set()
    if "_pid" in tap.columns:
        tap_keys = set(tap["_pid"].astype(str))
        top10["es_tapado"] = top10["_pid"].astype(str).isin(tap_keys)
    else:
        tap_keys = set(
            zip(
                normalizar_texto(tap[nombre_col]),
                normalizar_texto(tap[equipo_col]),
            )
        )
        top10["es_tapado"] = list(
            zip(
                normalizar_texto(top10[elegir(top10, ["player_name", "name", "jugador", "player"])]),
                normalizar_texto(top10[elegir(top10, ["team_name", "team", "equipo"])]),
            )
        )
        top10["es_tapado"] = top10["es_tapado"].apply(lambda x: x in tap_keys)

    show_cols = []
    for c in [elegir(top10, ["player_name", "name", "jugador", "player"]),
              elegir(top10, ["team_name", "team", "equipo"]),
              cand_pred_col]:
        if c and c not in show_cols:
            show_cols.append(c)
    show_cols += ["_real", "es_tapado"]
    print(top10[show_cols].to_string(index=False))

    salida = "datos/fecha10_auditoria_tapados_vs_real.csv"
    tap.to_csv(salida, index=False)
    print(f"\nArchivo completo: {salida}")

if __name__ == "__main__":
    main()
