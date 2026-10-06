import os
import pandas as pd

BASE = "datos"
FECHA = 10

AUDITORIA = os.path.join(BASE, "fecha10_auditoria_tapados_vs_real.csv")
CANDIDATOS = os.path.join(BASE, "fecha10_pre_simulacion_candidatos.csv")
EQUIPOS = os.path.join(BASE, "fecha10_pre_simulacion_equipos.csv")
FLEX = os.path.join(BASE, "fecha10_pre_simulacion_flex.csv")
TAPADOS = os.path.join(BASE, "fecha10_tapados.csv")

def cargar(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)

def normalizar(df):
    if df.empty:
        return df
    for c in ["player_id", "player_name", "team_name", "position"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    return df

def primera_fila(df, player_id, player_name):
    if df.empty:
        return pd.DataFrame()
    if "player_id" in df.columns:
        x = df[df["player_id"].astype(str).str.strip() == str(player_id).strip()]
        if not x.empty:
            return x.head(1)
    if "player_name" in df.columns:
        x = df[df["player_name"].astype(str).str.strip() == str(player_name).strip()]
        if not x.empty:
            return x.head(1)
    return pd.DataFrame()

def estado(row):
    if row["final_titular"]:
        return "TITULAR"
    if row["final_flex"]:
        return "FLEX"
    if row["tapado_exclusivo"]:
        return "TAPADO_EXCLUSIVO"
    if row["es_tapado_candidato"]:
        return "TAPADO_CANDIDATO_NO_FINAL"
    if row["elegible_tapado"]:
        return "ELEGIBLE_TAPADO_NO_RANKING"
    if row["en_candidatos"]:
        return "CANDIDATO_NO_TAPADO"
    return "NO_EN_CANDIDATOS"

def main():
    audit = normalizar(cargar(AUDITORIA))
    candidatos = normalizar(cargar(CANDIDATOS))
    equipos = normalizar(cargar(EQUIPOS))
    flex = normalizar(cargar(FLEX))
    tapados = normalizar(cargar(TAPADOS))

    if audit.empty:
        raise FileNotFoundError(f"No existe o está vacío: {AUDITORIA}")

    real_col = "_real" if "_real" in audit.columns else "real"
    audit[real_col] = pd.to_numeric(audit[real_col], errors="coerce")
    top = audit.dropna(subset=[real_col]).sort_values(real_col, ascending=False).head(10).copy()

    rows = []
    for _, a in top.iterrows():
        pid = a.get("player_id", "")
        name = str(a.get("player_name", "")).strip()
        team = str(a.get("team_name", "")).strip()

        c = primera_fila(candidatos, pid, name)
        e = primera_fila(equipos, pid, name)
        f = primera_fila(flex, pid, name)
        t = primera_fila(tapados, pid, name)

        cr = c.iloc[0].to_dict() if not c.empty else {}
        er = e.iloc[0].to_dict() if not e.empty else {}
        fr = f.iloc[0].to_dict() if not f.empty else {}
        tr = t.iloc[0].to_dict() if not t.empty else {}

        row = {
            "player_id": pid,
            "player_name": name,
            "team_name": team,
            "position": a.get("position", ""),
            "real_points": a.get(real_col, ""),
            "pre_sim_p90": a.get("pre_sim_p90_ajustada", cr.get("pre_sim_p90_ajustada", "")),
            "tapado_p90_aprendizaje": a.get("tapado_p90_aprendizaje", cr.get("tapado_p90_aprendizaje", "")),
            "score_tapado": a.get("score_tapado", cr.get("score_tapado", "")),
            "tapado_potencial": a.get("tapado_potencial", cr.get("tapado_potencial", "")),
            "tapado_gap": a.get("tapado_gap", cr.get("tapado_gap", "")),
            "ranking_tapado": cr.get("ranking_tapado", ""),
            "es_tapado_candidato": bool(cr.get("es_tapado_candidato", False)),
            "elegible_titular_flex": bool(cr.get("elegible_titular_flex", False)),
            "elegible_tapado": bool(cr.get("elegible_tapado", False)),
            "score_seleccion_seguro": "",
            "score_seleccion_intermedio": "",
            "score_seleccion_arriesgado": "",
            "final_titular": not e.empty and str(er.get("tipo_registro", "")).upper() == "TITULAR",
            "final_perfil_titular": er.get("perfil", ""),
            "final_flex": not f.empty,
            "final_perfil_flex": fr.get("perfil", fr.get("perfil_flex", "")),
            "score_flex": fr.get("score_flex", ""),
            "tapado_exclusivo": not t.empty,
            "ranking_final_tapado": tr.get("ranking_tapado", tr.get("ranking", "")),
        }

        # Recuperar scores por perfil directamente del archivo de candidatos
        # si están presentes; no recalculamos ninguna regla.
        for perfil, key in [
            ("SEGURO", "score_seleccion_seguro"),
            ("INTERMEDIO", "score_seleccion_intermedio"),
            ("ARRIESGADO", "score_seleccion_arriesgado"),
        ]:
            col = f"score_seleccion_{perfil.lower()}"
            if col in cr:
                row[key] = cr[col]
            elif str(cr.get("perfil", "")).upper() == perfil:
                row[key] = cr.get("score_seleccion", "")

        row["diagnostico"] = estado(row)
        rows.append(row)

    out = pd.DataFrame(rows)
    out["real_rank"] = range(1, len(out) + 1)

    cols = [
        "real_rank", "player_name", "team_name", "position", "real_points",
        "pre_sim_p90", "tapado_p90_aprendizaje", "tapado_potencial",
        "tapado_gap", "score_tapado", "ranking_tapado",
        "elegible_tapado", "es_tapado_candidato", "elegible_titular_flex",
        "score_seleccion_seguro", "score_seleccion_intermedio",
        "score_seleccion_arriesgado", "final_titular",
        "final_perfil_titular", "final_flex", "final_perfil_flex",
        "score_flex", "tapado_exclusivo", "ranking_final_tapado",
        "diagnostico"
    ]
    cols = [c for c in cols if c in out.columns]
    out = out[cols]

    destino = os.path.join(BASE, "fecha10_auditoria_pipeline_top10.csv")
    out.to_csv(destino, index=False, encoding="utf-8-sig")

    print("\nAUDITORIA PIPELINE FECHA 10")
    print("=" * 110)
    print(out.to_string(index=False))
    print("\nArchivo:", destino)

if __name__ == "__main__":
    main()
