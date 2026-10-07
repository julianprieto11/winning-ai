import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DATOS = Path("datos")
EXPERIENCIA = DATOS / "aprendizaje_predicciones.csv"

TIPOS_SELECCION = {"TITULAR", "FLEX", "TAPADO"}
POSICIONES = ["ARQ", "DEF", "VOL", "DEL"]


def num(s):
    return pd.to_numeric(s, errors="coerce")


def top_recall(grupo, pred_col, real_col, k):
    g = grupo.dropna(subset=[pred_col, real_col]).copy()
    if g.empty:
        return np.nan
    top_real = set(g.nlargest(k, real_col)["player_id"].astype(str))
    top_pred = set(g.nlargest(k, pred_col)["player_id"].astype(str))
    if not top_real:
        return np.nan
    return len(top_real & top_pred) / len(top_real)


def percent_rank(grupo, value, ascending=False):
    g = grupo.dropna(subset=[value]).copy()
    if g.empty:
        return np.nan
    ranks = g[value].rank(method="min", ascending=ascending)
    return float((len(g) - ranks.iloc[0] + 1) / len(g)) if not ascending else float(ranks.iloc[0] / len(g))


def main():
    parser = argparse.ArgumentParser(
        description="Auditoría histórica del ranking global de WINNING AI."
    )
    parser.add_argument("--hasta", type=int, default=None)
    parser.add_argument("--umbral", type=float, default=15.0)
    parser.add_argument("--top-real", type=int, default=10)
    args = parser.parse_args()

    if not EXPERIENCIA.exists():
        raise SystemExit(f"No existe {EXPERIENCIA}.")

    df = pd.read_csv(EXPERIENCIA, low_memory=False)
    if df.empty:
        raise SystemExit("aprendizaje_predicciones.csv está vacío.")

    for c in ["fecha", "prediccion_base", "prediccion_final", "puntos_reales"]:
        df[c] = num(df[c])

    df["player_id"] = df["player_id"].astype(str)
    df["position"] = df["position"].astype(str).str.upper().str.strip()
    df["tipo_registro"] = df["tipo_registro"].astype(str).str.upper().str.strip()
    df["perfil"] = df["perfil"].astype(str).str.upper().str.strip()

    if args.hasta is not None:
        df = df[df["fecha"] <= args.hasta].copy()

    df = df.dropna(subset=["fecha", "prediccion_base", "prediccion_final", "puntos_reales"])
    if df.empty:
        raise SystemExit("No hay registros auditables.")

    # CANDIDATO es el universo de decisión antes del optimizador.
    candidatos = df[df["tipo_registro"] == "CANDIDATO"].copy()
    seleccion = df[df["tipo_registro"].isin(TIPOS_SELECCION)].copy()
    seleccion["abs_final"] = (seleccion["puntos_reales"] - seleccion["prediccion_final"]).abs()

    # Si por alguna razón no existe snapshot CANDIDATO, usamos el resto
    # como fallback, pero lo dejamos explícito.
    fuente_ranking = "CANDIDATO"
    if candidatos.empty:
        candidatos = df.copy()
        fuente_ranking = "EXPERIENCIA_COMPLETA_FALLBACK"

    print("=" * 110)
    print("WINNING AI — AUDITORÍA DEL RANKING GLOBAL")
    print("=" * 110)
    print(f"Fechas: {int(df.fecha.min())} -> {int(df.fecha.max())}")
    print(f"Registros totales: {len(df)}")
    print(f"Universo de ranking: {len(candidatos)} ({fuente_ranking})")
    print(f"Registros seleccionados: {len(seleccion)}")
    print()

    # ------------------------------------------------------------------
    # 1. Calidad global de ranking: BASE vs FINAL
    # ------------------------------------------------------------------
    print("--- CAPTURA DE TOP REALES POR POSICIÓN ---")
    filas = []
    for fecha, ffecha in candidatos.groupby("fecha"):
        for pos, g in ffecha.groupby("position"):
            if pos not in POSICIONES:
                continue
            filas.append({
                "fecha": int(fecha),
                "position": pos,
                "casos": len(g),
                "recall_base_top5": top_recall(g, "prediccion_base", "puntos_reales", 5),
                "recall_final_top5": top_recall(g, "prediccion_final", "puntos_reales", 5),
                "recall_base_top10": top_recall(g, "prediccion_base", "puntos_reales", 10),
                "recall_final_top10": top_recall(g, "prediccion_final", "puntos_reales", 10),
                "recall_base_top20": top_recall(g, "prediccion_base", "puntos_reales", 20),
                "recall_final_top20": top_recall(g, "prediccion_final", "puntos_reales", 20),
            })

    ranking = pd.DataFrame(filas)
    if not ranking.empty:
        print(ranking.round(3).to_string(index=False))
        print()
        print("PROMEDIO POR POSICIÓN:")
        print(
            ranking.groupby("position")[
                [
                    "recall_base_top5", "recall_final_top5",
                    "recall_base_top10", "recall_final_top10",
                    "recall_base_top20", "recall_final_top20",
                ]
            ].mean().round(3).to_string()
        )

    # ------------------------------------------------------------------
    # 2. ¿El aprendizaje mueve a los jugadores en la dirección correcta?
    # ------------------------------------------------------------------
    candidatos["abs_base"] = (candidatos["puntos_reales"] - candidatos["prediccion_base"]).abs()
    candidatos["abs_final"] = (candidatos["puntos_reales"] - candidatos["prediccion_final"]).abs()

    print()
    print("--- ERROR POR POSICIÓN: BASE vs FINAL ---")
    error_pos = (
        candidatos.groupby("position")
        .agg(
            casos=("player_id", "size"),
            mae_base=("abs_base", "mean"),
            mae_final=("abs_final", "mean"),
            real_promedio=("puntos_reales", "mean"),
            pred_base=("prediccion_base", "mean"),
            pred_final=("prediccion_final", "mean"),
        )
    )
    error_pos["mejora_pct"] = np.where(
        error_pos["mae_base"] != 0,
        (error_pos["mae_base"] - error_pos["mae_final"]) / error_pos["mae_base"] * 100,
        np.nan,
    )
    print(error_pos.round(3).to_string())

    # ------------------------------------------------------------------
    # 3. Resultado de las decisiones que realmente toma el motor.
    # ------------------------------------------------------------------
    print()
    print("--- RESULTADO DE DECISIONES: TITULAR / FLEX / TAPADO ---")
    if not seleccion.empty:
        sel = (
            seleccion.groupby(["tipo_registro", "position"])
            .agg(
                casos=("player_id", "size"),
                real_promedio=("puntos_reales", "mean"),
                pred_promedio=("prediccion_final", "mean"),
                mae=("abs_final", "mean"),
                pct_umbral=( "puntos_reales", lambda s: float((s >= args.umbral).mean()) ),
                max_real=("puntos_reales", "max"),
            )
            .reset_index()
        )
        print(sel.round(3).to_string(index=False))

        print()
        print(f"TOP DECISIONES: porcentaje con >= {args.umbral:.1f} puntos")
        print(
            seleccion.groupby("tipo_registro")["puntos_reales"]
            .apply(lambda s: float((s >= args.umbral).mean()))
            .mul(100)
            .round(1)
            .rename("porcentaje")
            .to_string()
        )

    # ------------------------------------------------------------------
    # 4. Falsos negativos que sí importan.
    # ------------------------------------------------------------------
    print()
    print(f"--- FALSOS NEGATIVOS: REAL >= {args.umbral:.1f} Y NO ESTÁ ENTRE TOP {args.top_real} ---")
    fn = []
    for (fecha, pos), g in candidatos.groupby(["fecha", "position"]):
        if pos not in POSICIONES:
            continue
        g = g.copy()
        g["rank_final"] = g["prediccion_final"].rank(method="min", ascending=False)
        malos = g[(g["puntos_reales"] >= args.umbral) & (g["rank_final"] > args.top_real)].copy()
        malos["distancia_top"] = malos["rank_final"] - args.top_real
        fn.append(malos)

    if fn:
        falsos = pd.concat(fn, ignore_index=True)
        cols = [
            "fecha", "position", "player_name", "team_name",
            "tipo_registro", "prediccion_base", "prediccion_final",
            "puntos_reales", "rank_final", "distancia_top",
        ]
        cols = [c for c in cols if c in falsos.columns]
        print(
            falsos.sort_values(
                ["puntos_reales", "distancia_top"],
                ascending=[False, True],
            )[cols].head(50).round(3).to_string(index=False)
        )
    else:
        print("No se encontraron falsos negativos con este criterio.")

    # ------------------------------------------------------------------
    # 5. ¿Las decisiones estaban bien posicionadas dentro del universo?
    # ------------------------------------------------------------------
    print()
    print("--- POSICIÓN RELATIVA DE LAS DECISIONES DEL MOTOR ---")
    posiciones_decision = []
    for (fecha, pos), g in candidatos.groupby(["fecha", "position"]):
        if pos not in POSICIONES:
            continue
        s = seleccion[
            (seleccion["fecha"] == fecha)
            & (seleccion["position"] == pos)
        ]
        if s.empty:
            continue
        ranking_map = g[["player_id", "prediccion_final"]].drop_duplicates("player_id")
        ranking_map["rank"] = ranking_map["prediccion_final"].rank(method="min", ascending=False)
        n = len(ranking_map)
        for _, row in s.iterrows():
            rr = ranking_map[ranking_map["player_id"] == row["player_id"]]
            if rr.empty:
                continue
            rank = float(rr.iloc[0]["rank"])
            posiciones_decision.append({
                "fecha": fecha,
                "position": pos,
                "tipo_registro": row["tipo_registro"],
                "player_name": row.get("player_name", ""),
                "prediccion_final": row["prediccion_final"],
                "puntos_reales": row["puntos_reales"],
                "rank": rank,
                "universo": n,
                "percentil_ranking": 1.0 - ((rank - 1.0) / max(n - 1, 1)),
            })

    pd_dec = pd.DataFrame(posiciones_decision)
    if not pd_dec.empty:
        print(
            pd_dec.groupby("tipo_registro")[
                ["rank", "universo", "percentil_ranking", "puntos_reales"]
            ].mean().round(3).to_string()
        )

    # ------------------------------------------------------------------
    # 6. Exportación para inspección detallada.
    # ------------------------------------------------------------------
    out = DATOS / "auditoria_ranking_global.csv"
    ranking.to_csv(DATOS / "auditoria_ranking_global_resumen.csv", index=False, encoding="utf-8-sig")
    if not pd_dec.empty:
        pd_dec.to_csv(out, index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame().to_csv(out, index=False, encoding="utf-8-sig")

    print()
    print("Archivos generados:")
    print("-", DATOS / "auditoria_ranking_global_resumen.csv")
    print("-", out)
    print()
    print("AUDITORÍA TERMINADA — NO MODIFICA EL MOTOR.")


if __name__ == "__main__":
    main()
