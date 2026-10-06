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
        rr = r[["player_id", real_col]].copy()
        rr["puntos_reales"] = pd.to_numeric(rr[real_col], errors="coerce")
        c = c.merge(rr[["player_id", "puntos_reales"]], on="player_id", how="left")

    if "es_tapado_candidato" in c.columns:
        c = c[c["es_tapado_candidato"].astype(str).str.lower().isin(["true", "1"])].copy()

    tipo = e.get("tipo_registro", pd.Series(index=e.index, dtype=str)).astype(str).str.upper()
    usados = set(e[tipo.isin(["TITULAR", "FLEX"])]["player_id"].astype(str))
    c["competidor_final_tapado"] = ~c["player_id"].isin(usados)

    for col in [
        "tapado_p90_pct", "tapado_potencial", "tapado_sorpresa_pct",
        "factor_reconocimiento_tapado", "score_tapado", "puntos_reales"
    ]:
        if col in c.columns:
            c[col] = pd.to_numeric(c[col], errors="coerce")

    # Reconstrucción de la parte del score que NO depende del reconocimiento.
    # Fórmula actual:
    # bruto = 0.50*P90_pct + 0.30*potencial + 0.20*sorpresa_pct
    # score = bruto * factor_reconocimiento
    c["score_bruto_sin_reconocimiento"] = (
        0.50 * c["tapado_p90_pct"]
        + 0.30 * c["tapado_potencial"]
        + 0.20 * c["tapado_sorpresa_pct"]
    )

    print("\nAUDITORIA CONTRAFACTUAL DEL RECONOCIMIENTO — FECHA 10")
    print("=" * 120)
    print("NO modifica el modelo.")
    print("Comparamos la selección actual contra escenarios donde la penalización histórica es menos agresiva.")
    print()

    escenarios = [
        ("ACTUAL", lambda s, f: s * f),
        ("SIN_PENALIZACION", lambda s, f: s),
        ("PISO_070", lambda s, f: s * max(f, 0.70)),
        ("PISO_080", lambda s, f: s * max(f, 0.80)),
        ("PISO_090", lambda s, f: s * max(f, 0.90)),
    ]

    resultados = []

    for nombre, formula in escenarios:
        x = c.copy()
        f = x["factor_reconocimiento_tapado"].fillna(1.0)
        x["score_contrafactual"] = formula(x["score_bruto_sin_reconocimiento"], f)

        print(f"\n### ESCENARIO {nombre}")
        for pos in ["DEF", "VOL", "DEL"]:
            g = x[(x["position"].astype(str).str.upper() == pos) &
                  (x["competidor_final_tapado"] == True)].copy()
            g = g.sort_values(
                ["score_contrafactual", "tapado_potencial"],
                ascending=False
            )
            top = g.head(3)
            print(f"\n{pos} TOP 3:")
            cols = [q for q in [
                "player_name", "score_contrafactual", "factor_reconocimiento_tapado",
                "tapado_p90_pct", "tapado_potencial", "tapado_sorpresa_pct",
                "puntos_reales"
            ] if q in top.columns]
            print(top[cols].to_string(index=False))

            real = g.dropna(subset=["puntos_reales"]).sort_values(
                "puntos_reales", ascending=False
            )
            top_real = real.head(3)
            print(f"{pos} MEJORES 3 POR PUNTOS REALES ENTRE COMPETIDORES:")
            print(top_real[[q for q in [
                "player_name", "puntos_reales", "score_contrafactual"
            ] if q in top_real.columns]].to_string(index=False))

            for _, row in top.iterrows():
                resultados.append({
                    "escenario": nombre,
                    "position": pos,
                    "player_id": row["player_id"],
                    "player_name": row.get("player_name", ""),
                    "score": row["score_contrafactual"],
                    "puntos_reales": row.get("puntos_reales", float("nan"))
                })

    out = pd.DataFrame(resultados)
    destino = os.path.join(BASE, "fecha10_auditoria_contrafactual_reconocimiento.csv")
    out.to_csv(destino, index=False, encoding="utf-8-sig")

    print("\nRESUMEN DE LOS 9 CUPOS")
    print("=" * 120)
    for nombre in [x[0] for x in escenarios]:
        z = out[out["escenario"] == nombre].copy()
        reales = z["puntos_reales"].dropna()
        print(
            f"{nombre:18s} | "
            f"reales_conocidos={len(reales):2d} | "
            f"suma_reales={reales.sum():7.3f} | "
            f"promedio_reales={reales.mean() if len(reales) else float('nan'):7.3f} | "
            f">=10={int((reales >= 10).sum()):2d} | "
            f">=15={int((reales >= 15).sum()):2d}"
        )

    print("\nArchivo:", destino)


if __name__ == "__main__":
    main()
