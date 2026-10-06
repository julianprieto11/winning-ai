import os
import pandas as pd

BASE = "datos"
CANDIDATOS = os.path.join(BASE, "fecha10_pre_simulacion_candidatos.csv")
TAPADOS = os.path.join(BASE, "fecha10_tapados.csv")
REAL = os.path.join(BASE, "fecha10_auditoria_tapados_vs_real.csv")

def cargar(p):
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

def main():
    c = cargar(CANDIDATOS)
    t = cargar(TAPADOS)
    r = cargar(REAL)

    if c.empty:
        raise FileNotFoundError(CANDIDATOS)

    for df in (c, t, r):
        if not df.empty and "player_id" in df.columns:
            df["player_id"] = df["player_id"].astype(str).str.strip()

    real_col = "_real" if "_real" in r.columns else ("real" if "real" in r.columns else None)
    if real_col:
        rr = r[["player_id", "player_name", real_col]].copy()
        rr["puntos_reales"] = pd.to_numeric(rr[real_col], errors="coerce")
        c = c.merge(rr[["player_id", "puntos_reales"]], on="player_id", how="left")

    # Universo que realmente puede competir por TAPADO:
    # elegible + candidato + no titular/FLEX final.
    if "es_tapado_candidato" in c.columns:
        c = c[c["es_tapado_candidato"].astype(str).str.lower().isin(["true","1"])].copy()

    usados = set()
    if not t.empty and "player_id" in t.columns:
        usados = set(t["player_id"].astype(str))

    # El archivo de TAPADOS final puede tener solo los seleccionados.
    c["seleccionado_tapado_final"] = c["player_id"].isin(usados)

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

    print("\nAUDITORIA FINAL DE TAPADOS — FECHA 10")
    print("=" * 120)

    for pos in ["DEF", "VOL", "DEL"]:
        g = c[c["position"] == pos].copy()
        g = g.sort_values(["score_tapado", "tapado_potencial"], ascending=False)
        print(f"\n>>> {pos} — TOP 15 ELEGIBLES POR SCORE TAPADO")
        cols = [x for x in [
            "player_name","team_name","score_tapado","tapado_potencial",
            "tapado_gap","tapado_p90_aprendizaje","matchup_score",
            "veces_tapado_historico","penalizacion_reconocimiento",
            "puntos_reales","seleccionado_tapado_final"
        ] if x in g.columns]
        print(g.head(15)[cols].to_string(index=False))

        print(f"\n>>> {pos} — TOP 15 POR PUNTOS REALES DENTRO DEL MISMO UNIVERSO")
        gr = g.dropna(subset=["puntos_reales"]).sort_values("puntos_reales", ascending=False)
        print(gr.head(15)[cols].to_string(index=False))

    out_cols = [x for x in [
        "player_id","player_name","team_name","position","score_tapado",
        "tapado_potencial","tapado_gap","tapado_p90_aprendizaje",
        "pre_sim_p90_ajustada","matchup_score","veces_tapado_historico",
        "penalizacion_reconocimiento","puntos_reales","seleccionado_tapado_final"
    ] if x in c.columns]
    destino = os.path.join(BASE, "fecha10_auditoria_ranking_tapados.csv")
    c[out_cols].sort_values(["position","score_tapado"], ascending=[True,False]).to_csv(destino,index=False,encoding="utf-8-sig")
    print("\nArchivo:", destino)

if __name__ == "__main__":
    main()
