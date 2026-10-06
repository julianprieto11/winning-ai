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

    if "es_tapado_candidato" in c.columns:
        c = c[c["es_tapado_candidato"].astype(str).str.lower().isin(["true", "1"])].copy()

    tipo = e.get("tipo_registro", pd.Series(index=e.index, dtype=str)).astype(str).str.upper()
    tapados_finales = e[tipo == "TAPADO"].copy()
    titulares_flex = e[tipo.isin(["TITULAR", "FLEX"])].copy()

    seleccionados = set(tapados_finales["player_id"].astype(str))
    usados = set(titulares_flex["player_id"].astype(str))

    c["excluido_por_titular_flex_final"] = c["player_id"].isin(usados)
    c["seleccionado_tapado_final"] = c["player_id"].isin(seleccionados)
    c["competidor_final_tapado"] = ~c["excluido_por_titular_flex_final"]

    cols_num = [
        "score_tapado", "tapado_valor_seleccion", "tapado_potencial",
        "tapado_gap", "tapado_p90_pct", "tapado_p75_pct",
        "tapado_sorpresa_pct", "tapado_p90_aprendizaje",
        "pre_sim_p90_ajustada", "pre_sim_p75_ajustada",
        "matchup_score", "veces_tapado_historico",
        "penalizacion_reconocimiento",
        "factor_reconocimiento_tapado",
        "tapado_forma_pct", "tapado_contexto_pct",
        "tapado_modelo_c_pct", "tapado_minutos_pct"
    ]
    for col in cols_num:
        if col in c.columns:
            c[col] = pd.to_numeric(c[col], errors="coerce")

    c["position"] = c["position"].astype(str).str.upper()

    # Reconstruimos exactamente los componentes de la fórmula final conocida.
    # score_tapado = valor_seleccion
    # valor = (0.50*P90_pct + 0.30*potencial + 0.20*sorpresa_pct) * factor_reconocimiento
    if "tapado_valor_seleccion" in c.columns:
        c["valor_recalculado"] = c["tapado_valor_seleccion"]
    else:
        c["valor_recalculado"] = pd.NA

    c["perdida_por_reconocimiento_pct"] = (
        1.0 - c.get("factor_reconocimiento_tapado", pd.Series(1.0, index=c.index))
    )

    print("\nAUDITORIA DE COMPONENTES DEL SCORE TAPADO — FECHA 10")
    print("=" * 125)
    print("Objetivo: explicar por qué un jugador entra/sale del TOP 3 final.")
    print("NO modifica ningún archivo del modelo; solo genera auditoría.")
    print()

    for pos in ["DEF", "VOL", "DEL"]:
        g = c[
            (c["position"] == pos)
            & (c["competidor_final_tapado"] == True)
        ].copy()

        g = g.sort_values(["score_tapado", "tapado_potencial"], ascending=False)

        print(f"\n>>> {pos} — TOP 12 POR SCORE FINAL")
        cols = [x for x in [
            "player_name", "score_tapado", "tapado_valor_seleccion",
            "tapado_p90_pct", "tapado_potencial", "tapado_sorpresa_pct",
            "factor_reconocimiento_tapado", "penalizacion_reconocimiento",
            "perdida_por_reconocimiento_pct", "tapado_gap",
            "tapado_p90_aprendizaje", "puntos_reales",
            "seleccionado_tapado_final"
        ] if x in g.columns]
        print(g.head(12)[cols].to_string(index=False))

        gr = g.dropna(subset=["puntos_reales"]).sort_values("puntos_reales", ascending=False)
        print(f"\n>>> {pos} — TOP 12 POR PUNTOS REALES")
        print(gr.head(12)[cols].to_string(index=False))

    # Comparación directa: seleccionados vs mejores no seleccionados por puntos reales.
    filas = []
    for pos in ["DEF", "VOL", "DEL"]:
        g = c[(c["position"] == pos) & (c["competidor_final_tapado"] == True)].copy()
        for _, row in g.iterrows():
            filas.append(row)

    out = pd.DataFrame(filas)
    out_cols = [x for x in [
        "player_id", "player_name", "team_name", "position",
        "score_tapado", "tapado_valor_seleccion",
        "tapado_p90_pct", "tapado_potential" if "tapado_potential" in out.columns else "tapado_potencial",
        "tapado_potencial", "tapado_sorpresa_pct",
        "factor_reconocimiento_tapado", "penalizacion_reconocimiento",
        "perdida_por_reconocimiento_pct", "tapado_gap",
        "tapado_p90_aprendizaje", "pre_sim_p90_ajustada",
        "matchup_score", "veces_tapado_historico",
        "puntos_reales", "seleccionado_tapado_final"
    ] if x in out.columns]
    destino = os.path.join(BASE, "fecha10_auditoria_componentes_tapado.csv")
    out[out_cols].sort_values(["position", "score_tapado"], ascending=[True, False]).to_csv(
        destino, index=False, encoding="utf-8-sig"
    )
    print("\nArchivo:", destino)


if __name__ == "__main__":
    main()
