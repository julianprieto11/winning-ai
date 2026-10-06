import os
import pandas as pd

BASE = "datos"
CANDIDATOS = os.path.join(BASE, "fecha10_pre_simulacion_candidatos.csv")
EQUIPOS = os.path.join(BASE, "fecha10_pre_simulacion_equipos.csv")
REAL = os.path.join(BASE, "fecha10_auditoria_tapados_vs_real.csv")


def cargar(p):
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()


def main():
    c = cargar(CANDIDATOS)
    e = cargar(EQUIPOS)
    r = cargar(REAL)

    if c.empty:
        raise FileNotFoundError(CANDIDATOS)
    if e.empty:
        raise FileNotFoundError(EQUIPOS)

    for df in (c, e, r):
        if not df.empty and "player_id" in df.columns:
            df["player_id"] = df["player_id"].astype(str).str.strip()

    real_col = "_real" if "_real" in r.columns else ("real" if "real" in r.columns else None)
    if real_col:
        rr = r[["player_id", "player_name", real_col]].copy()
        rr["puntos_reales"] = pd.to_numeric(rr[real_col], errors="coerce")
        c = c.merge(rr[["player_id", "puntos_reales"]], on="player_id", how="left")

    # Universo que realmente puede competir por TAPADO:
    # debe ser candidato TAPADO y luego quedar fuera de TITULAR/FLEX.
    if "es_tapado_candidato" in c.columns:
        c = c[c["es_tapado_candidato"].astype(str).str.lower().isin(["true", "1"])].copy()

    # IMPORTANTE:
    # fecha10_tapados.csv es la salida del DETECTOR y contiene muchos candidatos.
    # No representa los 9 TAPADOS finales.
    # Los TAPADOS realmente seleccionados están en equipos.csv con tipo_registro=TAPADO.
    tapados_finales = e[
        e.get("tipo_registro", pd.Series(dtype=str)).astype(str).str.upper() == "TAPADO"
    ].copy()

    seleccionados = set(tapados_finales["player_id"].astype(str)) if not tapados_finales.empty else set()

    # Titulares + FLEX finales. El selector de TAPADOS los excluye antes de ordenar.
    usados = set(
        e[
            e.get("tipo_registro", pd.Series(dtype=str)).astype(str).str.upper().isin(
                ["TITULAR", "FLEX"]
            )
        ]["player_id"].astype(str)
    )

    c["excluido_por_titular_flex_final"] = c["player_id"].isin(usados)
    c["seleccionado_tapado_final"] = c["player_id"].isin(seleccionados)
    c["competidor_final_tapado"] = (
        c["es_tapado_candidato"].astype(bool)
        & ~c["excluido_por_titular_flex_final"]
    )

    cols_num = [
        "score_tapado", "tapado_valor_seleccion", "tapado_potencial",
        "tapado_gap", "tapado_p90_pct", "tapado_p75_pct",
        "tapado_sorpresa_pct", "tapado_p90_aprendizaje",
        "pre_sim_p90_ajustada", "pre_sim_p75_ajustada",
        "matchup_score", "veces_tapado_historico",
        "penalizacion_reconocimiento"
    ]
    for col in cols_num:
        if col in c.columns:
            c[col] = pd.to_numeric(c[col], errors="coerce")

    c["position"] = c["position"].astype(str).str.upper()

    print("\nAUDITORIA REAL DEL SELECTOR FINAL DE TAPADOS — FECHA 10")
    print("=" * 120)
    print("Detector TAPADO: candidatos")
    print("Selector final: 3 por posicion despues de excluir TITULAR + FLEX")
    print()

    for pos in ["DEF", "VOL", "DEL"]:
        g = c[
            (c["position"] == pos)
            & (c["competidor_final_tapado"] == True)
        ].copy()
        g = g.sort_values(
            ["score_tapado", "tapado_potencial"],
            ascending=False
        )

        print(f"\n>>> {pos} — TOP 15 COMPETIDORES REALES DEL SELECTOR")
        cols = [x for x in [
            "player_name", "team_name", "score_tapado", "tapado_potencial",
            "tapado_gap", "tapado_p90_aprendizaje", "matchup_score",
            "veces_tapado_historico", "penalizacion_reconocimiento",
            "puntos_reales", "seleccionado_tapado_final"
        ] if x in g.columns]
        print(g.head(15)[cols].to_string(index=False))

        print(f"\n>>> {pos} — TOP 15 POR PUNTOS REALES DENTRO DEL MISMO UNIVERSO")
        gr = g.dropna(subset=["puntos_reales"]).sort_values(
            "puntos_reales", ascending=False
        )
        print(gr.head(15)[cols].to_string(index=False))

    out_cols = [x for x in [
        "player_id", "player_name", "team_name", "position",
        "score_tapado", "tapado_potencial", "tapado_gap",
        "tapado_p90_aprendizaje", "pre_sim_p90_ajustada",
        "matchup_score", "veces_tapado_historico",
        "penalizacion_reconocimiento", "puntos_reales",
        "excluido_por_titular_flex_final",
        "competidor_final_tapado", "seleccionado_tapado_final"
    ] if x in c.columns]

    destino = os.path.join(BASE, "fecha10_auditoria_ranking_tapados.csv")
    c[out_cols].sort_values(
        ["position", "score_tapado"],
        ascending=[True, False]
    ).to_csv(destino, index=False, encoding="utf-8-sig")

    print("\nArchivo:", destino)


if __name__ == "__main__":
    main()
