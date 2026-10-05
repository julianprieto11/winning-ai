import json
import os
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATOS = ROOT / "datos"

DATASET_FILE = DATOS / "dataset_winning_pitchapi.csv"
MEMORIA_FILE = DATOS / "memoria_aprendizaje.csv"
EXPERIENCIA_FILE = DATOS / "aprendizaje_predicciones.csv"


# El aprendizaje NO reemplaza al modelo base.
# Solo puede corregir el score final usando errores de fechas anteriores.
MIN_CASOS = 5
MAX_CORRECCION = 4.0
SHRINK_CASOS = 8.0


FEATURE_COLUMNS = [
    "position",
    "es_local",
    "factor_contexto",
    "factor_confianza",
    "partidos_historicos",
    "participaciones_ultimos_3",
    "titulares_ultimos_3",
    "promedio",
    "p90",
    "std",
    "matchup_score",
]


def _float(value, default=np.nan):
    try:
        value = float(value)
        return value if np.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def _normalizar_bool(value):
    if isinstance(value, bool):
        return value
    texto = str(value).strip().lower()
    if texto in {"true", "1", "si", "sí", "yes"}:
        return True
    if texto in {"false", "0", "no"}:
        return False
    return False


def _banda_form(valor):
    valor = _float(valor)
    if not np.isfinite(valor):
        return "SIN_DATO"
    if valor < 4:
        return "BAJA"
    if valor < 6:
        return "MEDIA_BAJA"
    if valor < 8:
        return "MEDIA_ALTA"
    return "ALTA"


def _banda_matchup(valor):
    valor = _float(valor)
    if not np.isfinite(valor):
        return "SIN_DATO"
    if valor < -0.5:
        return "BAJO"
    if valor > 0.5:
        return "ALTO"
    return "NEUTRO"


def _banda_contexto(valor):
    valor = _float(valor)
    if not np.isfinite(valor):
        return "SIN_DATO"
    if valor < 0.95:
        return "NEGATIVO"
    if valor > 1.05:
        return "POSITIVO"
    return "NEUTRO"


def construir_patrones(fila):
    """Patrones deliberadamente simples para evitar sobreajuste temprano."""
    posicion = str(fila.get("position", "")).upper()
    local = "LOCAL" if _normalizar_bool(fila.get("es_local")) else "VISITANTE"
    form = _banda_form(fila.get("promedio"))
    matchup = _banda_matchup(fila.get("matchup_score"))
    contexto = _banda_contexto(fila.get("factor_contexto"))

    return [
        ("POSICION", posicion),
        ("POSICION_LOCALIA", f"{posicion}|{local}"),
        ("POSICION_FORMA", f"{posicion}|{form}"),
        ("POSICION_MATCHUP", f"{posicion}|{matchup}"),
        ("POSICION_CONTEXTO", f"{posicion}|{contexto}"),
    ]


def _leer_memoria():
    if not MEMORIA_FILE.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(MEMORIA_FILE, low_memory=False)
    except Exception as error:
        print(f"[APRENDIZAJE] No se pudo leer memoria: {error}")
        return pd.DataFrame()


def _guardar_memoria(df):
    MEMORIA_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(MEMORIA_FILE, index=False, encoding="utf-8-sig")


def _leer_experiencia():
    if not EXPERIENCIA_FILE.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(EXPERIENCIA_FILE, low_memory=False)
    except Exception:
        return pd.DataFrame()


def _guardar_experiencia(df):
    EXPERIENCIA_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(EXPERIENCIA_FILE, index=False, encoding="utf-8-sig")


def _fechas_de_fecha(fecha_numero):
    """Obtiene las fechas calendario de una fecha de Liga desde SofaScore local."""
    fechas = set()

    for archivo in (DATOS / "partidos").glob("*.json"):
        try:
            data = json.loads(archivo.read_text(encoding="utf-8"))
            event = data.get("event", {}).get("event", data.get("event", {}))
            round_info = event.get("roundInfo", {}) or {}
            if int(round_info.get("round", -1)) != int(fecha_numero):
                continue

            timestamp = event.get("startTimestamp")
            if timestamp is None:
                continue

            fecha_obj = pd.to_datetime(
                timestamp,
                unit="s",
                utc=True
            ).date()

            # Solo Clausura 2026. El mismo número de ronda existe
            # también en Apertura.
            if fecha_obj < pd.Timestamp("2026-07-23").date():
                continue

            fechas.add(fecha_obj.isoformat())
        except Exception:
            continue

    return sorted(fechas)


def _actuales_por_jugador(dataset, fecha_numero):
    fechas = _fechas_de_fecha(fecha_numero)

    if not fechas:
        raise RuntimeError(
            f"No se pudieron determinar las fechas reales de la Fecha {fecha_numero}."
        )

    df = dataset.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["player_id"] = df["player_id"].astype(str)

    return df[df["date"].isin(fechas)].copy()


def registrar_resultados_fecha(fecha_numero):
    """
    Cierra una predicción ya realizada.

    Usa exclusivamente:
      - la predicción guardada antes de jugarse la fecha;
      - los puntos reales de esa fecha.

    No modifica el modelo base.
    """
    # La versión PRO genera la predicción mediante pre-simulación.
    # Conservamos por separado TITULARES, FLEX y TAPADOS para que el
    # aprendizaje conozca qué tipo de decisión produjo cada error.
    archivos_prediccion = [
        (DATOS / f"fecha{int(fecha_numero)}_pre_simulacion_equipos.csv", "TITULAR"),
        (DATOS / f"fecha{int(fecha_numero)}_pre_simulacion_flex.csv", "FLEX"),
    ]

    predicciones = []

    for archivo, tipo_default in archivos_prediccion:
        if not archivo.exists():
            continue
        bloque = pd.read_csv(archivo, low_memory=False)
        if bloque.empty:
            continue
        if "tipo_registro" not in bloque.columns:
            bloque["tipo_registro"] = tipo_default
        else:
            bloque["tipo_registro"] = bloque["tipo_registro"].fillna(tipo_default)
        predicciones.append(bloque)

    # TAPADOS no participan del optimizador principal, pero sí son una
    # fuente de experiencia. Para ellos usamos P90 pre-simulado como
    # predicción de puntos esperados; el score_tapado sigue siendo solo
    # el detector de potencial/reconocimiento.
    archivo_tapados = DATOS / f"fecha{int(fecha_numero)}_tapados.csv"
    if archivo_tapados.exists():
        tapados = pd.read_csv(archivo_tapados, low_memory=False)
        if not tapados.empty:
            tapados["tipo_registro"] = "TAPADO"
            tapados["perfil"] = "TAPADOS"
            tapados["prediccion_base"] = pd.to_numeric(
                tapados.get("pre_sim_p90_ajustada"),
                errors="coerce",
            )
            tapados["prediccion_final"] = tapados["prediccion_base"]
            predicciones.append(tapados)

    if not DATASET_FILE.exists():
        raise RuntimeError(f"No existe {DATASET_FILE}.")

    dataset = pd.read_csv(DATASET_FILE, low_memory=False)

    if not predicciones:
        print(
            f"[APRENDIZAJE] No existen predicciones PRO para Fecha {fecha_numero}; "
            "se salta esta fecha."
        )
        return

    pred = pd.concat(predicciones, ignore_index=True, sort=False)

    if pred.empty:
        return

    reales = _actuales_por_jugador(dataset, fecha_numero)

    if reales.empty:
        print(
            f"[APRENDIZAJE] No hay puntos reales todavía para Fecha {fecha_numero}."
        )
        return

    reales = (
        reales
        .sort_values(["player_id", "date", "match_id"])
        .drop_duplicates(["player_id", "team_name"], keep="last")
    )

    columnas_reales = [
        "player_id",
        "team_name",
        "date",
        "winning_total",
        "match_id",
    ]

    reales = reales[
        [c for c in columnas_reales if c in reales.columns]
    ].copy()

    pred["player_id"] = pred["player_id"].astype(str)
    pred["team_name"] = pred["team_name"].astype(str)

    # Un jugador puede aparecer como TITULAR y FLEX. Ambos registros
    # conservan la experiencia de la decisión concreta del motor.
    merged = pred.merge(
        reales,
        on=["player_id", "team_name"],
        how="left",
        suffixes=("", "_real"),
    )

    merged["puntos_reales"] = pd.to_numeric(
        merged.get("winning_total"),
        errors="coerce",
    )

    merged["prediccion_base"] = pd.to_numeric(
        merged.get("prediccion_base", merged.get("score_seleccion")),
        errors="coerce",
    )

    merged["prediccion_final"] = pd.to_numeric(
        merged.get("prediccion_final", merged.get("score_seleccion")),
        errors="coerce",
    )

    merged["error_base"] = (
        merged["puntos_reales"] - merged["prediccion_base"]
    )

    merged["error_final"] = (
        merged["puntos_reales"] - merged["prediccion_final"]
    )

    merged["error_abs_base"] = merged["error_base"].abs()
    merged["error_abs_final"] = merged["error_final"].abs()

    merged["fecha_prediccion"] = int(fecha_numero)
    merged["fecha_real"] = int(fecha_numero)

    # El snapshot conserva las características que el motor tenía
    # al momento de predecir. No se reconstruyen después.
    filas = []
    for _, fila in merged.iterrows():
        if not np.isfinite(_float(fila.get("puntos_reales"))):
            continue

        registro = {
            "fecha": int(fecha_numero),
            "player_id": str(fila.get("player_id", "")),
            "player_name": fila.get("player_name", ""),
            "team_name": fila.get("team_name", ""),
            "position": fila.get("position", ""),
            "rival": fila.get("rival", ""),
            "es_local": fila.get("es_local", False),
            "tipo_registro": fila.get("tipo_registro", ""),
            "perfil": fila.get("perfil", ""),
            "prediccion_base": _float(fila.get("prediccion_base")),
            "correccion_aprendizaje": _float(
                fila.get("correccion_aprendizaje"), 0.0
            ),
            "prediccion_final": _float(fila.get("prediccion_final")),
            "puntos_reales": _float(fila.get("puntos_reales")),
            "error_base": _float(fila.get("error_base")),
            "error_final": _float(fila.get("error_final")),
            "error_abs_base": _float(fila.get("error_abs_base")),
            "error_abs_final": _float(fila.get("error_abs_final")),
            "match_id": fila.get("match_id_real", fila.get("match_id", "")),
        }

        for columna in FEATURE_COLUMNS:
            registro[columna] = fila.get(columna, np.nan)

        filas.append(registro)

    if not filas:
        print(
            f"[APRENDIZAJE] Fecha {fecha_numero}: no hubo predicciones "
            "con puntos reales identificables."
        )
        return

    nuevas = pd.DataFrame(filas)
    anteriores = _leer_experiencia()

    if not anteriores.empty:
        # Evita duplicar una fecha si ejecutar_fecha.py se vuelve a correr.
        claves_nuevas = set(
            zip(
                nuevas["fecha"].astype(str),
                nuevas["player_id"].astype(str),
                nuevas["tipo_registro"].astype(str),
                nuevas["perfil"].astype(str),
            )
        )

        mask = ~anteriores.apply(
            lambda r: (
                str(r.get("fecha", "")),
                str(r.get("player_id", "")),
                str(r.get("tipo_registro", "")),
                str(r.get("perfil", "")),
            ) in claves_nuevas,
            axis=1,
        )
        anteriores = anteriores[mask]

    experiencia = pd.concat(
        [anteriores, nuevas],
        ignore_index=True,
    )

    _guardar_experiencia(experiencia)

    # La memoria se recalcula solamente con fechas ya cerradas.
    construir_memoria(experiencia)

    print(
        f"[APRENDIZAJE] Fecha {fecha_numero}: "
        f"{len(nuevas)} predicciones cerradas y guardadas."
    )


def construir_memoria(experiencia=None):
    if experiencia is None:
        experiencia = _leer_experiencia()

    if experiencia.empty:
        _guardar_memoria(pd.DataFrame())
        return

    filas = []

    for _, fila in experiencia.iterrows():
        error = _float(fila.get("error_base"))
        if not np.isfinite(error):
            continue

        for tipo, clave in construir_patrones(fila):
            filas.append(
                {
                    "patron_tipo": tipo,
                    "patron": clave,
                    "fecha_maxima": int(_float(fila.get("fecha"), 0)),
                    "error_base": error,
                    "error_abs": abs(error),
                }
            )

    if not filas:
        _guardar_memoria(pd.DataFrame())
        return

    df = pd.DataFrame(filas)

    memoria = (
        df.groupby(["patron_tipo", "patron"], dropna=False)
        .agg(
            casos=("error_base", "size"),
            error_medio=("error_base", "mean"),
            error_mediano=("error_base", "median"),
            desvio_error=("error_base", "std"),
            error_abs_medio=("error_abs", "mean"),
            fecha_maxima=("fecha_maxima", "max"),
        )
        .reset_index()
    )

    memoria["desvio_error"] = memoria["desvio_error"].fillna(0.0)

    # Corrección estadística con shrinkage:
    # pocos casos -> casi cero;
    # muchos casos -> se acerca al error observado.
    memoria["peso_casos"] = (
        memoria["casos"] / (memoria["casos"] + SHRINK_CASOS)
    )

    # Consistencia: penaliza patrones con errores muy dispersos.
    memoria["consistencia"] = (
        1.0
        / (
            1.0
            + (
                memoria["desvio_error"]
                / (
                    memoria["error_medio"].abs() + 1.0
                )
            )
        )
    )

    memoria["correccion"] = (
        memoria["error_medio"]
        * memoria["peso_casos"]
        * memoria["consistencia"]
    ).clip(
        lower=-MAX_CORRECCION,
        upper=MAX_CORRECCION,
    )

    _guardar_memoria(memoria)

    return memoria


def aplicar_correccion(candidatos, fecha_objetivo):
    """
    Aplica memoria creada únicamente con fechas anteriores.

    La corrección se calcula antes de seleccionar los equipos.
    La predicción base queda guardada en 'prediccion_base'.
    """
    df = candidatos.copy()

    df["prediccion_base"] = pd.to_numeric(
        df["score_seleccion"],
        errors="coerce",
    )

    df["correccion_aprendizaje"] = 0.0
    df["aprendizaje_casos"] = 0
    df["aprendizaje_patrones"] = ""

    memoria = _leer_memoria()

    if memoria.empty:
        df["prediccion_final"] = df["prediccion_base"]
        return df

    # Seguridad anti-leakage:
    # una memoria que accidentalmente contenga una fecha futura no puede
    # influir en una fecha anterior.
    memoria = memoria[
        pd.to_numeric(
            memoria["fecha_maxima"],
            errors="coerce",
        ).fillna(-1)
        < int(fecha_objetivo)
    ].copy()

    if memoria.empty:
        df["prediccion_final"] = df["prediccion_base"]
        return df

    for idx, fila in df.iterrows():
        correcciones = []
        casos_total = 0
        patrones = []

        for tipo, clave in construir_patrones(fila):
            m = memoria[
                (memoria["patron_tipo"] == tipo)
                & (memoria["patron"] == clave)
                & (pd.to_numeric(memoria["casos"], errors="coerce") >= MIN_CASOS)
            ]

            if m.empty:
                continue

            registro = m.iloc[0]
            corr = _float(registro.get("correccion"), 0.0)
            casos = int(_float(registro.get("casos"), 0))

            if not np.isfinite(corr) or corr == 0:
                continue

            correcciones.append((corr, max(casos, 1)))
            casos_total += casos
            patrones.append(f"{tipo}:{clave}")

        if correcciones:
            # Los patrones más específicos tienen más peso, pero no se
            # permite que una sola regla domine completamente.
            pesos = np.array([c for _, c in correcciones], dtype=float)
            valores = np.array([v for v, _ in correcciones], dtype=float)
            peso_rel = np.sqrt(pesos)
            correccion = float(
                np.average(valores, weights=peso_rel)
            )
            correccion = float(
                np.clip(correccion, -MAX_CORRECCION, MAX_CORRECCION)
            )

            df.at[idx, "correccion_aprendizaje"] = correccion
            df.at[idx, "aprendizaje_casos"] = casos_total
            df.at[idx, "aprendizaje_patrones"] = " || ".join(patrones)

    df["prediccion_final"] = (
        df["prediccion_base"]
        + df["correccion_aprendizaje"]
    )

    # Nunca permitimos una predicción negativa.
    df["prediccion_final"] = df["prediccion_final"].clip(lower=0.0)

    return df


def main():
    import sys

    if len(sys.argv) != 3 or sys.argv[1] != "actualizar":
        raise SystemExit(
            "Uso: python aprendizaje_fecha.py actualizar <numero_fecha>"
        )

    registrar_resultados_fecha(int(sys.argv[2]))


if __name__ == "__main__":
    main()
