import pandas as pd
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.dimensions import ColumnDimension

INPUT = Path("datos/dataset_winning_pitchapi.csv")
OUTPUT_CSV = Path("datos/rankings_jugadores.csv")
OUTPUT_XLSX = Path("datos/rankings_jugadores.xlsx")

MIN_MINUTES = 450

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

    faltantes = [
        x for x, c in {
            "player_id": col_player,
            "nombre": col_name,
            "posición": col_pos,
            "minutos": col_minutes,
        }.items()
        if c is None
    ]

    if faltantes:
        raise ValueError("Faltan columnas obligatorias: " + ", ".join(faltantes))

    df = df.copy()
    df[col_minutes] = pd.to_numeric(df[col_minutes], errors="coerce").fillna(0)

    for met in METRICAS.values():
        if met["col"] not in df.columns:
            raise ValueError(f"Falta la métrica '{met['col']}' en el dataset.")
        df[met["col"]] = pd.to_numeric(df[met["col"]], errors="coerce").fillna(0)

    return df, col_player, col_name, col_pos, col_minutes


def generar_ranking(df, metrica, col_player, col_name, col_pos, col_minutes, posicion=None):
    cfg = METRICAS[metrica]
    trabajo = df.copy()

    if posicion is not None:
        trabajo = trabajo[
            trabajo[col_pos].astype(str).str.upper() == posicion
        ].copy()

    agrupado = (
        trabajo.groupby([col_player, col_name, col_pos], as_index=False)
        .agg(
            minutos=(col_minutes, "sum"),
            total=(cfg["col"], "sum"),
        )
    )

    agrupado = agrupado[agrupado["minutos"] >= MIN_MINUTES].copy()
    agrupado["por_90"] = agrupado["total"] / agrupado["minutos"] * 90

    agrupado = agrupado.sort_values(
        ["por_90", "total", "minutos"],
        ascending=[False, False, False],
    ).head(5).copy()

    agrupado.insert(0, "ranking", range(1, len(agrupado) + 1))
    agrupado["metrica"] = metrica
    agrupado["grupo"] = "GENERAL" if posicion is None else posicion

    return agrupado[
        ["metrica", "grupo", "ranking", col_player, col_name, col_pos,
         "minutos", "total", "por_90"]
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

    # Paleta sobria y muy contrastada.
    azul = "001E5F"
    azul_claro = "D9E7F7"
    azul_medio = "B8CCE4"
    gris = "F2F2F2"
    blanco = "FFFFFF"
    negro = "111111"
    verde = "E2F0D9"
    dorado = "FFF2CC"

    borde_fino = Side(style="thin", color="A6A6A6")
    borde_grueso = Side(style="medium", color="001E5F")
    borde_bloque = Border(
        left=borde_grueso,
        right=borde_grueso,
        top=borde_fino,
        bottom=borde_fino,
    )

    # Título.
    ws.merge_cells("A1:I1")
    ws["A1"] = "WINNING AI — RANKINGS DE MÉTRICAS"
    ws["A1"].font = Font(bold=True, size=18, color=blanco)
    ws["A1"].fill = PatternFill("solid", fgColor=azul)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:I2")
    ws["A2"] = (
        f"Top 5 GENERAL y Top 5 por posición | Mínimo: {MIN_MINUTES} minutos | "
        "Ranking principal: rendimiento por 90"
    )
    ws["A2"].font = Font(italic=True, size=10, color="404040")
    ws["A2"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 22

    headers = [
        "Puesto", "Jugador", "Posición", "Minutos",
        "Total", "Por 90", "Grupo", "Métrica", "ID jugador"
    ]

    fila = 4

    for metrica, cfg in METRICAS.items():
        # Separación clara entre métricas.
        if fila > 4:
            fila += 2

        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=9)
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
                top=borde_grueso,
                bottom=borde_grueso,
                left=borde_fino,
                right=borde_fino,
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
                    r["position"],
                    int(r["minutos"]),
                    float(r["total"]),
                    float(r["por_90"]),
                    grupo,
                    cfg["nombre"],
                    r["player_id"],
                ]

                for col, valor in enumerate(valores, 1):
                    c = ws.cell(fila, col, valor)
                    c.border = borde_bloque
                    c.alignment = Alignment(
                        horizontal="left" if col == 2 else "center",
                        vertical="center",
                    )

                    if grupo == "GENERAL":
                        c.fill = PatternFill("solid", fgColor=verde)
                    elif grupo in ("ARQ", "DEF", "VOL", "DEL"):
                        c.fill = PatternFill("solid", fgColor=gris)

                    if col == 1:
                        c.font = Font(bold=True)
                    elif col == 6:
                        c.font = Font(bold=True)

                ws.cell(fila, 6).number_format = "0.00"
                ws.cell(fila, 5).number_format = "0.00"
                fila += 1

            # Línea visual entre grupos.
            fila += 1

    # Anchos.
    anchos = {
        1: 9,
        2: 28,
        3: 12,
        4: 12,
        5: 12,
        6: 12,
        7: 14,
        8: 28,
        9: 16,
    }

    for col, ancho in anchos.items():
        ws.column_dimensions[get_column_letter(col)].width = ancho

    ws.auto_filter.ref = f"A4:I{max(4, fila - 1)}"

    # Segunda hoja: explicación.
    info = wb.create_sheet("Cómo leerlo")
    info.sheet_view.showGridLines = False
    info.column_dimensions["A"].width = 30
    info.column_dimensions["B"].width = 95

    info.merge_cells("A1:B1")
    info["A1"] = "CÓMO LEER EL RANKING"
    info["A1"].font = Font(bold=True, size=16, color=blanco)
    info["A1"].fill = PatternFill("solid", fgColor=azul)
    info["A1"].alignment = Alignment(horizontal="center")
    info.row_dimensions[1].height = 28

    explicaciones = [
        ("Ranking", "Cada métrica tiene un Top 5 GENERAL y un Top 5 separado para cada posición permitida."),
        ("Por 90", "Es la columna principal para ordenar. Normaliza la producción según 90 minutos jugados."),
        ("Total", "Cantidad acumulada de la métrica durante el período disponible."),
        ("Minutos", f"Solo entran jugadores que alcanzan al menos {MIN_MINUTES} minutos acumulados."),
        ("GENERAL", "Compara a todos los jugadores que están habilitados para esa métrica, independientemente de su posición."),
        ("Posiciones", "Los grupos DEF, VOL, DEL y ARQ respetan exactamente las posiciones configuradas para cada métrica."),
        ("Fuente", "Los datos salen de datos/dataset_winning_pitchapi.csv."),
        ("Último tercio", "Este archivo usa passes_into_final_third. No utiliza ultimo_tercio/touches_final_third."),
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
        info.row_dimensions[f].height = 34
        f += 1

    wb.save(OUTPUT_XLSX)


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"No existe {INPUT}")

    df = pd.read_csv(INPUT)

    df, col_player, col_name, col_pos, col_minutes = preparar(df)

    resultados = []

    for metrica, cfg in METRICAS.items():
        resultados.append(
            generar_ranking(
                df, metrica, col_player, col_name, col_pos, col_minutes
            )
        )

        for posicion in cfg["posiciones"]:
            resultados.append(
                generar_ranking(
                    df, metrica, col_player, col_name, col_pos, col_minutes, posicion
                )
            )

    salida = pd.concat(resultados, ignore_index=True)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    salida.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    generar_excel(salida)

    print(f"CSV generado: {OUTPUT_CSV}")
    print(f"Excel generado: {OUTPUT_XLSX}")
    print(f"Filas de ranking: {len(salida)}")
    print(f"Jugadores únicos: {df[col_player].nunique()}")
    print(f"Mínimo de minutos: {MIN_MINUTES}")
    print()
    print("Rankings generados:")

    for metrica, cfg in METRICAS.items():
        grupos = ["GENERAL", *cfg["posiciones"]]
        print(f"  {cfg['nombre']}: {', '.join(grupos)}")


if __name__ == "__main__":
    main()
