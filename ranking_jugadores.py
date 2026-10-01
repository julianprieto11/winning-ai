import json
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

INPUT = Path("datos/dataset_winning_pitchapi.csv")
OUTPUT_CSV = Path("datos/rankings_jugadores.csv")
OUTPUT_XLSX = Path("datos/rankings_jugadores.xlsx")
PITCHAPI_PLAYERS_DIR = Path("datos/pitchapi")
PITCHAPI_LINEUPS_DIR = Path("datos/pitchapi/lineups")

MIN_MINUTES = 450
MIN_TITULARIDADES_ULTIMOS_5 = 3
MIN_MINUTOS_ULTIMOS_5 = 9
ULTIMOS_PARTIDOS = 5

METRICAS = {
    "pases_precisos": {"nombre": "Pases precisos", "col": "accurate_passes", "posiciones": ["VOL", "DEL", "DEF"]},
    "pases_progresivos": {"nombre": "Pases progresivos", "col": "progressive_passes", "posiciones": ["VOL", "DEF", "DEL"]},
    "pases_ultimo_tercio": {"nombre": "Pases al último tercio", "col": "passes_into_final_third", "posiciones": ["VOL", "DEF", "DEL"]},
    "conducciones_progresivas": {"nombre": "Conducciones progresivas", "col": "progressive_carries", "posiciones": ["VOL", "DEL", "DEF"]},
    "ocasiones_creadas": {"nombre": "Ocasiones creadas", "col": "chances_created", "posiciones": ["DEL", "VOL"]},
    "tiros_al_arco": {"nombre": "Tiros al arco", "col": "shots_on_target", "posiciones": ["DEF", "VOL", "DEL"]},
    "duelos_ganados": {"nombre": "Duelos ganados", "col": "duels_won", "posiciones": ["DEF", "VOL", "DEL"]},
    "intercepciones": {"nombre": "Intercepciones", "col": "interceptions", "posiciones": ["DEF", "VOL"]},
    "tackles": {"nombre": "Entradas / tackles", "col": "tackles", "posiciones": ["DEF", "VOL"]},
    "recuperaciones": {"nombre": "Recuperaciones", "col": "recoveries", "posiciones": ["DEF", "VOL", "DEL"]},
    "despejes": {"nombre": "Despejes", "col": "clearances", "posiciones": ["DEF"]},
    "bloqueos": {"nombre": "Bloqueos", "col": "blocks", "posiciones": ["DEF"]},
    "regates_exitosos": {"nombre": "Regates exitosos", "col": "take_ons_won", "posiciones": ["VOL", "DEL"]},
    "centros_precisos": {"nombre": "Centros precisos", "col": "accurate_crosses", "posiciones": ["DEF", "VOL", "DEL"]},
    "balones_largos_precisos": {"nombre": "Balones largos precisos", "col": "long_balls_accurate", "posiciones": ["ARQ", "DEF", "VOL"]},
    "asistencias": {"nombre": "Asistencias", "col": "assists", "posiciones": ["DEF", "VOL", "DEL"]},
    "goles": {"nombre": "Goles", "col": "goals", "posiciones": ["DEF", "VOL", "DEL"]},
    "atajadas": {"nombre": "Atajadas", "col": "saves", "posiciones": ["ARQ"]},
}


def encontrar_columna(df, candidatos):
    for c in candidatos:
        if c in df.columns:
            return c
    return None


def preparar(df):
    col_player = encontrar_columna(df, ["player_id"])
    col_name = encontrar_columna(df, ["player_name", "nombre_jugador", "name"])
    col_pos = encontrar_columna(df, ["position", "posicion", "position_group", "perfil"])
    col_minutes = encontrar_columna(df, ["minutes_played", "minutes"])
    col_team = encontrar_columna(df, ["team_name", "club", "team", "equipo"])
    col_date = encontrar_columna(df, ["match_date", "date", "fecha", "fecha_partido"])
    col_match = encontrar_columna(df, ["match_id", "fixture_id", "partido_id"])

    faltantes = [
        x for x, c in {
            "player_id": col_player,
            "nombre": col_name,
            "posición": col_pos,
            "minutos": col_minutes,
            "club/equipo": col_team,
            "fecha": col_date,
            "partido": col_match,
        }.items()
        if c is None
    ]

    if faltantes:
        raise ValueError("Faltan columnas obligatorias: " + ", ".join(faltantes))

    df = df.copy()
    df[col_minutes] = pd.to_numeric(df[col_minutes], errors="coerce").fillna(0)
    df[col_date] = pd.to_datetime(df[col_date], errors="coerce")

    for met in METRICAS.values():
        if met["col"] not in df.columns:
            raise ValueError(f"Falta la métrica '{met['col']}' en el dataset.")
        df[met["col"]] = pd.to_numeric(df[met["col"]], errors="coerce").fillna(0)

    col_club = col_team
    return df, col_player, col_name, col_pos, col_minutes, col_club, col_team, col_date, col_match



def _cargar_lineup(match_id):
    """Carga el lineup confirmado de un partido, si existe."""
    ruta = PITCHAPI_LINEUPS_DIR / f"{match_id}_lineups.json"
    try:
        with ruta.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    if data.get("confirmed") is False:
        home_confirmed = bool(data.get("home", {}).get("confirmed"))
        away_confirmed = bool(data.get("away", {}).get("confirmed"))
        if not (home_confirmed and away_confirmed):
            return None
    return data


def _ids_lineup(lineup, club):
    """Devuelve titulares y suplentes del club a partir del lineup."""
    if not lineup:
        return set(), set()
    lado = None
    if str(lineup.get("home_team", {}).get("name", "")) == str(club):
        lado = lineup.get("home", {})
    elif str(lineup.get("away_team", {}).get("name", "")) == str(club):
        lado = lineup.get("away", {})
    if not lado:
        return set(), set()
    starters = {
        str(x.get("player_id"))
        for x in lado.get("starters", [])
        if x.get("player_id") is not None
    }
    subs = {
        str(x.get("player_id"))
        for x in lado.get("subs", [])
        if x.get("player_id") is not None
    }
    return starters, subs


def _mapa_ultimos_5(df, col_team, col_date, col_match):
    partidos = (
        df[[col_team, col_date, col_match]]
        .dropna(subset=[col_team, col_date, col_match])
        .drop_duplicates()
        .sort_values([col_team, col_date])
    )
    return {
        str(club): grupo.tail(ULTIMOS_PARTIDOS)[col_match].astype(str).tolist()
        for club, grupo in partidos.groupby(col_team)
    }


def cargar_titularidades_ultimos_5(df, col_player, col_team, col_date, col_match):
    """Cuenta titularidades reales usando /lineups, no /players."""
    ultimos = _mapa_ultimos_5(df, col_team, col_date, col_match)
    jugadores = df[[col_player, col_team]].dropna().drop_duplicates()
    resultado = {}
    cache = {}

    for _, fila in jugadores.iterrows():
        pid, club = str(fila[col_player]), str(fila[col_team])
        total = 0
        for match_id in ultimos.get(club, []):
            if match_id not in cache:
                cache[match_id] = _cargar_lineup(match_id)
            starters, _ = _ids_lineup(cache[match_id], club)
            total += int(pid in starters)
        resultado[(pid, club)] = total

    return pd.Series(resultado, dtype="int64")


def cargar_participaciones_ultimos_5(df, col_player, col_team, col_date, col_match):
    """Cuenta participación si fue titular O estuvo entre los suplentes."""
    ultimos = _mapa_ultimos_5(df, col_team, col_date, col_match)
    jugadores = df[[col_player, col_team]].dropna().drop_duplicates()
    resultado = {}
    cache = {}

    for _, fila in jugadores.iterrows():
        pid, club = str(fila[col_player]), str(fila[col_team])
        cantidad = 0
        for match_id in ultimos.get(club, []):
            if match_id not in cache:
                cache[match_id] = _cargar_lineup(match_id)
            starters, subs = _ids_lineup(cache[match_id], club)
            cantidad += int(pid in starters or pid in subs)
        resultado[(pid, club)] = cantidad

    return pd.Series(resultado, dtype="int64")


def _club_actual_por_jugador(df, col_player, col_club, col_date):
    return (
        df.sort_values([col_player, col_date])
        .dropna(subset=[col_player, col_club])
        .drop_duplicates(subset=[col_player], keep="last")
        [[col_player, col_club]]
        .rename(columns={col_club: "club_actual"})
    )


def _datos_ultimos_5_por_club(df, col_team, col_date, col_match):
    partidos = (
        df[[col_team, col_date, col_match]]
        .dropna(subset=[col_team, col_date, col_match])
        .drop_duplicates()
        .sort_values([col_team, col_date])
    )

    ultimos_por_club = {}
    for club, grupo in partidos.groupby(col_team):
        ultimos_por_club[str(club)] = grupo.tail(ULTIMOS_PARTIDOS)[col_match].astype(str).tolist()

    return ultimos_por_club


def _agregar_minutos_ultimos_5(
    df, col_player, col_club, col_match, ultimos_por_club
):
    registros = []

    for club, partidos in ultimos_por_club.items():
        bloque = df[
            (df[col_club].astype(str) == club)
            & (df[col_match].astype(str).isin(partidos))
        ]

        if bloque.empty:
            continue

        minutos = (
            bloque.groupby(col_player, as_index=False)[col_match]
            .first()
            .drop(columns=[col_match])
        )
        minutos["minutos_ultimos_5"] = (
            bloque.groupby(col_player)[
                next(c for c in [c for c in df.columns if c in ["minutes_played", "minutes"]] if c in df.columns)
            ].sum().values
        )
        minutos[col_club] = club
        registros.append(minutos)

    if not registros:
        return pd.DataFrame(columns=[col_player, col_club, "minutos_ultimos_5"])

    return pd.concat(registros, ignore_index=True)


def generar_ranking(
    df,
    metrica,
    col_player,
    col_name,
    col_pos,
    col_minutes,
    col_club,
    col_date,
    participaciones,
    posicion=None,
):
    cfg = METRICAS[metrica]
    trabajo = df.copy()

    if posicion is not None:
        trabajo = trabajo[
            trabajo[col_pos].astype(str).str.upper() == posicion
        ].copy()

    # El jugador es la unidad de identidad del ranking histórico.
    # Si cambia de club dentro de la competencia, se acumulan sus estadísticas.
    agrupado = (
        trabajo.groupby([col_player, col_name, col_pos], as_index=False)
        .agg(
            minutos=(col_minutes, "sum"),
            total=(cfg["col"], "sum"),
        )
    )

    clubes_actuales = _club_actual_por_jugador(
        trabajo, col_player, col_club, col_date
    )
    agrupado = agrupado.merge(clubes_actuales, on=col_player, how="left")

    claves_participacion = list(zip(
        agrupado[col_player].astype(str),
        agrupado["club_actual"].astype(str),
    ))
    agrupado["participaciones_ultimos_5"] = [
        int(participaciones.get(clave, 0)) for clave in claves_participacion
    ]

    # Nueva regla de actividad: además de figurar en al menos 3 de los
    # últimos 5 partidos, debe haber jugado al menos 9 minutos acumulados.
    # Estar en el banco cuenta como participación, pero no aporta minutos.
    minutos_recientes = (
        df.assign(
            _club=df[col_club].astype(str),
            _player=df[col_player].astype(str),
            _match=df["__match_id_aux"].astype(str),
        )
        if "__match_id_aux" in df.columns
        else None
    )

    # Se recibe el cálculo ya incorporado en df por main.
    recientes = (
        df.groupby([col_player, col_club], as_index=False)[col_minutes]
        .sum()
        .rename(columns={col_minutes: "_minutos_total_club"})
    )

    # El cálculo exacto de los últimos 5 se agrega en main y llega como
    # columna auxiliar para evitar mezclar partidos anteriores.
    if "__minutos_ultimos_5" in df.columns:
        recientes = (
            df.groupby([col_player, col_club], as_index=False)["__minutos_ultimos_5"]
            .max()
            .rename(columns={"__minutos_ultimos_5": "minutos_ultimos_5"})
        )
    else:
        recientes["minutos_ultimos_5"] = 0

    agrupado = agrupado.merge(
        recientes[[col_player, col_club, "minutos_ultimos_5"]].rename(
            columns={col_club: "club_actual"}
        ),
        on=[col_player, "club_actual"],
        how="left",
    )
    agrupado["minutos_ultimos_5"] = agrupado["minutos_ultimos_5"].fillna(0)

    agrupado = agrupado[
        (agrupado["minutos"] >= MIN_MINUTES)
        & (agrupado["participaciones_ultimos_5"] >= MIN_TITULARIDADES_ULTIMOS_5)
        & (agrupado["minutos_ultimos_5"] >= MIN_MINUTOS_ULTIMOS_5)
    ].copy()

    agrupado["por_90"] = agrupado["total"] / agrupado["minutos"] * 90

    agrupado = agrupado.sort_values(
        ["por_90", "total", "minutos"],
        ascending=[False, False, False],
    ).head(5).copy()

    agrupado.insert(0, "ranking", range(1, len(agrupado) + 1))
    agrupado["metrica"] = metrica
    agrupado["grupo"] = "GENERAL" if posicion is None else posicion

    salida = agrupado[
        [
            "metrica", "grupo", "ranking", col_player, col_name, "club_actual",
            col_pos, "minutos", "total", "por_90",
            "participaciones_ultimos_5", "minutos_ultimos_5"
        ]
    ].copy()

    return salida.rename(
        columns={
            col_player: "player_id",
            col_name: "player_name",
            "club_actual": "club",
            col_pos: "position",
        }
    )


def generar_ranking_ultimos_5(
    df_ultimos, metrica, col_player, col_name, col_pos, col_minutes,
    col_club, col_date, titularidades, posicion=None
):
    cfg = METRICAS[metrica]
    trabajo = df_ultimos.copy()

    if posicion is not None:
        trabajo = trabajo[
            trabajo[col_pos].astype(str).str.upper() == posicion
        ].copy()

    agrupado = (
        trabajo.groupby([col_player, col_name, col_pos, col_club], as_index=False)
        .agg(
            minutos_ultimos_5=(col_minutes, "sum"),
            total_ultimos_5=(cfg["col"], "sum"),
        )
    )

    agrupado["titularidades_ultimos_5"] = [
        int(titularidades.get((str(pid), str(club)), 0))
        for pid, club in zip(agrupado[col_player], agrupado[col_club])
    ]
    agrupado = agrupado[
        (agrupado["minutos_ultimos_5"] >= MIN_MINUTOS_ULTIMOS_5)
        & (agrupado["titularidades_ultimos_5"] >= MIN_TITULARIDADES_ULTIMOS_5)
    ].copy()

    agrupado["por_90_ultimos_5"] = (
        agrupado["total_ultimos_5"]
        / agrupado["minutos_ultimos_5"]
        * 90
    )

    agrupado = agrupado.sort_values(
        ["por_90_ultimos_5", "total_ultimos_5", "minutos_ultimos_5"],
        ascending=[False, False, False],
    ).head(5).copy()

    agrupado.insert(0, "ranking", range(1, len(agrupado) + 1))
    agrupado["metrica"] = metrica
    agrupado["grupo"] = "GENERAL" if posicion is None else posicion

    salida = agrupado[
        [
            "metrica", "grupo", "ranking", col_player, col_name, col_club,
            col_pos, "minutos_ultimos_5", "total_ultimos_5",
            "por_90_ultimos_5", "titularidades_ultimos_5"
        ]
    ].copy()

    return salida.rename(
        columns={
            col_player: "player_id",
            col_name: "player_name",
            col_club: "club",
            col_pos: "position",
        }
    )


def construir_df_ultimos_5(
    df, col_player, col_club, col_date, col_match, col_minutes
):
    ultimos_por_club = _datos_ultimos_5_por_club(
        df, col_club, col_date, col_match
    )

    partes = []
    for club, partidos in ultimos_por_club.items():
        bloque = df[
            (df[col_club].astype(str) == club)
            & (df[col_match].astype(str).isin(partidos))
        ].copy()
        if not bloque.empty:
            partes.append(bloque)

    if not partes:
        return df.iloc[0:0].copy()

    return pd.concat(partes, ignore_index=True)

def generar_excel(salida_historica, salida_ultimos_5):
    wb = Workbook()

    azul = "001E5F"
    azul_claro = "D9E7F7"
    gris = "F2F2F2"
    blanco = "FFFFFF"
    negro = "111111"
    verde = "E2F0D9"

    borde_fino = Side(style="thin", color="A6A6A6")
    borde_grueso = Side(style="medium", color=azul)
    borde_bloque = Border(
        left=borde_grueso,
        right=borde_grueso,
        top=borde_fino,
        bottom=borde_fino,
    )

    def preparar_hoja(ws, titulo, subtitulo, headers, salida, es_actualidad=False):
        ws.sheet_view.showGridLines = False
        ws.freeze_panes = "A4"
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.page_setup.orientation = "landscape"

        ultima_col = len(headers)
        ultima_letra = get_column_letter(ultima_col)

        ws.merge_cells(f"A1:{ultima_letra}1")
        ws["A1"] = titulo
        ws["A1"].font = Font(bold=True, size=18, color=blanco)
        ws["A1"].fill = PatternFill("solid", fgColor=azul)
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 30

        ws.merge_cells(f"A2:{ultima_letra}2")
        ws["A2"] = subtitulo
        ws["A2"].font = Font(italic=True, size=10, color="404040")
        ws["A2"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.row_dimensions[2].height = 32

        fila = 4

        for metrica, cfg in METRICAS.items():
            if fila > 4:
                fila += 2

            ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ultima_col)
            celda = ws.cell(fila, 1)
            celda.value = cfg["nombre"].upper()
            celda.font = Font(bold=True, size=13, color=blanco)
            celda.fill = PatternFill("solid", fgColor=azul)
            celda.alignment = Alignment(horizontal="left", vertical="center")
            ws.row_dimensions[fila].height = 24
            fila += 1

            for col, header in enumerate(headers, 1):
                c = ws.cell(fila, col, header)
                c.font = Font(bold=True, color=negro)
                c.fill = PatternFill("solid", fgColor=azul_claro)
                c.border = Border(
                    top=borde_grueso, bottom=borde_grueso,
                    left=borde_fino, right=borde_fino,
                )
                c.alignment = Alignment(horizontal="center", vertical="center")
            fila += 1

            bloques = ["GENERAL"] + cfg["posiciones"]
            for grupo in bloques:
                bloque = salida[
                    (salida["metrica"] == metrica)
                    & (salida["grupo"] == grupo)
                ].copy()

                if bloque.empty:
                    continue

                for _, r in bloque.iterrows():
                    if es_actualidad:
                        valores = [
                            int(r["ranking"]),
                            r["player_name"],
                            r["club"],
                            r["position"],
                            int(r["minutos_ultimos_5"]),
                            float(r["total_ultimos_5"]),
                            float(r["por_90_ultimos_5"]),
                            grupo,
                            cfg["nombre"],
                            r["player_id"],
                            int(r["titularidades_ultimos_5"]),
                        ]
                    else:
                        valores = [
                            int(r["ranking"]),
                            r["player_name"],
                            r["club"],
                            r["position"],
                            int(r["minutos"]),
                            float(r["total"]),
                            float(r["por_90"]),
                            grupo,
                            cfg["nombre"],
                            r["player_id"],
                            int(r["titularidades_ultimos_5"]),
                        ]

                    for col, valor in enumerate(valores, 1):
                        c = ws.cell(fila, col, valor)
                        c.border = borde_bloque
                        c.alignment = Alignment(
                            horizontal="left" if col in (2, 3) else "center",
                            vertical="center",
                        )
                        c.fill = PatternFill(
                            "solid", fgColor=verde if grupo == "GENERAL" else gris
                        )
                        if col in (1, 7):
                            c.font = Font(bold=True)

                    ws.cell(fila, 6).number_format = "0.00"
                    ws.cell(fila, 7).number_format = "0.00"
                    fila += 1

                fila += 1

        anchos = {
            1: 9, 2: 28, 3: 24, 4: 12, 5: 18, 6: 16,
            7: 18, 8: 14, 9: 28, 10: 16, 11: 18,
        }
        for col, ancho in anchos.items():
            ws.column_dimensions[get_column_letter(col)].width = ancho

        ws.auto_filter.ref = f"A4:{ultima_letra}{max(4, fila - 1)}"

    ws = wb.active
    ws.title = "TOP 5 Rankings"
    preparar_hoja(
        ws,
        "WINNING AI — RANKINGS DE MÉTRICAS",
        f"Top 5 GENERAL y Top 5 por posición | Histórico | Mínimo: {MIN_MINUTES} minutos | "
        f"mínimo {MIN_TITULARIDADES_ULTIMOS_5} participaciones en los últimos {ULTIMOS_PARTIDOS} partidos | "
        f"mínimo {MIN_MINUTOS_ULTIMOS_5} minutos jugados en esos últimos {ULTIMOS_PARTIDOS} partidos | Ranking por 90",
        [
            "Puesto", "Jugador", "Club", "Posición", "Minutos", "Total",
            "Por 90", "Grupo", "Métrica", "ID jugador", "Tit. últimos 5"
        ],
        salida_historica,
        False,
    )

    ws2 = wb.create_sheet("TOP 5 Últimos 5")
    preparar_hoja(
        ws2,
        "WINNING AI — TOP 5 ÚLTIMOS 5",
        f"Top 5 GENERAL y Top 5 por posición | Solo últimos {ULTIMOS_PARTIDOS} partidos del club actual | "
        f"Mínimo {MIN_TITULARIDADES_ULTIMOS_5} titularidades y {MIN_MINUTOS_ULTIMOS_5} minutos jugados | Ranking por 90",
        [
            "Puesto", "Jugador", "Club", "Posición", "Minutos últimos 5",
            "Total últimos 5", "Por 90 últimos 5", "Grupo", "Métrica",
            "ID jugador", "Tit. últimos 5"
        ],
        salida_ultimos_5,
        True,
    )

    info = wb.create_sheet("Cómo leerlo")
    info.sheet_view.showGridLines = False
    info.column_dimensions["A"].width = 34
    info.column_dimensions["B"].width = 105

    info.merge_cells("A1:B1")
    info["A1"] = "CÓMO LEER EL RANKING"
    info["A1"].font = Font(bold=True, size=16, color=blanco)
    info["A1"].fill = PatternFill("solid", fgColor=azul)
    info["A1"].alignment = Alignment(horizontal="center")

    explicaciones = [
        ("Ranking histórico", "La primera hoja acumula las estadísticas del período disponible y exige al menos 450 minutos acumulados."),
        ("Ranking últimos 5", "La segunda hoja calcula los mismos rankings usando exclusivamente los últimos 5 partidos del club actual del jugador."),
        ("Por 90", "Es la columna principal para ordenar. Normaliza la producción según 90 minutos jugados."),
        ("Actividad reciente", f"Para entrar en cualquiera de los rankings, el jugador debe figurar en la lista PitchAPI de al menos {MIN_TITULARIDADES_ULTIMOS_5} de los últimos {ULTIMOS_PARTIDOS} partidos de su club."),
        ("Minutos recientes", f"Además, debe haber jugado al menos {MIN_MINUTOS_ULTIMOS_5} minutos acumulados en esos últimos {ULTIMOS_PARTIDOS}. Esto evita considerar activo a alguien que solo estuvo en el banco."),
        ("Banco cuenta", "Figurar en la convocatoria/lista PitchAPI cuenta como participación, aunque el jugador no haya ingresado al campo. Los minutos jugados se evalúan por separado."),
        ("Transferencias", "En el ranking histórico, si un jugador cambia de club dentro de la misma competencia, sus estadísticas se acumulan en un único registro y se muestra su último club. En Últimos 5 se usan solamente los partidos de su club actual."),
        ("Fuente", "Las estadísticas salen de datos/dataset_winning_pitchapi.csv y la actividad reciente se verifica con datos/pitchapi/lineups/*_lineups.json."),
        ("Último tercio", "Este ranking usa passes_into_final_third. No utiliza ultimo_tercio/touches_final_third."),
    ]

    f = 3
    for titulo, texto in explicaciones:
        info.cell(f, 1, titulo)
        info.cell(f, 1).font = Font(bold=True)
        info.cell(f, 1).fill = PatternFill("solid", fgColor=azul_claro)
        info.cell(f, 1).border = Border(
            left=borde_fino, right=borde_fino, top=borde_fino, bottom=borde_fino
        )
        info.cell(f, 2, texto)
        info.cell(f, 2).alignment = Alignment(wrap_text=True, vertical="top")
        info.cell(f, 2).border = Border(
            left=borde_fino, right=borde_fino, top=borde_fino, bottom=borde_fino
        )
        info.row_dimensions[f].height = 42
        f += 1

    wb.save(OUTPUT_XLSX)

def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"No existe {INPUT}")
    if not PITCHAPI_PLAYERS_DIR.exists():
        raise FileNotFoundError(f"No existe {PITCHAPI_PLAYERS_DIR}")
    if not PITCHAPI_LINEUPS_DIR.exists():
        raise FileNotFoundError(f"No existe {PITCHAPI_LINEUPS_DIR}")

    df = pd.read_csv(INPUT)
    df, col_player, col_name, col_pos, col_minutes, col_club, col_team, col_date, col_match = preparar(df)

    # Últimos 5 partidos de cada club. La actividad se mide contra estos
    # partidos, no contra los últimos 5 que haya jugado cada futbolista.
    participaciones = cargar_participaciones_ultimos_5(
        df, col_player, col_team, col_date, col_match
    ).to_dict()
    titularidades = cargar_titularidades_ultimos_5(df, col_player, col_team, col_date, col_match).to_dict()

    df_ultimos_5 = construir_df_ultimos_5(
        df, col_player, col_team, col_date, col_match, col_minutes
    )

    # Se genera una columna auxiliar con los minutos acumulados del jugador
    # en los últimos 5 partidos de su club actual.
    df_ultimos_5_min = (
        df_ultimos_5.groupby([col_player, col_team], as_index=False)[col_minutes]
        .sum()
        .rename(columns={col_minutes: "__minutos_ultimos_5"})
    )
    df = df.merge(
        df_ultimos_5_min,
        on=[col_player, col_team],
        how="left",
    )
    df["__minutos_ultimos_5"] = df["__minutos_ultimos_5"].fillna(0)

    resultados_historicos = []
    resultados_ultimos_5 = []

    for metrica, cfg in METRICAS.items():
        resultados_historicos.append(
            generar_ranking(
                df, metrica, col_player, col_name, col_pos, col_minutes,
                col_club, col_date, participaciones
            )
        )
        resultados_ultimos_5.append(
            generar_ranking_ultimos_5(
                df_ultimos_5, metrica, col_player, col_name, col_pos,
                col_minutes, col_club, col_date, titularidades
            )
        )

        for posicion in cfg["posiciones"]:
            resultados_historicos.append(
                generar_ranking(
                    df, metrica, col_player, col_name, col_pos, col_minutes,
                    col_club, col_date, participaciones, posicion
                )
            )
            resultados_ultimos_5.append(
                generar_ranking_ultimos_5(
                    df_ultimos_5, metrica, col_player, col_name, col_pos,
                    col_minutes, col_club, col_date, titularidades, posicion
                )
            )

    salida_historica = pd.concat(resultados_historicos, ignore_index=True)
    salida_ultimos_5 = pd.concat(resultados_ultimos_5, ignore_index=True)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    salida_historica.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    output_csv_ultimos_5 = Path("datos/rankings_jugadores_ultimos_5.csv")
    salida_ultimos_5.to_csv(output_csv_ultimos_5, index=False, encoding="utf-8-sig")

    generar_excel(salida_historica, salida_ultimos_5)

    print(f"CSV histórico generado: {OUTPUT_CSV}")
    print(f"CSV últimos 5 generado: {output_csv_ultimos_5}")
    print(f"Excel generado: {OUTPUT_XLSX}")
    print(f"Filas de ranking histórico: {len(salida_historica)}")
    print(f"Filas de ranking últimos 5: {len(salida_ultimos_5)}")
    print(f"Jugadores únicos en dataset: {df[col_player].nunique()}")
    print(f"Mínimo histórico de minutos: {MIN_MINUTES}")
    print(f"Mínimo de participaciones últimos {ULTIMOS_PARTIDOS}: {MIN_TITULARIDADES_ULTIMOS_5}")
    print(f"Mínimo de minutos últimos {ULTIMOS_PARTIDOS}: {MIN_MINUTOS_ULTIMOS_5}")
    print(f"Archivos PitchAPI players: {len(list(PITCHAPI_PLAYERS_DIR.glob('*_players.json')))}")
    print()
    print("Rankings generados:")
    for metrica, cfg in METRICAS.items():
        grupos = ["GENERAL", *cfg["posiciones"]]
        print(f"  {cfg['nombre']}: {', '.join(grupos)}")


if __name__ == "__main__":
    main()
