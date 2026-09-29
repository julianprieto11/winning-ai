"""
Integra el detector histórico de TAPADOS al pipeline actual.

No modifica la selección de TITULARES ni FLEX.
Agrega 3 DEF + 3 VOL + 3 DEL al CSV técnico y al CSV que se abre con Excel,
y los deja disponibles para el cerebro de aprendizaje.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import aprendizaje_fecha
import detector_tapados


ROOT = Path(__file__).resolve().parent
DATOS = ROOT / "datos"


def simular_distribucion_previa(valores, rng, n_sim=10000):
    valores = pd.to_numeric(pd.Series(valores), errors="coerce").dropna()
    if valores.empty:
        return {
            "pre_sim_n": 0,
            "pre_sim_media": np.nan,
            "pre_sim_p50": np.nan,
            "pre_sim_p75": np.nan,
            "pre_sim_p90": np.nan,
            "pre_sim_p95": np.nan,
            "pre_sim_std": np.nan,
            "pre_sim_prob_10": np.nan,
            "pre_sim_prob_15": np.nan,
        }
    muestra = rng.choice(valores.to_numpy(float), size=n_sim, replace=True)
    return {
        "pre_sim_n": int(len(valores)),
        "pre_sim_media": float(np.mean(muestra)),
        "pre_sim_p50": float(np.quantile(muestra, .50)),
        "pre_sim_p75": float(np.quantile(muestra, .75)),
        "pre_sim_p90": float(np.quantile(muestra, .90)),
        "pre_sim_p95": float(np.quantile(muestra, .95)),
        "pre_sim_std": float(np.std(muestra)),
        "pre_sim_prob_10": float(np.mean(muestra >= 10)),
        "pre_sim_prob_15": float(np.mean(muestra >= 15)),
    }


def agregar_pre_simulacion(candidatos, historico, corte, n_sim=10000):
    rng = np.random.default_rng(42)
    h = historico.copy()
    h["date"] = pd.to_datetime(h["date"], errors="coerce")
    h["winning_total"] = pd.to_numeric(h["winning_total"], errors="coerce")
    h = h[
        h["date"].notna()
        & (h["date"] < pd.Timestamp(corte))
        & h["winning_total"].notna()
    ].copy()

    filas = []
    for _, j in candidatos.iterrows():
        pid = str(j["player_id"])
        club = str(j["team_name"])
        serie = h[
            (h["player_id"].astype(str) == pid)
            & (h["team_name"].astype(str) == club)
        ]["winning_total"]
        if serie.empty:
            serie = h[h["player_id"].astype(str) == pid]["winning_total"]
        filas.append(simular_distribucion_previa(serie, rng, n_sim))

    m = pd.DataFrame(filas, index=candidatos.index)
    for col in m.columns:
        candidatos[col] = m[col]

    media = pd.to_numeric(candidatos["pre_sim_media"], errors="coerce")
    contexto = pd.to_numeric(candidatos["score_contextual"], errors="coerce")
    matchup = pd.to_numeric(candidatos["matchup_score"], errors="coerce").clip(0.0, 1.0)
    factor_matchup = 1.0 + (matchup.fillna(0.50) - 0.50) * 0.60
    centro_contextual = (contexto * factor_matchup).fillna(media)
    delta = (centro_contextual - media).fillna(0.0)

    for col in ["pre_sim_media", "pre_sim_p50", "pre_sim_p75", "pre_sim_p90", "pre_sim_p95"]:
        candidatos[col + "_ajustada"] = pd.to_numeric(
            candidatos[col], errors="coerce"
        ) + delta

    candidatos["pre_sim_factor_matchup"] = factor_matchup
    candidatos["pre_sim_centro_contextual"] = centro_contextual
    return candidatos


def integrar_fecha(fecha_numero, corte=None):
    fecha = int(fecha_numero)
    sufijo = f"fecha{fecha}"

    candidatos_path = DATOS / f"candidatos_{sufijo}_final.csv"
    equipos_path = DATOS / f"{sufijo}_equipos_predichos.csv"
    excel_path = DATOS / f"{sufijo}_equipos_predichos_excel.csv"
    tapados_path = DATOS / f"{sufijo}_tapados.csv"

    if corte is None:
        fechas = aprendizaje_fecha._fechas_de_fecha(fecha)
        if not fechas:
            raise RuntimeError(f"No se encontró la fecha real del Clausura para Fecha {fecha}.")
        corte = min(fechas)

    corte = pd.Timestamp(corte)

    if not candidatos_path.exists():
        raise FileNotFoundError(f"No existe {candidatos_path}")
    if not equipos_path.exists():
        raise FileNotFoundError(f"No existe {equipos_path}")

    candidatos = pd.read_csv(candidatos_path, low_memory=False)
    historico = pd.read_csv(
        DATOS / "dataset_winning_pitchapi.csv",
        low_memory=False,
    )

    candidatos = agregar_pre_simulacion(
        candidatos,
        historico,
        corte,
    )

    candidatos = detector_tapados.detectar_tapados(
        candidatos,
        historico,
    )

    tapados = detector_tapados.seleccionar_tapados(
        candidatos,
        usados=None,
        cantidad_por_posicion=3,
    )

    if not tapados:
        print("[TAPADOS] No se encontraron candidatos.")
        return

    df_tapados = pd.DataFrame(tapados)

    # Predicción puntual para aprendizaje: media pre-simulada ajustada.
    df_tapados["score_seleccion"] = pd.to_numeric(
        df_tapados["pre_sim_media_ajustada"],
        errors="coerce",
    )
    df_tapados["score_seleccion_original"] = df_tapados["score_seleccion"]
    df_tapados["score_seleccion_sin_aprendizaje"] = df_tapados["score_seleccion"]

    # El cerebro puede corregir también a los TAPADOS usando solamente
    # memoria de fechas anteriores.
    df_tapados = aprendizaje_fecha.aplicar_correccion(
        df_tapados,
        fecha,
    )
    df_tapados["score_seleccion"] = df_tapados["prediccion_final"]

    filas = []
    for orden, j in enumerate(df_tapados.to_dict("records"), start=1):
        filas.append({
            "perfil": "TAPADOS",
            "tipo_registro": "TAPADO",
            "orden": orden,
            "player_id": j.get("player_id", ""),
            "player_name": j.get("player_name", ""),
            "team_name": j.get("team_name", ""),
            "position": j.get("position", ""),
            "rival": j.get("rival", ""),
            "es_local": j.get("es_local", ""),
            "score_contextual": j.get("score_contextual", ""),
            "score_seleccion": j.get("score_seleccion", ""),
            "prediccion_base": j.get("prediccion_base", j.get("pre_sim_media_ajustada", "")),
            "correccion_aprendizaje": j.get("correccion_aprendizaje", 0),
            "prediccion_final": j.get("prediccion_final", j.get("score_seleccion", "")),
            "aprendizaje_casos": j.get("aprendizaje_casos", 0),
            "aprendizaje_patrones": j.get("aprendizaje_patrones", ""),
            "partidos_historicos": j.get("partidos_historicos", ""),
            "participaciones_ultimos_3": j.get("participaciones_ultimos_3", 0),
            "titulares_ultimos_3": j.get("titulares_ultimos_3", 0),
            "promedio": j.get("promedio", ""),
            "p90": j.get("p90", ""),
            "std": j.get("std", ""),
            "factor_contexto": j.get("factor_contexto", ""),
            "factor_confianza": j.get("factor_confianza", ""),
            "matchup_score": j.get("matchup_score", ""),
            "matchup_variables_usadas": j.get("matchup_variables_usadas", ""),
            "prediccion_modelo_c": j.get("prediccion_modelo_c", ""),
            "score_tapado": j.get("score_tapado", ""),
            "tapado_potencial": j.get("tapado_potencial", ""),
            "tapado_reconocimiento": j.get("tapado_reconocimiento", ""),
            "tapado_gap": j.get("tapado_gap", ""),
            "pre_sim_media_ajustada": j.get("pre_sim_media_ajustada", ""),
            "pre_sim_p75_ajustada": j.get("pre_sim_p75_ajustada", ""),
            "pre_sim_p90_ajustada": j.get("pre_sim_p90_ajustada", ""),
            "score_diversidad": "",
            "veces_usado_otros_equipos": "",
            "score_flex": "",
            "flex_repetido": "",
            "titular_mismo_equipo": "",
            "titular_otro_equipo": "",
            "veces_flex_usado": "",
            "perfil_flex": "",
            "sim_promedio_equipo": "",
            "sim_p50_equipo": "",
            "sim_p90_equipo": "",
            "sim_min_equipo": "",
            "sim_max_equipo": "",
            "prob_100": "",
            "prob_140": "",
        })

    nuevos = pd.DataFrame(filas)

    # Evita duplicados si el integrador se ejecuta dos veces para la misma fecha.
    equipos = pd.read_csv(equipos_path, low_memory=False)
    equipos = equipos[
        ~(
            (equipos.get("perfil", "") == "TAPADOS")
            & (equipos.get("tipo_registro", "") == "TAPADO")
        )
    ]
    equipos = pd.concat([equipos, nuevos], ignore_index=True, sort=False)
    equipos.to_csv(equipos_path, index=False, encoding="utf-8-sig")

    if excel_path.exists():
        excel = pd.read_csv(excel_path, sep=";", low_memory=False)
        excel = excel[
            ~(
                (excel.get("Perfil", "") == "TAPADOS")
                & (excel.get("Tipo", "") == "TAPADO")
            )
        ]

        excel_nuevos = pd.DataFrame([
            {
                "Perfil": "TAPADOS",
                "Tipo": "TAPADO",
                "Orden": i + 1,
                "Posición": j.get("position", ""),
                "Jugador": j.get("player_name", ""),
                "Club": j.get("team_name", ""),
                "Rival": j.get("rival", ""),
                "Local": j.get("es_local", ""),
                "Matchup score": j.get("matchup_score", ""),
                "Predicción Modelo C": j.get("prediccion_modelo_c", ""),
                "Score": j.get("score_contextual", ""),
                "Score selección": j.get("score_seleccion", ""),
                "Predicción base": j.get("prediccion_base", j.get("pre_sim_media_ajustada", "")),
                "Corrección aprendizaje": j.get("correccion_aprendizaje", 0),
                "Predicción final": j.get("prediccion_final", ""),
                "Casos aprendizaje": j.get("aprendizaje_casos", 0),
                "Patrones aprendizaje": j.get("aprendizaje_patrones", ""),
                "Historial": j.get("partidos_historicos", ""),
                "Participaciones últimos 3": j.get("participaciones_ultimos_3", 0),
                "Titulares últimos 3": j.get("titulares_ultimos_3", 0),
                "Promedio": j.get("promedio", ""),
                "P90": j.get("p90", ""),
                "Factor contexto": j.get("factor_contexto", ""),
                "Factor confianza": j.get("factor_confianza", ""),
                "Score TAPADO": j.get("score_tapado", ""),
                "Potencial TAPADO": j.get("tapado_potencial", ""),
                "Reconocimiento TAPADO": j.get("tapado_reconocimiento", ""),
                "Gap TAPADO": j.get("tapado_gap", ""),
                "Pre-Sim media": j.get("pre_sim_media_ajustada", ""),
                "Pre-Sim P75": j.get("pre_sim_p75_ajustada", ""),
                "Pre-Sim P90": j.get("pre_sim_p90_ajustada", ""),
                "Score FLEX": "",
                "FLEX repetido": "",
                "FLEX usado antes": "",
                "Titular mismo equipo": "",
                "Titular otro equipo": "",
                "Sim promedio": "",
                "Sim P50": "",
                "Sim P90": "",
                "Sim mínimo": "",
                "Sim máximo": "",
                "Prob ≥100": "",
                "Prob ≥140": "",
            }
            for i, j in enumerate(df_tapados.to_dict("records"))
        ])

        # Mantener las columnas existentes y agregar las nuevas de TAPADOS.
        for col in excel_nuevos.columns:
            if col not in excel.columns:
                excel[col] = ""
        for col in excel.columns:
            if col not in excel_nuevos.columns:
                excel_nuevos[col] = ""

        excel = pd.concat(
            [excel, excel_nuevos[excel.columns]],
            ignore_index=True,
        )

        excel.to_csv(
            excel_path,
            index=False,
            sep=";",
            encoding="utf-8-sig",
        )

        # Mantener también un XLSX real con los TAPADOS ya integrados.
        excel_xlsx_path = excel_path.with_suffix(".xlsx")
        excel.to_excel(
            excel_xlsx_path,
            index=False,
            sheet_name="Equipos",
        )

    df_tapados.to_csv(
        tapados_path,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("=" * 70)
    print(f"[TAPADOS] FECHA {fecha}")
    print("=" * 70)
    for posicion in ["DEF", "VOL", "DEL"]:
        grupo = df_tapados[
            df_tapados["position"].astype(str).str.upper() == posicion
        ]
        print(f">>> {posicion}")
        for _, j in grupo.iterrows():
            print(
                j["player_name"],
                "|", j["team_name"],
                "| score:", round(float(j["score_tapado"]), 3),
                "| potencial:", round(float(j["tapado_potencial"]), 3),
                "| gap:", round(float(j["tapado_gap"]), 3),
                "| predicción:", round(float(j["prediccion_final"]), 3),
            )

    print(f"[TAPADOS] Guardados: {len(df_tapados)}")
    print(f"[TAPADOS] {equipos_path}")
    print(f"[TAPADOS] {excel_path}")
    print(f"[TAPADOS] {tapados_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("fecha", type=int)
    args = parser.parse_args()
    integrar_fecha(args.fecha)
