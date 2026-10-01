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

MIN_MINUTES = 450
MIN_PARTICIPACIONES_ULTIMOS_5 = 3
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


def _ids_de_players_json(ruta):
    try:
        with ruta.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return set()

    ids = set()
    for item in payload.get("data", []):
        player = item.get("player", {})
        pid = player.get("id")
        if pid is not None:
            ids.add(str(pid))
    return ids


def cargar_participaciones_ultimos_5(df, col_player, col_team, col_date, col_match):
    # Una participación significa figurar en la lista PitchAPI del partido.
    # Por lo tanto, también cuenta haber ido al banco aunque no haya jugado.
    partidos = (
        df[[col_team, col_date, col_match]]
        .dropna(subset=[col_team, col_date, col_match])
        .drop_duplicates()
        .sort_values([col_team, col_date])
    )

    ultimos_por_club = {}
    for club, grupo in partidos.groupby(col_team):
        ultimos_por_club[str(club)] = grupo.tail(ULTIMOS_PARTIDOS)[col_match].astype(str).tolist()

    jugadores = (
        df[[col_player, col_team]]
        .dropna(subset=[col_player, col_team])
        .drop_duplicates()
        .sort_values([col_player, col_team])
    )

    resultado = {}

    # Guardamos la cantidad de participaciones por jugador y club. Después,
    # el ranking utilizará solamente el club actual del jugador.
    for _, fila in jugadores.iterrows():
        pid = str(fila[col_player])
        club = str(fila[col_team])
        ids_partidos = ultimos_por_club.get(club, [])

        cantidad = 0
        for match_id in ids_partidos:
            ruta = PITCHAPI_PLAYERS_DIR / f"{match_id}_players.json"
            if pid in _ids_de_players_json(ruta):
                cantidad += 1

        resultado[pid] = max(resultado.get(pid, 0), cantidad)

    return pd.Series(resultado, dtype="int64")


def generar_ranking(
    df,
    metrica,
    col_player,
    col_name,
    col_pos,
    col_minutes,
    col_club,
    participaciones,
    posicion=None,
):
    cfg = METRICAS[metrica]
    trabajo = df.copy()

    if posicion is not None:
        trabajo = trabajo[
            trabajo[col_pos].astype(str).str.upper() == posicion
        ].copy()

    # El jugador es la unidad de identidad del ranking, no el jugador+club.
    # Si cambia de club dentro de la misma competencia, acumulamos sus estadísticas
    # de toda la temporada para conservar un promedio representativo.
    agrupado = (
        trabajo.groupby([col_player, col_name, col_pos], as_index=False)
        .agg(
            minutos=(col_minutes, "sum"),
            total=(cfg["col"], "sum"),
        )
    )

    # El club mostrado es el último club conocido del jugador.
    clubes_actuales = (
        trabajo.sort_values([col_player, col_date])
        .dropna(subset=[col_player, col_club])
        .drop_duplicates(subset=[col_player], keep="last")
        [[col_player, col_club]]
        .rename(columns={col_club: "club_actual"})
    )
    agrupado = agrupado.merge(clubes_actuales, on=col_player, how="left")

    claves_participacion = list(zip(
        agrupado[col_player].astype(str),
        agrupado["club_actual"].astype(str),
    ))
    agrupado["participaciones_ultimos_5"] = [
        int(participaciones.get(clave, 0)) for clave in claves_participacion
    ]

    agrupado = agrupado[
        (agrupado["minutos"] >= MIN_MINUTES)
        & (agrupado["participaciones_ultimos_5"] >= MIN_PARTICIPACIONES_ULTIMOS_5)
    ].copy()

    agrupado["por_90"] = agrupado["total"] / agrupado["minutos"] * 90

    agrupado = agrupado.sort_values(
        ["por_90", "total", "minutos"],
        ascending=[False, False, False],
    ).head(5).copy()

    agrupado.insert(0, "ranking", range(1, len(agrupado) + 1))
    agrupado["metrica"] = metrica
    agrupado["grupo"] = "GENERAL" if posicion is None else posicion

    return agrupado[
        [
            "metrica", "grupo", "ranking", col_player, col_name, "club_actual",
            col_pos, "minutos", "total", "por_90", "participaciones_ultimos_5"
        ]
    ]


def generar_excel(salida):
    wb = Workbook()
    ws = wb.active
    ws.title = "TOP 5 Rankings"
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A4"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_setup.orientation = "landscape"

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

    ws.merge_cells("A1:K1")
    ws["A1"] = "WINNING AI — RANKINGS DE MÉTRICAS"
    ws["A1"].font = Font(bold=True, size=18, color=blanco)
    ws["A1"].fill = PatternFill("solid", fgColor=azul)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:K2")
    ws["A2"] = (
        f"Top 5 GENERAL y Top 5 por posición | Mínimo: {MIN_MINUTES} minutos | "
        f"mínimo {MIN_PARTICIPACIONES_ULTIMOS_5} participaciones en los últimos "
        f"{ULTIMOS_PARTIDOS} partidos | Ranking por 90"
    )
    ws["A2"].font = Font(italic=True, size=10, color="404040")
    ws["A2"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 28

    headers = [
        "Puesto", "Jugador", "Club", "Posición", "Minutos", "Total",
        "Por 90", "Grupo", "Métrica", "ID jugador", "Part. últimos 5"
    ]

    fila = 4

    for metrica, cfg in METRICAS.items():
        if fila > 4:
            fila += 2

        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=11)
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
                valores = [
                    int(r["ranking"]),
                    r["player_name"],
                    r["club_actual"],
                    r["position"],
                    int(r["minutos"]),
                    float(r["total"]),
                    float(r["por_90"]),
                    grupo,
                    cfg["nombre"],
                    r["player_id"],
                    int(r["participaciones_ultimos_5"]),
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
        1: 9, 2: 28, 3: 24, 4: 12, 5: 12, 6: 12,
        7: 12, 8: 14, 9: 28, 10: 16, 11: 18,
    }
    for col, ancho in anchos.items():
        ws.column_dimensions[get_column_letter(col)].width = ancho

    ws.auto_filter.ref = f"A4:K{max(4, fila - 1)}"

    info = wb.create_sheet("Cómo leerlo")
    info.sheet_view.showGridLines = False
    info.column_dimensions["A"].width = 32
    info.column_dimensions["B"].width = 100

    info.merge_cells("A1:B1")
    info["A1"] = "CÓMO LEER EL RANKING"
    info["A1"].font = Font(bold=True, size=16, color=blanco)
    info["A1"].fill = PatternFill("solid", fgColor=azul)
    info["A1"].alignment = Alignment(horizontal="center")

    explicaciones = [
        ("Ranking", "Cada métrica tiene un Top 5 GENERAL y un Top 5 separado para cada posición permitida."),
        ("Por 90", "Es la columna principal para ordenar. Normaliza la producción según 90 minutos jugados."),
        ("Total", "Cantidad acumulada de la métrica durante el período disponible."),
        ("Minutos", f"Solo entran jugadores con al menos {MIN_MINUTES} minutos acumulados."),
        ("Actividad reciente", f"Además, el jugador debe figurar en la lista PitchAPI de al menos {MIN_PARTICIPACIONES_ULTIMOS_5} de los últimos {ULTIMOS_PARTIDOS} partidos de su club."),
        ("Banco cuenta", "Figurar en la convocatoria/lista de jugadores cuenta como participación aunque el jugador no haya ingresado al campo."),
        ("Club", "Se muestra el último club conocido del jugador. Si cambió de club dentro de la misma competencia, sus estadísticas de toda la temporada se acumulan en un único registro."),
        ("Fuente", "Las estadísticas salen de datos/dataset_winning_pitchapi.csv y la actividad reciente se verifica con datos/pitchapi/*_players.json."),
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
        info.row_dimensions[f].height = 38
        f += 1

    wb.save(OUTPUT_XLSX)


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"No existe {INPUT}")
    if not PITCHAPI_PLAYERS_DIR.exists():
        raise FileNotFoundError(f"No existe {PITCHAPI_PLAYERS_DIR}")

    df = pd.read_csv(INPUT)
    df, col_player, col_name, col_pos, col_minutes, col_club, col_team, col_date, col_match = preparar(df)

    participaciones = cargar_participaciones_ultimos_5(
        df, col_player, col_team, col_date, col_match
    ).to_dict()

    resultados = []

    for metrica, cfg in METRICAS.items():
        resultados.append(
            generar_ranking(
                df, metrica, col_player, col_name, col_pos, col_minutes,
                col_club, participaciones
            )
        )
        for posicion in cfg["posiciones"]:
            resultados.append(
                generar_ranking(
                    df, metrica, col_player, col_name, col_pos, col_minutes,
                    col_club, participaciones, posicion
                )
            )

    salida = pd.concat(resultados, ignore_index=True)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    generar_excel(salida)

    print(f"CSV generado: {OUTPUT_CSV}")
    print(f"Excel generado: {OUTPUT_XLSX}")
    print(f"Filas de ranking: {len(salida)}")
    print(f"Jugadores únicos en dataset: {df[col_player].nunique()}")
    print(f"Mínimo de minutos: {MIN_MINUTES}")
    print(f"Mínimo de participaciones últimos {ULTIMOS_PARTIDOS}: {MIN_PARTICIPACIONES_ULTIMOS_5}")
    print(f"Archivos PitchAPI players: {len(list(PITCHAPI_PLAYERS_DIR.glob('*_players.json')))}")
    print()
    print("Rankings generados:")
    for metrica, cfg in METRICAS.items():
        grupos = ["GENERAL", *cfg["posiciones"]]
        print(f"  {cfg['nombre']}: {', '.join(grupos)}")


if __name__ == "__main__":
    main()
