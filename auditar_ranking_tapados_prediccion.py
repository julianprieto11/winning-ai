import glob
import os
import pandas as pd

BASE = "datos"


def cargar(path):
    return pd.read_csv(path, low_memory=False) if os.path.exists(path) else pd.DataFrame()


def num(df, col):
    if col not in df.columns:
        return pd.Series(float("nan"), index=df.index)
    return pd.to_numeric(df[col], errors="coerce")


def analizar_fecha(candidatos_path):
    nombre = os.path.basename(candidatos_path)
    fecha = nombre.replace("fecha", "").replace("_pre_simulacion_candidatos.csv", "")
    equipos_path = os.path.join(BASE, f"fecha{fecha}_pre_simulacion_equipos.csv")

    c = cargar(candidatos_path)
    e = cargar(equipos_path)

    if c.empty or e.empty:
        return [], {"fecha": fecha, "estado": "SIN_DATOS", "motivo": "Falta candidatos o equipos"}

    c = c.copy()
    e = e.copy()
    c["player_id"] = c["player_id"].astype(str).str.strip()
    e["player_id"] = e["player_id"].astype(str).str.strip()

    c["position_norm"] = c["position"].astype(str).str.upper().str.strip()
    tipo = e.get("tipo_registro", pd.Series("", index=e.index)).astype(str).str.upper().str.strip()

    usados = set(e.loc[tipo.isin(["TITULAR", "FLEX"]), "player_id"])
    seleccionados = e.loc[tipo.eq("TAPADO")].copy()
    seleccionados["position_norm"] = seleccionados["position"].astype(str).str.upper().str.strip()

    # Universo exacto que puede alcanzar el selector final:
    # candidato TAPADO + no usado como TITULAR/FLEX.
    elig = c[
        c["es_tapado_candidato"].astype(str).str.lower().isin(["true", "1"])
        & (~c["player_id"].isin(usados))
        & c["position_norm"].isin(["DEF", "VOL", "DEL"])
    ].copy()

    # La predicción principal para TAPADOS es el P90 que el detector
    # realmente usa después de la corrección de aprendizaje.
    elig["prediccion_tapado"] = num(elig, "tapado_p90_aprendizaje")
    elig["prediccion_base"] = num(elig, "pre_sim_p90_ajustada")
    elig["score_tapado_num"] = num(elig, "score_tapado")

    seleccionados = seleccionados.merge(
        elig[[
            "player_id", "prediccion_tapado", "prediccion_base",
            "score_tapado_num"
        ]],
        on="player_id",
        how="left",
        suffixes=("", "_candidato")
    )

    resultados = []
    resumen = {
        "fecha": fecha,
        "estado": "OK",
        "universo_elegible": len(elig),
        "seleccionados": len(seleccionados),
        "inversiones": 0,
        "seleccionados_con_inversion": 0,
        "max_diferencia_prediccion": 0.0,
    }

    for pos in ["DEF", "VOL", "DEL"]:
        g = elig[elig["position_norm"].eq(pos)].copy()
        s = seleccionados[seleccionados["position_norm"].eq(pos)].copy()

        selected_ids = set(s["player_id"])
        no_selected = g[~g["player_id"].isin(selected_ids)].copy()

        for _, row in s.iterrows():
            pred = row.get("prediccion_tapado", float("nan"))
            if pd.isna(pred):
                continue

            mejores = no_selected[
                no_selected["prediccion_tapado"].notna()
                & (no_selected["prediccion_tapado"] > pred)
            ].sort_values("prediccion_tapado", ascending=False)

            if mejores.empty:
                continue

            mejor = mejores.iloc[0]
            diferencia = float(mejor["prediccion_tapado"] - pred)
            resumen["inversiones"] += 1
            resumen["seleccionados_con_inversion"] += 1
            resumen["max_diferencia_prediccion"] = max(
                resumen["max_diferencia_prediccion"], diferencia
            )

            resultados.append({
                "fecha": fecha,
                "position": pos,
                "seleccionado": row.get("player_name", ""),
                "seleccionado_id": row["player_id"],
                "prediccion_seleccionado": float(pred),
                "score_tapado_seleccionado": row.get("score_tapado_num", float("nan")),
                "competidor_mejor": mejor.get("player_name", ""),
                "competidor_id": mejor["player_id"],
                "prediccion_competidor": float(mejor["prediccion_tapado"]),
                "score_tapado_competidor": mejor.get("score_tapado_num", float("nan")),
                "diferencia_prediccion": diferencia,
                "prediccion_base_seleccionado": row.get("prediccion_base", float("nan")),
                "prediccion_base_competidor": mejor.get("prediccion_base", float("nan")),
                "factor_reconocimiento_seleccionado": row.get("factor_reconocimiento_tapado", float("nan")),
                "factor_reconocimiento_competidor": mejor.get("factor_reconocimiento_tapado", float("nan")),
                "motivo_auditoria": "SELECCIONADO_CON_MENOR_PREDICCION",
            })

    return resultados, resumen


def main():
    paths = sorted(
        glob.glob(os.path.join(BASE, "fecha*_pre_simulacion_candidatos.csv")),
        key=lambda p: int(
            os.path.basename(p).split("fecha", 1)[1].split("_", 1)[0]
        )
    )

    if not paths:
        raise FileNotFoundError(
            "No encontré datos/fecha*_pre_simulacion_candidatos.csv"
        )

    todos = []
    resumenes = []

    for path in paths:
        try:
            hallazgos, resumen = analizar_fecha(path)
            todos.extend(hallazgos)
            resumenes.append(resumen)
        except Exception as exc:
            resumenes.append({
                "fecha": os.path.basename(path),
                "estado": "ERROR",
                "motivo": repr(exc),
            })

    out_hallazgos = pd.DataFrame(todos)
    out_resumen = pd.DataFrame(resumenes)

    hallazgos_path = os.path.join(BASE, "auditoria_ranking_tapados_prediccion.csv")
    resumen_path = os.path.join(BASE, "auditoria_ranking_tapados_resumen.csv")

    out_hallazgos.to_csv(hallazgos_path, index=False, encoding="utf-8-sig")
    out_resumen.to_csv(resumen_path, index=False, encoding="utf-8-sig")

    print()
    print("=" * 110)
    print("AUDITORIA HISTORICA — RANKING FINAL DE TAPADOS VS PREDICCION")
    print("=" * 110)
    print("No modifica el modelo.")
    print("Criterio: un TAPADO seleccionado es una INVERSION si existe otro")
    print("TAPADO elegible de la misma posicion, no usado como TITULAR/FLEX,")
    print("con una prediccion P90 TAPADO superior.")
    print()

    if out_resumen.empty:
        print("No hubo fechas procesables.")
        return

    for _, r in out_resumen.iterrows():
        if r.get("estado") != "OK":
            print(f"Fecha {r.get('fecha')}: {r.get('estado')} | {r.get('motivo', '')}")
            continue
        print(
            f"Fecha {int(float(r['fecha'])):>2} | "
            f"elegibles={int(r['universo_elegible']):>3} | "
            f"seleccionados={int(r['seleccionados']):>2} | "
            f"inversiones={int(r['inversiones']):>2} | "
            f"máx diferencia={float(r['max_diferencia_prediccion']):>6.2f}"
        )

    print()
    total = len(out_hallazgos)
    fechas_con = (
        int((out_resumen.get("inversiones", pd.Series(dtype=float)).fillna(0) > 0).sum())
        if not out_resumen.empty else 0
    )
    print(f"TOTAL INVERSIONES: {total}")
    print(f"FECHAS CON AL MENOS UNA INVERSION: {fechas_con}")

    if total:
        print()
        print("TOP 20 INVERSIONES POR DIFERENCIA DE PREDICCION:")
        cols = [
            "fecha", "position", "seleccionado", "prediccion_seleccionado",
            "competidor_mejor", "prediccion_competidor",
            "diferencia_prediccion", "score_tapado_seleccionado",
            "score_tapado_competidor",
            "factor_reconocimiento_seleccionado",
            "factor_reconocimiento_competidor",
        ]
        print(
            out_hallazgos.sort_values(
                "diferencia_prediccion", ascending=False
            )[cols].head(20).to_string(index=False)
        )
    else:
        print()
        print("RESULTADO: no se encontraron inversiones de prediccion.")

    print()
    print("Archivos:")
    print("-", hallazgos_path)
    print("-", resumen_path)


if __name__ == "__main__":
    main()
