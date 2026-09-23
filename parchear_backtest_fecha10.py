from pathlib import Path

PATH = Path("backtest_fecha10.py")
text = PATH.read_text(encoding="utf-8-sig")

old = '''def calcular_matchup_directo(
    player_id,
    team_id,
    rival_team_id,
    posicion,
    fecha_objetivo
):

    salida = {
        "matchup_arq": np.nan,
        "matchup_def": np.nan,
        "matchup_vol": np.nan,
        "matchup_del": np.nan,
        "matchup_score": np.nan,
        "matchup_variables_usadas": np.nan,
    }

    if contexto_matchup.empty:
        return salida

    if "date" not in contexto_matchup.columns:
        return salida

    fecha = pd.to_datetime(
        fecha_objetivo,
        errors="coerce"
    )

    if pd.isna(fecha):
        return salida

    fecha = pd.Timestamp(fecha).normalize()

    df = contexto_matchup.copy()
    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    ).dt.normalize()

    candidatos = pd.DataFrame()

    if "player_id" in df.columns:
        candidatos = df[
            (df["player_id"].astype(str) == str(player_id))
            & (df["date"] == fecha)
        ].copy()

    if candidatos.empty and "team_id" in df.columns:
        candidatos = df[
            (df["team_id"].astype(str) == str(team_id))
            & (df["date"] == fecha)
        ].copy()

    if candidatos.empty:
        return salida

    if len(candidatos) > 1 and "position" in candidatos.columns:
        posicion_norm = candidatos["position"].map(
            normalizar_posicion_matchup
        )
        filtradas = candidatos[
            posicion_norm == normalizar_posicion_matchup(posicion)
        ]
        if not filtradas.empty:
            candidatos = filtradas

    # Si existe el rival en el archivo, priorizamos coincidencia exacta.
    if len(candidatos) > 1 and "rival_team_id" in candidatos.columns:
        exactas = candidatos[
            candidatos["rival_team_id"].astype(str) == str(rival_team_id)
        ]
        if not exactas.empty:
            candidatos = exactas

    fila = candidatos.iloc[0]

    for columna in salida:
        if columna in fila.index:
            salida[columna] = fila[columna]

    return salida
'''

new = '''def calcular_matchup_directo(
    player_id,
    team_id,
    rival_team_id,
    rival_team_name,
    posicion,
    fecha_objetivo
):

    salida = {
        "matchup_arq": np.nan,
        "matchup_def": np.nan,
        "matchup_vol": np.nan,
        "matchup_del": np.nan,
        "matchup_score": np.nan,
        "matchup_variables_usadas": np.nan,
    }

    if contexto_matchup.empty:
        return salida

    if "date" not in contexto_matchup.columns:
        return salida

    fecha = pd.to_datetime(
        fecha_objetivo,
        errors="coerce"
    )

    if pd.isna(fecha):
        return salida

    # Regla anti-leakage:
    # solamente se puede usar historial estrictamente anterior
    # al partido objetivo. Para Fecha 10 esto permite utilizar
    # los registros históricos hasta 15/09/2026.
    fecha = pd.Timestamp(fecha).normalize()

    df = contexto_matchup.copy()

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    ).dt.normalize()

    # Primero identificamos al jugador. NO buscamos la fecha exacta
    # del partido objetivo porque contexto_matchup contiene historial.
    if "player_id" in df.columns:
        candidatos = df[
            df["player_id"].astype(str) == str(player_id)
        ].copy()
    elif "team_id" in df.columns:
        candidatos = df[
            df["team_id"].astype(str) == str(team_id)
        ].copy()
    else:
        return salida

    if candidatos.empty:
        return salida

    # Solo historial anterior al partido objetivo.
    candidatos = candidatos[
        candidatos["date"].notna()
        & (candidatos["date"] < fecha)
    ].copy()

    if candidatos.empty:
        return salida

    # Preferimos la misma posición cuando está disponible.
    if "position" in candidatos.columns:
        posicion_objetivo = normalizar_posicion_matchup(posicion)
        if posicion_objetivo:
            filtradas = candidatos[
                candidatos["position"].map(
                    normalizar_posicion_matchup
                ) == posicion_objetivo
            ]
            if not filtradas.empty:
                candidatos = filtradas

    # --------------------------------------------------------
    # PRIORIDAD 1: mismo rival histórico
    #
    # contexto_matchup.csv no tiene rival_team_id, pero sí
    # rival_team_name.
    # --------------------------------------------------------
    rival_objetivo = normalizar_texto(rival_team_name)

    if (
        rival_objetivo
        and "rival_team_name" in candidatos.columns
    ):
        exactas = candidatos[
            candidatos["rival_team_name"]
            .map(normalizar_texto)
            == rival_objetivo
        ].copy()

        if not exactas.empty:
            candidatos = exactas

    # --------------------------------------------------------
    # Dentro del conjunto elegido, priorizamos registros con
    # matchup_score disponible y luego el historial más reciente.
    # --------------------------------------------------------
    if "matchup_score" in candidatos.columns:
        score_numerico = pd.to_numeric(
            candidatos["matchup_score"],
            errors="coerce"
        )
        candidatos = (
            candidatos
            .assign(_matchup_score_num=score_numerico)
            .sort_values(
                ["_matchup_score_num", "date"],
                ascending=[False, False],
                na_position="last"
            )
        )
    else:
        candidatos = candidatos.sort_values(
            "date",
            ascending=False
        )

    fila = candidatos.iloc[0]

    for columna in salida:
        if columna in fila.index:
            salida[columna] = fila[columna]

    return salida
'''

if old not in text:
    raise SystemExit("No se encontró la función calcular_matchup_directo esperada.")

text = text.replace(old, new, 1)

old_call = '''        matchup = calcular_matchup_directo(
            objetivo["player_id"],
            objetivo["team_id"],
            objetivo.get("rival_team_id", ""),
            posicion,
            objetivo.get("fecha_partido", pd.NaT),
        )
'''

new_call = '''        matchup = calcular_matchup_directo(
            objetivo["player_id"],
            objetivo["team_id"],
            objetivo.get("rival_team_id", ""),
            objetivo.get("rival_team_name", rival_name),
            posicion,
            objetivo.get("fecha_partido", pd.NaT),
        )
'''

if old_call not in text:
    raise SystemExit("No se encontró la llamada a calcular_matchup_directo esperada.")

text = text.replace(old_call, new_call, 1)

old_excel = '''        "rival": "Rival",

        "es_local": "Local",
'''

new_excel = '''        "rival": "Rival",

        "es_local": "Local",

        "matchup_score": "Matchup score",

        "prediccion_modelo_c": "Predicción Modelo C",
'''

if old_excel not in text:
    raise SystemExit("No se encontró el bloque de columnas Excel esperado.")

text = text.replace(old_excel, new_excel, 1)

PATH.write_text(text, encoding="utf-8")
print("OK: backtest_fecha10.py corregido.")
