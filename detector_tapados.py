import numpy as np
import pandas as pd

from aprendizaje_fecha import aplicar_correccion

POSICIONES_TAPADO = ("DEF", "VOL", "DEL")
MIN_POTENCIAL_PERCENTIL = 0.60
TOP_TAPADOS_POR_POSICION = 10
MAX_TITULARES_PARA_TAPADO = 3
MAX_FLEX_PARA_TAPADO = 3

# ============================================================
# RECONOCIMIENTO HISTORICO DEL JUGADOR
# ============================================================
EXPERIENCIA_FILE = "datos/aprendizaje_predicciones.csv"

def _penalizacion_tapado_por_frecuencia(cantidad):
    cantidad = int(max(0, cantidad))
    if cantidad <= 0: return 0.00
    if cantidad == 1: return 0.05
    if cantidad == 2: return 0.10
    if cantidad == 3: return 0.15
    if cantidad == 4: return 0.20
    if cantidad == 5: return 0.30
    if cantidad == 6: return 0.40
    if cantidad == 7: return 0.50
    return 0.60

def _penalizacion_titular_por_frecuencia(cantidad):
    return min(0.90, max(0, int(cantidad)) * 0.25)

def _penalizacion_flex_por_frecuencia(cantidad):
    return min(0.80, max(0, int(cantidad)) * 0.20)

def calcular_reconocimiento_historico(candidatos, fecha_objetivo=None, experiencia_file=EXPERIENCIA_FILE):
    df = candidatos.copy()
    columnas = ["veces_titular_historico","veces_flex_historico","veces_tapado_historico","penalizacion_titular_historico","penalizacion_flex_historico","penalizacion_tapado_historico","penalizacion_reconocimiento","factor_reconocimiento_tapado"]
    for c in columnas: df[c] = 0.0
    # Sin historial de reconocimiento = 0% de penalización.\n    # 1.0 es el factor neutro; no reconocer todavía a un jugador\n    # no debe castigarlo automáticamente.\n    df["factor_reconocimiento_tapado"] = 1.0
    df["bloqueado_por_reconocimiento"] = False
    if df.empty: return df
    try: experiencia = pd.read_csv(experiencia_file, low_memory=False)
    except Exception: experiencia = pd.DataFrame()
    if experiencia.empty: return df
    requeridas = {"player_id", "tipo_registro", "fecha"}
    if not requeridas.issubset(experiencia.columns): return df
    experiencia = experiencia.copy()
    experiencia["player_id"] = experiencia["player_id"].astype(str)
    experiencia["tipo_registro"] = experiencia["tipo_registro"].astype(str).str.upper().str.strip()
    experiencia["fecha"] = pd.to_numeric(experiencia["fecha"], errors="coerce")
    if fecha_objetivo is not None:
        experiencia = experiencia[experiencia["fecha"] < int(fecha_objetivo)].copy()
    experiencia = experiencia[experiencia["tipo_registro"].isin({"TITULAR","FLEX","TAPADO"}) & experiencia["fecha"].notna()].copy()
    if experiencia.empty: return df
    conteos = (experiencia.drop_duplicates(["player_id","fecha","tipo_registro"]).groupby(["player_id","tipo_registro"]).size().unstack(fill_value=0))
    for idx, jugador in df.iterrows():
        pid = str(jugador.get("player_id", ""))
        if pid not in conteos.index: continue
        fila = conteos.loc[pid]
        nt = int(fila.get("TITULAR", 0)); nf = int(fila.get("FLEX", 0)); na = int(fila.get("TAPADO", 0))
        pt = _penalizacion_titular_por_frecuencia(nt); pf = _penalizacion_flex_por_frecuencia(nf); pa = _penalizacion_tapado_por_frecuencia(na)
        p = max(pt, pf, pa)
        df.at[idx,"veces_titular_historico"] = nt
        df.at[idx,"veces_flex_historico"] = nf
        df.at[idx,"veces_tapado_historico"] = na
        df.at[idx,"penalizacion_titular_historico"] = pt
        df.at[idx,"penalizacion_flex_historico"] = pf
        df.at[idx,"penalizacion_tapado_historico"] = pa
        df.at[idx,"penalizacion_reconocimiento"] = p
        df.at[idx,"factor_reconocimiento_tapado"] = 1.0 - p
        df.at[idx,"bloqueado_por_reconocimiento"] = bool(
            nt > MAX_TITULARES_PARA_TAPADO
            or nf > MAX_FLEX_PARA_TAPADO
        )
    return df


def _percentil_serie(serie):
    s = pd.to_numeric(serie, errors="coerce")
    if s.notna().sum() <= 1:
        return pd.Series(0.5, index=serie.index)
    return s.rank(method="average", pct=True)


def calcular_minutos_esperados(historico, candidatos):
    """
    Proxy de minutos esperados usando solamente historial anterior
    al partido objetivo. Combina promedio total y promedio reciente,
    y utiliza la continuidad de titularidad de los últimos 3 partidos.
    """
    resultado = candidatos.copy()

    if historico is None or historico.empty:
        resultado["minutos_esperados"] = np.nan
        return resultado

    h = historico.copy()

    if "date" not in h.columns or "minutes_played" not in h.columns:
        resultado["minutos_esperados"] = np.nan
        return resultado

    h["date"] = pd.to_datetime(h["date"], errors="coerce")
    h["minutes_played"] = pd.to_numeric(
        h["minutes_played"], errors="coerce"
    )

    salida = []

    for _, jugador in resultado.iterrows():
        pid = str(jugador.get("player_id", ""))
        club = str(jugador.get("team_name", ""))
        corte = pd.to_datetime(
            jugador.get("fecha_partido", pd.NaT),
            errors="coerce"
        )

        serie = h[
            (h["player_id"].astype(str) == pid)
            & (h["team_name"].astype(str) == club)
            & h["date"].notna()
        ].copy()

        if pd.notna(corte):
            serie = serie[serie["date"] < corte]

        serie = serie.sort_values("date")

        if serie.empty:
            salida.append(np.nan)
            continue

        minutos = serie["minutes_played"].dropna()

        if minutos.empty:
            salida.append(np.nan)
            continue

        promedio_total = float(minutos.mean())
        ultimos_5 = minutos.tail(5)
        pesos = np.arange(1, len(ultimos_5) + 1)
        promedio_reciente = float(
            np.average(ultimos_5, weights=pesos)
        )

        esperado = promedio_total * 0.35 + promedio_reciente * 0.65

        titulares_3 = pd.to_numeric(
            pd.Series([jugador.get("titulares_ultimos_3", 0)]),
            errors="coerce"
        ).iloc[0]

        participaciones_3 = pd.to_numeric(
            pd.Series([jugador.get("participaciones_ultimos_3", 0)]),
            errors="coerce"
        ).iloc[0]

        if pd.notna(titulares_3) and pd.notna(participaciones_3):
            if titulares_3 >= 2:
                esperado *= 1.05
            elif participaciones_3 == 0:
                esperado *= 0.85

        salida.append(float(np.clip(esperado, 0.0, 90.0)))

    resultado["minutos_esperados"] = salida
    return resultado


def detectar_tapados(candidatos, historico=None, fecha_objetivo=None):
    """
    Detector independiente de TAPADOS.

    Busca potencial contextual alto con reconocimiento tradicional
    relativamente bajo. No modifica titulares ni FLEX.

    Potencial:
      35% P90 simulado ajustado
      25% P75 simulado ajustado
      15% score contextual
      10% Modelo C
      10% minutos esperados
       5% forma reciente

    Reconocimiento tradicional:
      50% score contextual
      30% promedio histórico
      20% forma reciente

    El matchup y el contexto ya influyen en los percentiles
    simulados ajustados, por lo que no se vuelven a sumar aquí.
    """
    df = candidatos.copy()

    if df.empty:
        return df

    df = calcular_minutos_esperados(historico, df)
    df = calcular_reconocimiento_historico(df, fecha_objetivo=fecha_objetivo)

    columnas = [
        "pre_sim_p75_ajustada",
        "pre_sim_p90_ajustada",
        "score_contextual",
        "prediccion_modelo_c",
        "minutos_esperados",
        "weighted_recent",
        "promedio",
    ]

    for col in columnas:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # El aprendizaje puede rescatar falsos negativos, pero de forma
    # deliberadamente conservadora: solo corrige el P90 hasta +/-2 puntos
    # y nunca reemplaza la simulacion base.
    base_p90 = pd.to_numeric(
        df["pre_sim_p90_ajustada"],
        errors="coerce",
    )
    df["tapado_correccion_aprendizaje"] = 0.0
    df["tapado_p90_aprendizaje"] = base_p90

    if fecha_objetivo is not None:
        aprendizaje = df.copy()
        aprendizaje["score_seleccion"] = base_p90
        aprendizaje = aplicar_correccion(
            aprendizaje,
            fecha_objetivo=int(fecha_objetivo),
        )
        correccion = pd.to_numeric(
            aprendizaje["correccion_aprendizaje"],
            errors="coerce",
        ).fillna(0.0)
        correccion = (correccion * 0.50).clip(-2.0, 2.0)

        df["tapado_correccion_aprendizaje"] = correccion
        df["tapado_p90_aprendizaje"] = (
            base_p90 + correccion
        ).clip(lower=0.0)

    mascara_tapado = (
        df.get("elegible_tapado", pd.Series(False, index=df.index))
        .fillna(False)
        .astype(bool)
    )

    # Los inactivos no pueden ser TAPADOS y tampoco deben alterar
    # el ranking percentil de los jugadores activos.
    df["tapado_p90_pct"] = _percentil_serie(
        df["tapado_p90_aprendizaje"].where(mascara_tapado)
    )
    df["tapado_p75_pct"] = _percentil_serie(
        df["pre_sim_p75_ajustada"].where(mascara_tapado)
    )
    df["tapado_contexto_pct"] = _percentil_serie(
        df["score_contextual"].where(mascara_tapado)
    )
    df["tapado_modelo_c_pct"] = _percentil_serie(
        df["prediccion_modelo_c"].where(mascara_tapado)
    )
    df["tapado_minutos_pct"] = _percentil_serie(
        df["minutos_esperados"].where(mascara_tapado)
    )
    df["tapado_forma_pct"] = _percentil_serie(
        df["weighted_recent"].where(mascara_tapado)
    )

    df["tapado_potencial"] = (
        df["tapado_p90_pct"] * 0.35
        + df["tapado_p75_pct"] * 0.25
        + df["tapado_contexto_pct"] * 0.15
        + df["tapado_modelo_c_pct"] * 0.10
        + df["tapado_minutos_pct"] * 0.10
        + df["tapado_forma_pct"] * 0.05
    )

    df["tapado_reconocimiento"] = (
        _percentil_serie(df["score_contextual"]) * 0.50
        + _percentil_serie(df["promedio"]) * 0.30
        + _percentil_serie(df["weighted_recent"]) * 0.20
    )

    df["tapado_gap"] = (
        df["tapado_potencial"]
        - df["tapado_reconocimiento"]
    )

    df["score_tapado_base"] = (
        df["tapado_gap"] * 0.70
        + df["tapado_potencial"] * 0.30
    )

    # La frecuencia histórica reduce el score, pero no elimina al jugador.
    # Un matchup/contexto excepcional puede volver a levantarlo.
    # ------------------------------------------------------------
    # VALOR FINAL DEL TAPADO
    #
    # score_tapado_base mide principalmente "sorpresa" respecto del
    # reconocimiento historico. Eso sirve para DETECTAR, pero no es
    # suficiente para decidir cual TAPADO conviene llevar finalmente.
    #
    # Una vez que titulares/FLEX quedan fuera del universo, necesitamos
    # priorizar el valor de puntos potencial sin perder la condicion
    # de TAPADO. Por eso combinamos:
    #   50% P90 simulado ajustado
    #   30% potencial TAPADO
    #   20% sorpresa/reconocimiento
    #
    # La penalizacion historica sigue multiplicando el valor final.
    # El score original se conserva como score_tapado_reconocimiento.
    # ------------------------------------------------------------
    df["score_tapado_reconocimiento"] = (
        df["score_tapado_base"]
        * df["factor_reconocimiento_tapado"].clip(0.40, 1.00)
    )

    df["tapado_sorpresa_pct"] = _percentil_serie(
        df["score_tapado_reconocimiento"].where(mascara_tapado)
    )

    df["tapado_valor_seleccion"] = (
        df["tapado_p90_pct"] * 0.50
        + df["tapado_potencial"] * 0.30
        + df["tapado_sorpresa_pct"] * 0.20
    ) * df["factor_reconocimiento_tapado"].clip(0.40, 1.00)

    # Compatibilidad con el selector existente: score_tapado pasa a
    # representar el valor FINAL de seleccion, mientras que el score
    # puramente de reconocimiento queda preservado arriba.
    df["score_tapado"] = df["tapado_valor_seleccion"]

    df["tapado_potencial_suficiente"] = (
        df["tapado_potencial"] >= MIN_POTENCIAL_PERCENTIL
    )

    df["ranking_tapado"] = np.nan

    for posicion in POSICIONES_TAPADO:
        mask = (
            df["position"].astype(str).str.upper() == posicion
        )

        grupo = df.loc[
            mask
            & mascara_tapado
            & (~df["bloqueado_por_reconocimiento"].astype(bool))
            & df["tapado_potencial_suficiente"]
        ].copy()

        if grupo.empty:
            continue

        ordenado = grupo.sort_values(
            ["score_tapado", "tapado_potencial"],
            ascending=False
        )

        df.loc[ordenado.index, "ranking_tapado"] = np.arange(
            1, len(ordenado) + 1
        )

    df["es_tapado_candidato"] = (
        df["ranking_tapado"].notna()
        & mascara_tapado
    )

    return df


def seleccionar_tapados(
    candidatos_con_tapados,
    usados=None,
    cantidad_por_posicion=1,
):
    """
    Selecciona los mejores tapados por posición y evita reutilizar
    jugadores ya usados por titulares/FLEX u otros tapados.
    """
    usados = {str(x) for x in (usados or set())}
    salida = []

    for posicion in POSICIONES_TAPADO:
        grupo = candidatos_con_tapados[
            (
                candidatos_con_tapados["position"].astype(str).str.upper()
                == posicion
            )
            & (
                candidatos_con_tapados["es_tapado_candidato"] == True
            )
            & (
                ~candidatos_con_tapados["player_id"].astype(str).isin(usados)
            )
        ].copy()

        if grupo.empty:
            continue

        grupo = grupo.sort_values(
            ["score_tapado", "tapado_potencial"],
            ascending=False
        )

        for _, jugador in grupo.head(cantidad_por_posicion).iterrows():
            salida.append(jugador.to_dict())
            usados.add(str(jugador["player_id"]))

    return salida
