import numpy as np
import pandas as pd
import backtest_fecha10 as motor

CORTE = pd.Timestamp("2026-09-16")
N_SIM = 10000
SEED = 42

SALIDA_CANDIDATOS = "datos/fecha10_pre_simulacion_candidatos.csv"
SALIDA_EQUIPOS = "datos/fecha10_pre_simulacion_equipos.csv"
SALIDA_FLEX = "datos/fecha10_pre_simulacion_flex.csv"


def simular_distribucion(valores, rng):
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
    muestra = rng.choice(valores.to_numpy(float), size=N_SIM, replace=True)
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


def agregar_pre_simulacion(candidatos, historico):
    rng = np.random.default_rng(SEED)
    h = historico.copy()
    h["date"] = pd.to_datetime(h["date"], errors="coerce")
    h["winning_total"] = pd.to_numeric(h["winning_total"], errors="coerce")
    h = h[h["date"].notna() & (h["date"] < CORTE) & h["winning_total"].notna()].copy()

    filas = []
    for _, j in candidatos.iterrows():
        pid = str(j["player_id"])
        club = str(j["team_name"])
        serie = h[(h["player_id"].astype(str) == pid) & (h["team_name"].astype(str) == club)]["winning_total"]
        if serie.empty:
            serie = h[h["player_id"].astype(str) == pid]["winning_total"]
        filas.append(simular_distribucion(serie, rng))

    m = pd.DataFrame(filas, index=candidatos.index)
    for c in m.columns:
        candidatos[c] = m[c]

    # Contextualizacion especifica del partido objetivo.
    # El contexto del jugador/equipo y el matchup modifican el
    # centro esperado de la distribucion historica.
    #
    # matchup_score esta normalizado entre 0 y 1:
    # 0.50 = neutro; 0.00 = -10%; 1.00 = +10%.
    # El limite evita que el matchup domine el historial.

    media = pd.to_numeric(
        candidatos["pre_sim_media"],
        errors="coerce"
    )

    contexto = pd.to_numeric(
        candidatos["score_contextual"],
        errors="coerce"
    )

    matchup = pd.to_numeric(
        candidatos["matchup_score"],
        errors="coerce"
    ).clip(0.0, 1.0)

    factor_matchup = (
        1.0
        + (matchup.fillna(0.50) - 0.50) * 0.20
    )

    centro_contextual = (
        contexto * factor_matchup
    ).fillna(media)

    delta = (
        centro_contextual - media
    ).fillna(0.0)

    for c in [
        "pre_sim_media",
        "pre_sim_p50",
        "pre_sim_p75",
        "pre_sim_p90",
        "pre_sim_p95",
    ]:
        candidatos[c + "_ajustada"] = (
            pd.to_numeric(
                candidatos[c],
                errors="coerce"
            ) + delta
        )

    candidatos["pre_sim_factor_matchup"] = factor_matchup
    candidatos["pre_sim_centro_contextual"] = centro_contextual

    candidatos["score_pre_sim_SEGURO"] = candidatos["pre_sim_p50_ajustada"]
    candidatos["score_pre_sim_INTERMEDIO"] = candidatos["pre_sim_p75_ajustada"]
    candidatos["score_pre_sim_ARRIESGADO"] = candidatos["pre_sim_p90_ajustada"]
    return candidatos


def activar_score_pre_simulacion():
    original = motor.calcular_score_seleccion

    def score_experimental(df, perfil):
        r = original(df, perfil).copy()
        columna = "score_pre_sim_" + perfil
        r["score_seleccion"] = pd.to_numeric(r[columna], errors="coerce").fillna(-np.inf)
        r["score_seleccion_original"] = r["score_seleccion"]
        return r

    motor.calcular_score_seleccion = score_experimental


def guardar_equipos(equipos):
    filas = []
    for perfil, jugadores in equipos.items():
        for j in jugadores:
            fila = dict(j)
            fila["motor"] = "PRE_SIMULACION"
            fila["perfil"] = perfil
            fila["tipo_registro"] = "TITULAR"
            filas.append(fila)
    pd.DataFrame(filas).to_csv(SALIDA_EQUIPOS, index=False, encoding="utf-8-sig")


def construir_flex(candidatos, equipos):
    flex_por_perfil = {}
    flex_usados = set()
    titulares_global = {str(j["player_id"]) for js in equipos.values() for j in js}

    for perfil in ["SEGURO", "INTERMEDIO", "ARRIESGADO"]:
        propios = {str(j["player_id"]) for j in equipos.get(perfil, [])}
        otros = titulares_global - propios
        flex = motor.construir_flex(
            candidatos.copy(),
            perfil,
            propios,
            otros,
            jugadores_titulares_global=titulares_global,
            flex_usados_global=flex_usados,
        )
        flex_por_perfil[perfil] = flex
        flex_usados.update(str(j["player_id"]) for j in flex)

    filas = []
    for perfil, jugadores in flex_por_perfil.items():
        for j in jugadores:
            fila = dict(j)
            fila["motor"] = "PRE_SIMULACION"
            fila["perfil"] = perfil
            fila["tipo_registro"] = "FLEX"
            filas.append(fila)
    pd.DataFrame(filas).to_csv(SALIDA_FLEX, index=False, encoding="utf-8-sig")
    return flex_por_perfil


def main():
    print("=" * 72)
    print("WINNING AI - PRE-SIMULACION + OPTIMIZADOR - FECHA 10")
    print("=" * 72)
    print("Corte historico:", CORTE.strftime("%d/%m/%Y"))
    print("Simulaciones por jugador:", N_SIM)

    historico = pd.read_csv(motor.HISTORICO_FILE, low_memory=False)
    # El motor compara la fecha histórica contra un Timestamp.
    # Normalizamos aquí para evitar mezclar strings con fechas.
    historico["date"] = pd.to_datetime(historico["date"], errors="coerce")
    partidos = motor.cargar_partidos_fecha10()
    jugadores = motor.construir_jugadores_objetivo(historico, partidos)
    mapa = motor.construir_mapa_lineups_historicos()
    contexto, forma, local_visitante, rendimiento = motor.cargar_contextos()
    posiciones = motor.cargar_posiciones()

    candidatos = motor.construir_candidatos(
        historico, jugadores, mapa, contexto, forma,
        local_visitante, rendimiento, posiciones
    )

    modelo, columnas = motor.entrenar_modelo_c()
    candidatos = motor.agregar_prediccion_modelo_c(candidatos, modelo, columnas)
    candidatos = agregar_pre_simulacion(candidatos, historico)
    candidatos.to_csv(SALIDA_CANDIDATOS, index=False, encoding="utf-8-sig")

    activar_score_pre_simulacion()
    equipos = motor.optimizar_tres_equipos_globalmente(candidatos.copy())
    guardar_equipos(equipos)
    flex = construir_flex(candidatos, equipos)

    print()
    print("=" * 72)
    print("PREDICCION PRE-SIMULACION FECHA 10")
    print("=" * 72)

    for perfil in ["SEGURO", "INTERMEDIO", "ARRIESGADO"]:
        print()
        print(">>>", perfil)
        for j in equipos.get(perfil, []):
            print(
                j["position"], "|", j["player_name"], "|", j["team_name"],
                "| rival:", j.get("rival", ""),
                "| objetivo:", round(float(j.get("score_seleccion", 0)), 2)
            )
        print("FLEX:")
        for j in flex.get(perfil, []):
            print(
                j["position"], "|", j["player_name"], "|", j["team_name"],
                "| score FLEX:", round(float(j.get("score_flex", 0)), 2)
            )

    print()
    print("Archivos generados:")
    print("-", SALIDA_CANDIDATOS)
    print("-", SALIDA_EQUIPOS)
    print("-", SALIDA_FLEX)
    print("Los puntos reales de Fecha 10 NO se usan para seleccionar.")


if __name__ == "__main__":
    main()
