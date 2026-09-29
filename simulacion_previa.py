import numpy as np
import pandas as pd


N_SIM = 10000
SEED = 42


def simular_distribucion(valores, rng, n_sim=N_SIM):
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

    muestra = rng.choice(
        valores.to_numpy(float),
        size=n_sim,
        replace=True,
    )

    return {
        "pre_sim_n": int(len(valores)),
        "pre_sim_media": float(np.mean(muestra)),
        "pre_sim_p50": float(np.quantile(muestra, 0.50)),
        "pre_sim_p75": float(np.quantile(muestra, 0.75)),
        "pre_sim_p90": float(np.quantile(muestra, 0.90)),
        "pre_sim_p95": float(np.quantile(muestra, 0.95)),
        "pre_sim_std": float(np.std(muestra)),
        "pre_sim_prob_10": float(np.mean(muestra >= 10)),
        "pre_sim_prob_15": float(np.mean(muestra >= 15)),
    }


def agregar_pre_simulacion(candidatos, historico, corte, n_sim=N_SIM, seed=SEED):
    """
    Genera una distribución previa para CADA candidato usando únicamente
    su historial anterior al partido objetivo.

    Importante: se ejecuta antes de seleccionar titulares/FLEX.
    No utiliza los puntos reales de la fecha objetivo.
    """
    resultado = candidatos.copy()
    h = historico.copy()

    h["date"] = pd.to_datetime(h["date"], errors="coerce")
    h["winning_total"] = pd.to_numeric(h["winning_total"], errors="coerce")
    h = h[
        h["date"].notna()
        & (h["date"] < pd.Timestamp(corte))
        & h["winning_total"].notna()
    ].copy()

    rng = np.random.default_rng(seed)
    filas = []

    for _, jugador in resultado.iterrows():
        pid = str(jugador.get("player_id", ""))
        club = str(jugador.get("team_name", ""))

        serie = h[
            (h["player_id"].astype(str) == pid)
            & (h["team_name"].astype(str) == club)
        ]["winning_total"]

        # Si no hay historial en el club actual, se usa el historial
        # del jugador como respaldo, manteniendo siempre el corte temporal.
        if serie.empty:
            serie = h[
                h["player_id"].astype(str) == pid
            ]["winning_total"]

        filas.append(
            simular_distribucion(
                serie,
                rng,
                n_sim=n_sim,
            )
        )

    m = pd.DataFrame(filas, index=resultado.index)

    for columna in m.columns:
        resultado[columna] = m[columna]

    media = pd.to_numeric(
        resultado["pre_sim_media"],
        errors="coerce",
    )

    contexto = pd.to_numeric(
        resultado.get("score_contextual", np.nan),
        errors="coerce",
    )

    matchup = pd.to_numeric(
        resultado.get("matchup_score", np.nan),
        errors="coerce",
    ).clip(0.0, 1.0)

    # 0.50 = neutro. El matchup puede mover el centro esperado +/-30%.
    factor_matchup = (
        1.0
        + (matchup.fillna(0.50) - 0.50) * 0.60
    )

    centro_contextual = (
        contexto * factor_matchup
    ).fillna(media)

    delta = (
        centro_contextual - media
    ).fillna(0.0)

    for columna in [
        "pre_sim_media",
        "pre_sim_p50",
        "pre_sim_p75",
        "pre_sim_p90",
        "pre_sim_p95",
    ]:
        resultado[columna + "_ajustada"] = (
            pd.to_numeric(
                resultado[columna],
                errors="coerce",
            )
            + delta
        )

    resultado["pre_sim_factor_matchup"] = factor_matchup
    resultado["pre_sim_centro_contextual"] = centro_contextual

    resultado["score_pre_sim_SEGURO"] = (
        resultado["pre_sim_p50_ajustada"]
    )
    resultado["score_pre_sim_INTERMEDIO"] = (
        resultado["pre_sim_p75_ajustada"]
    )
    resultado["score_pre_sim_ARRIESGADO"] = (
        resultado["pre_sim_p90_ajustada"]
    )

    resultado["pre_simulacion_activa"] = True

    return resultado
