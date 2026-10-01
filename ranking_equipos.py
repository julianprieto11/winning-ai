import json
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter


# ============================================================
# RANKING DE EQUIPOS - WINNING AI
# ============================================================
# Modelo simple por BLOQUES DE PODERÍO.
#
# Hojas del Excel:
#   1. HISTORICO_GENERAL
#   2. TOP5_HISTORICO
#   3. TOP5_ULTIMOS_5
#
# Cada bloque tiene:
#   - descripción
#   - variables que SUMAN
#   - variables que RESTAN
#   - fórmula transparente
#   - resultado del bloque
#
# El puntaje de cada bloque se calcula sobre percentiles relativos
# entre los equipos del período.
#
# Fórmula:
#   PUNTAJE = 50 + Σ [peso × dirección × (percentil - 50)]
#
# dirección:
#   +1 = la variable suma poderío
#   -1 = la variable resta poderío
#
# Así, 50 es el punto central de la muestra; un valor alto de una
# variable positiva aumenta el bloque y un valor alto de una variable
# negativa lo reduce.
#
# PitchAPI = fuente principal.
# No se inventan variables que no existan en los datos.
# ============================================================

BASE = Path(__file__).resolve().parent
DATOS = BASE / "datos"
DATASET = DATOS / "dataset_winning_pitchapi.csv"
MATCHES_DIR = DATOS / "pitchapi" / "matches"

OUTPUT_XLSX = DATOS / "ranking_equipos_bloques.xlsx"
ULTIMOS_5 = 5
TOP_N = 5


ALIASES = {
    "team": ["team_name", "club", "team", "equipo"],
    "date": ["match_date", "date", "fecha", "fecha_partido"],
    "match": ["match_id", "fixture_id", "partido_id"],
    "minutes": ["minutes_played", "minutes"],
    "accurate_passes": ["accurate_passes"],
    "passes": ["passes", "total_passes", "passes_total"],
    "passes_into_final_third": ["passes_into_final_third"],
    "progressive_passes": ["progressive_passes"],
    "progressive_carries": ["progressive_carries"],
    "chances_created": ["chances_created"],
    "shots": ["shots", "total_shots"],
    "shots_on_target": ["shots_on_target"],
    "duels": ["duels", "total_duels"],
    "duels_won": ["duels_won"],
    "interceptions": ["interceptions"],
    "tackles": ["tackles"],
    "recoveries": ["recoveries"],
    "clearances": ["clearances"],
    "blocks": ["blocks"],
    "take_ons_won": ["take_ons_won"],
    "assists": ["assists"],
    "goals": ["goals"],
    "possession": ["possession", "possession_percentage"],
}


# ============================================================
# BLOQUES
# ============================================================

BLOCKS = [
    {
        "key": "PODERIO OFENSIVO",
        "description": (
            "Mide la capacidad ofensiva general del equipo combinando producción "
            "de gol, finalización y generación de oportunidades."
        ),
        "formula_text": (
            "50 + 30% Goles/90 + 20% Tiros al arco/90 + 20% Ocasiones creadas/90 "
            "+ 10% Asistencias/90 + 10% Conducciones progresivas/90 "
            "+ 10% Regates exitosos/90, usando percentiles centrados en 50."
        ),
        "variables": [
            ("goles_p90", "Goles por 90", 0.30, +1),
            ("shots_on_target_p90", "Tiros al arco por 90", 0.20, +1),
            ("chances_created_p90", "Ocasiones creadas por 90", 0.20, +1),
            ("assists_p90", "Asistencias por 90", 0.10, +1),
            ("progressive_carries_p90", "Conducciones progresivas por 90", 0.10, +1),
            ("take_ons_won_p90", "Regates exitosos por 90", 0.10, +1),
        ],
    },
    {
        "key": "PODERIO DEFENSIVO",
        "description": (
            "Mide la capacidad del equipo para recuperar, cortar, bloquear y "
            "evitar que el rival convierta sus ataques en goles."
        ),
        "formula_text": (
            "50 + 20% Intercepciones/90 + 15% Bloqueos/90 + 15% Entradas/90 "
            "+ 15% Despejes/90 + 10% Recuperaciones/90 + 10% Duelos ganados/90 "
            "- 15% Goles recibidos/90, usando percentiles centrados en 50."
        ),
        "variables": [
            ("interceptions_p90", "Intercepciones por 90", 0.20, +1),
            ("blocks_p90", "Bloqueos por 90", 0.15, +1),
            ("tackles_p90", "Entradas / tackles por 90", 0.15, +1),
            ("clearances_p90", "Despejes por 90", 0.15, +1),
            ("recoveries_p90", "Recuperaciones por 90", 0.10, +1),
            ("duels_won_p90", "Duelos ganados por 90", 0.10, +1),
            ("goles_recibidos_p90", "Goles recibidos por 90", 0.15, -1),
        ],
    },
    {
        "key": "PODERIO TENENCIA",
        "description": (
            "Mide la capacidad del equipo para controlar la pelota y sostener "
            "la circulación mediante posesión y pase."
        ),
        "formula_text": (
            "50 + 50% Posesión + 25% Pases precisos/90 "
            "+ 25% Efectividad de pases, usando percentiles centrados en 50."
        ),
        "variables": [
            ("posesion", "Posesión (%)", 0.50, +1),
            ("accurate_passes_p90", "Pases precisos por 90", 0.25, +1),
            ("efectividad_pases", "Efectividad de pases (%)", 0.25, +1),
        ],
    },
    {
        "key": "PODERIO ÚLTIMO TERCIO",
        "description": (
            "Mide la capacidad del equipo para llevar la pelota hacia el último "
            "tercio y progresar territorialmente mediante pase y conducción."
        ),
        "formula_text": (
            "50 + 40% Pases al último tercio/90 + 25% Efectividad de pase al "
            "último tercio + 20% Pases progresivos/90 + 15% Conducciones "
            "progresivas/90, usando percentiles centrados en 50."
        ),
        "variables": [
            ("passes_into_final_third_p90", "Pases al último tercio por 90", 0.40, +1),
            ("efectividad_ultimo_tercio", "Efectividad de pase al último tercio (%)", 0.25, +1),
            ("progressive_passes_p90", "Pases progresivos por 90", 0.20, +1),
            ("progressive_carries_p90", "Conducciones progresivas por 90", 0.15, +1),
        ],
    },
]


# ============================================================
# UTILIDADES
# ============================================================

def find_col(df, names):
    for name in names:
        if name in df.columns:
            return name
    return None


def numeric(df, col):
    if col is None:
        return pd.Series(np.nan, index=df.index)
    return pd.to_numeric(df[col], errors="coerce")


def safe_div(a, b):
    a = pd.to_numeric(a, errors="coerce")
    b = pd.to_numeric(b, errors="coerce")
    return np.where(b > 0, a / b, np.nan)


def load_match_info():
    rows = []

    if not MATCHES_DIR.exists():
        return pd.DataFrame(
            columns=["match_id", "home_team", "away_team", "home_goals", "away_goals"]
        )

    for p in sorted(MATCHES_DIR.glob("*.json")):
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            m = payload.get("data", payload)

            if not isinstance(m, dict):
                continue

            home = m.get("home_team", {}) or {}
            away = m.get("away_team", {}) or {}
            match_id = str(m.get("id") or p.stem)

            def extract_score(side):
                value = m.get(f"score_{side}")
                if value is None:
                    value = m.get(f"{side}_score")
                if isinstance(value, dict):
                    value = value.get(
                        "current",
                        value.get("display", value.get("value"))
                    )
                return pd.to_numeric(value, errors="coerce")

            rows.append(
                {
                    "match_id": match_id,
                    "home_team": home.get("name", ""),
                    "away_team": away.get("name", ""),
                    "home_goals": extract_score("home"),
                    "away_goals": extract_score("away"),
                }
            )

        except Exception:
            continue

    return pd.DataFrame(rows)


def build_team_match(df, cols):
    team_col = cols["team"]
    date_col = cols["date"]
    match_col = cols["match"]
    minutes_col = cols["minutes"]

    # Suma de estadísticas de jugadores para obtener la unidad equipo-partido.
    numeric_cols = {}

    for key, col in cols.items():
        if (
            col
            and key not in {"team", "date", "match", "minutes"}
        ):
            numeric_cols[key] = col

    group_cols = [team_col, match_col, date_col]

    agg = {c: "sum" for c in numeric_cols.values()}
    agg[minutes_col] = "sum"

    tm = df.groupby(group_cols, as_index=False).agg(agg)

    tm = tm.rename(
        columns={
            team_col: "equipo",
            match_col: "match_id",
            date_col: "fecha",
            minutes_col: "minutos",
        }
    )

    # Posesión: no se suma. Si el campo está repetido a nivel jugador,
    # el promedio evita inflarlo artificialmente.
    if cols.get("possession"):
        pc = cols["possession"]
        pos = (
            df.groupby(group_cols)[pc]
            .mean()
            .reset_index(name="posesion")
        )
        pos = pos.rename(
            columns={
                team_col: "equipo",
                match_col: "match_id",
                date_col: "fecha",
            }
        )
        tm = tm.merge(
            pos,
            on=["equipo", "match_id", "fecha"],
            how="left",
        )

    matches = load_match_info()

    if not matches.empty:
        tm["match_id"] = tm["match_id"].astype(str)
        matches["match_id"] = matches["match_id"].astype(str)

        tm = tm.merge(matches, on="match_id", how="left")

        def own_score(row):
            team = str(row["equipo"]).strip()
            if team == str(row["home_team"]).strip():
                return row["home_goals"]
            if team == str(row["away_team"]).strip():
                return row["away_goals"]
            return np.nan

        def opponent_score(row):
            team = str(row["equipo"]).strip()
            if team == str(row["home_team"]).strip():
                return row["away_goals"]
            if team == str(row["away_team"]).strip():
                return row["home_goals"]
            return np.nan

        tm["goles_equipo"] = tm.apply(own_score, axis=1)
        tm["goles_recibidos"] = tm.apply(opponent_score, axis=1)

    else:
        tm["goles_equipo"] = np.nan
        tm["goles_recibidos"] = np.nan

    return tm


def add_derived_metrics(tm):
    minutes = pd.to_numeric(tm["minutos"], errors="coerce").clip(lower=0)

    raw_to_p90 = [
        "accurate_passes",
        "progressive_passes",
        "passes_into_final_third",
        "progressive_carries",
        "chances_created",
        "shots_on_target",
        "duels_won",
        "interceptions",
        "tackles",
        "recoveries",
        "clearances",
        "blocks",
        "take_ons_won",
        "assists",
        "goals",
    ]

    for raw in raw_to_p90:
        if raw in tm.columns:
            tm[raw + "_p90"] = safe_div(tm[raw] * 90, minutes)

    if "accurate_passes" in tm.columns and "passes" in tm.columns:
        tm["efectividad_pases"] = safe_div(
            tm["accurate_passes"] * 100,
            tm["passes"],
        )

    if (
        "passes_into_final_third" in tm.columns
        and "passes" in tm.columns
    ):
        tm["efectividad_ultimo_tercio"] = safe_div(
            tm["passes_into_final_third"] * 100,
            tm["passes"],
        )

    if "goles_equipo" in tm.columns:
        tm["goles_p90"] = safe_div(
            tm["goles_equipo"] * 90,
            minutes,
        )

    if "goles_recibidos" in tm.columns:
        tm["goles_recibidos_p90"] = safe_div(
            tm["goles_recibidos"] * 90,
            minutes,
        )

    return tm


def aggregate_period(team_matches):
    if team_matches.empty:
        return pd.DataFrame()

    raw_fields = [
        "accurate_passes",
        "passes",
        "progressive_passes",
        "passes_into_final_third",
        "progressive_carries",
        "chances_created",
        "shots",
        "shots_on_target",
        "duels",
        "duels_won",
        "interceptions",
        "tackles",
        "recoveries",
        "clearances",
        "blocks",
        "take_ons_won",
        "assists",
        "goals",
        "minutos",
        "goles_equipo",
        "goles_recibidos",
    ]

    raw_fields = [c for c in raw_fields if c in team_matches.columns]

    out = (
        team_matches
        .groupby("equipo", as_index=False)[raw_fields]
        .sum(min_count=1)
    )

    if "posesion" in team_matches.columns:
        pos = (
            team_matches
            .groupby("equipo")["posesion"]
            .mean()
            .reset_index()
        )
        out = out.merge(pos, on="equipo", how="left")

    minutes = pd.to_numeric(out["minutos"], errors="coerce").clip(lower=0)

    p90_fields = [
        "accurate_passes",
        "progressive_passes",
        "passes_into_final_third",
        "progressive_carries",
        "chances_created",
        "shots_on_target",
        "duels_won",
        "interceptions",
        "tackles",
        "recoveries",
        "clearances",
        "blocks",
        "take_ons_won",
        "assists",
        "goals",
    ]

    for raw in p90_fields:
        if raw in out.columns:
            out[raw + "_p90"] = safe_div(
                out[raw] * 90,
                minutes,
            )

    if "accurate_passes" in out.columns and "passes" in out.columns:
        out["efectividad_pases"] = safe_div(
            out["accurate_passes"] * 100,
            out["passes"],
        )

    if (
        "passes_into_final_third" in out.columns
        and "passes" in out.columns
    ):
        out["efectividad_ultimo_tercio"] = safe_div(
            out["passes_into_final_third"] * 100,
            out["passes"],
        )

    if "goles_equipo" in out.columns:
        out["goles_p90"] = safe_div(
            out["goles_equipo"] * 90,
            minutes,
        )

    if "goles_recibidos" in out.columns:
        out["goles_recibidos_p90"] = safe_div(
            out["goles_recibidos"] * 90,
            minutes,
        )

    return out


def make_recent(team_matches):
    if team_matches.empty:
        return pd.DataFrame()

    pieces = []

    for team, group in team_matches.groupby("equipo"):
        group = group.copy()
        group["fecha"] = pd.to_datetime(
            group["fecha"],
            errors="coerce",
        )
        group = group.sort_values(
            ["fecha", "match_id"]
        ).tail(ULTIMOS_5)

        pieces.append(group)

    return (
        pd.concat(pieces, ignore_index=True)
        if pieces
        else pd.DataFrame()
    )


# ============================================================
# CÁLCULO DE BLOQUES
# ============================================================

def percentile_0_100(series):
    values = pd.to_numeric(series, errors="coerce")

    if values.notna().sum() <= 1:
        return pd.Series(
            np.where(values.notna(), 50.0, np.nan),
            index=series.index,
        )

    # rank(pct=True) evita depender de una escala absoluta.
    return values.rank(method="average", pct=True) * 100


def calculate_block(period, block):
    result = pd.DataFrame(index=period.index)
    result["Equipo"] = period["equipo"]

    available = []

    for field, label, weight, direction in block["variables"]:
        if field not in period.columns:
            continue

        series = pd.to_numeric(period[field], errors="coerce")

        if series.notna().sum() == 0:
            continue

        pct = percentile_0_100(series)

        contribution = (
            weight
            * direction
            * (pct - 50.0)
        )

        available.append(
            {
                "field": field,
                "label": label,
                "weight": weight,
                "direction": direction,
                "series": series,
                "percentile": pct,
                "contribution": contribution,
            }
        )

    if not available:
        result["Puntaje"] = np.nan
        return result, []

    # Si alguna variable no existe, sus pesos se redistribuyen
    # proporcionalmente entre las variables realmente disponibles.
    weight_sum = sum(x["weight"] for x in available)

    contributions = []

    for item in available:
        adjusted_weight = item["weight"] / weight_sum
        contribution = (
            adjusted_weight
            * item["direction"]
            * (item["percentile"] - 50.0)
        )

        result[item["field"] + "_percentil"] = item["percentile"]
        result[item["field"] + "_aporte"] = contribution

        item = item.copy()
        item["adjusted_weight"] = adjusted_weight
        item["adjusted_contribution"] = contribution
        contributions.append(item)

    result["Puntaje"] = (
        50.0
        + sum(item["adjusted_contribution"] for item in contributions)
    )

    result["Puntaje"] = result["Puntaje"].clip(0, 100)

    return result, contributions


def calculate_all_blocks(period):
    blocks_data = {}

    for block in BLOCKS:
        calculated, components = calculate_block(
            period,
            block,
        )
        blocks_data[block["key"]] = {
            "data": calculated,
            "components": components,
        }

    return blocks_data


# ============================================================
# DESCRIPCIONES Y JUSTIFICACIONES
# ============================================================

def available_variables_text(components):
    if not components:
        return "No hay variables disponibles en los datos actuales."

    parts = []

    for item in components:
        sign = "SUMA" if item["direction"] > 0 else "RESTA"
        weight = item["adjusted_weight"] * 100
        parts.append(
            f'{item["label"]} ({sign}, peso {weight:.0f}%)'
        )

    return " | ".join(parts)


def block_formula_actual(components):
    if not components:
        return "Sin fórmula: no hay variables disponibles."

    parts = ["50"]

    for item in components:
        sign = "+" if item["direction"] > 0 else "-"
        weight = item["adjusted_weight"] * 100
        parts.append(
            f'{sign} {weight:.0f}% × (percentil de {item["label"]} - 50)'
        )

    return " ".join(parts)


def team_justification(team_row, components):
    phrases = []

    for item in components:
        value = team_row.get(item["field"], np.nan)
        if pd.isna(value):
            continue

        percentile = team_row.get(
            item["field"] + "_percentil",
            np.nan,
        )

        if pd.isna(percentile):
            continue

        if item["direction"] > 0:
            if percentile >= 80:
                phrases.append(
                    f'{item["label"]}: muy alto ({value:.2f})'
                )
            elif percentile >= 60:
                phrases.append(
                    f'{item["label"]}: alto ({value:.2f})'
                )
        else:
            if percentile <= 20:
                phrases.append(
                    f'{item["label"]}: muy favorable por ser bajo ({value:.2f})'
                )
            elif percentile <= 40:
                phrases.append(
                    f'{item["label"]}: favorable por ser bajo ({value:.2f})'
                )
            elif percentile >= 80:
                phrases.append(
                    f'{item["label"]}: penaliza por ser alto ({value:.2f})'
                )

    if not phrases:
        return (
            "Integra las variables disponibles del bloque; su posición TOP "
            "surge del resultado combinado y no de una sola estadística."
        )

    return "; ".join(phrases) + "."


# ============================================================
# EXCEL
# ============================================================

NAVY = "001E5F"
LIGHT = "D9E6F7"
MID = "B4C7E7"
WHITE = "FFFFFF"
DARK = "111111"


def set_title(ws, row, title):
    ws.merge_cells(
        start_row=row,
        start_column=1,
        end_row=row,
        end_column=7,
    )

    cell = ws.cell(row, 1, title)
    cell.font = Font(
        bold=True,
        size=15,
        color=WHITE,
    )
    cell.fill = PatternFill(
        "solid",
        fgColor=NAVY,
    )
    cell.alignment = Alignment(
        horizontal="left",
        vertical="center",
    )

    ws.row_dimensions[row].height = 24


def set_block_description(ws, row, block, components):
    set_title(ws, row, block["key"])

    row += 1
    ws.merge_cells(
        start_row=row,
        start_column=1,
        end_row=row,
        end_column=7,
    )
    ws.cell(
        row,
        1,
        block["description"],
    )
    ws.cell(row, 1).alignment = Alignment(
        wrap_text=True,
        vertical="top",
    )

    row += 1
    ws.cell(row, 1, "VARIABLES UTILIZADAS")
    ws.cell(row, 1).font = Font(bold=True)

    ws.merge_cells(
        start_row=row,
        start_column=2,
        end_row=row,
        end_column=7,
    )
    ws.cell(
        row,
        2,
        available_variables_text(components),
    )
    ws.cell(row, 2).alignment = Alignment(
        wrap_text=True,
        vertical="top",
    )

    row += 1
    ws.cell(row, 1, "FÓRMULA")
    ws.cell(row, 1).font = Font(bold=True)

    ws.merge_cells(
        start_row=row,
        start_column=2,
        end_row=row,
        end_column=7,
    )
    ws.cell(
        row,
        2,
        block_formula_actual(components),
    )
    ws.cell(row, 2).alignment = Alignment(
        wrap_text=True,
        vertical="top",
    )

    return row + 2


def style_table_header(ws, row, headers):
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row, col, header)
        cell.font = Font(
            bold=True,
            color=WHITE,
        )
        cell.fill = PatternFill(
            "solid",
            fgColor=NAVY,
        )
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )
        cell.border = Border(
            top=Side(style="medium"),
            bottom=Side(style="medium"),
        )


def style_table_body(ws, start_row, end_row, start_col, end_col):
    thin = Side(style="thin")

    for row in range(start_row, end_row + 1):
        for col in range(start_col, end_col + 1):
            cell = ws.cell(row, col)
            cell.border = Border(
                bottom=thin,
            )
            cell.alignment = Alignment(
                vertical="center",
                wrap_text=True,
            )


def write_general_sheet(ws, period, blocks_data, title):
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A3"

    set_title(ws, 1, title)

    row = 3

    for block in BLOCKS:
        info = blocks_data[block["key"]]
        calc = info["data"]
        components = info["components"]

        row = set_block_description(
            ws,
            row,
            block,
            components,
        )

        if calc.empty:
            row += 2
            continue

        # Tabla simple: equipo + variables usadas + puntaje.
        # Ordenamos del mejor al peor según el puntaje del bloque.
        calc = calc.sort_values(
            "Puntaje",
            ascending=False,
            na_position="last",
        ).reset_index(drop=True)

        headers = ["Equipo"]

        for item in components:
            headers.append(item["label"])

        headers.append("PUNTAJE " + block["key"])

        style_table_header(ws, row, headers)

        # Recuperamos las variables originales del período.
        merged = period.copy()
        merged = merged.set_index("equipo")

        for idx, team in enumerate(calc["Equipo"], row + 1):
            ws.cell(idx, 1, team)

            col = 2

            for item in components:
                value = merged.loc[team, item["field"]]
                ws.cell(
                    idx,
                    col,
                    value,
                )
                col += 1

            score = calc.loc[
                calc["Equipo"].eq(team),
                "Puntaje",
            ].iloc[0]

            ws.cell(
                idx,
                col,
                score,
            )

        end_row = row + len(calc)
        style_table_body(
            ws,
            row + 1,
            end_row,
            1,
            len(headers),
        )

        row = end_row + 3

    ws.auto_filter.ref = None

    widths = {
        1: 28,
        2: 22,
        3: 22,
        4: 22,
        5: 22,
        6: 22,
        7: 22,
    }

    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width


def write_top_sheet(ws, period, blocks_data, title):
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A3"

    set_title(ws, 1, title)

    row = 3

    for block in BLOCKS:
        info = blocks_data[block["key"]]
        calc = info["data"]
        components = info["components"]

        row = set_block_description(
            ws,
            row,
            block,
            components,
        )

        if calc.empty:
            row += 2
            continue

        # Se unen los datos originales para construir la justificación.
        base = period.copy().set_index("equipo")
        calc_indexed = calc.set_index("Equipo")

        ordered = (
            calc.sort_values(
                "Puntaje",
                ascending=False,
            )
            .head(TOP_N)
        )

        headers = [
            "Puesto",
            "Equipo",
            "Puntaje",
            "Por qué entra al TOP 5",
        ]

        style_table_header(ws, row, headers)

        for rank, (_, top_row) in enumerate(
            ordered.iterrows(),
            1,
        ):
            excel_row = row + rank

            team = top_row["Equipo"]
            score = top_row["Puntaje"]

            ws.cell(
                excel_row,
                1,
                rank,
            )
            ws.cell(
                excel_row,
                2,
                team,
            )
            ws.cell(
                excel_row,
                3,
                score,
            )

            # La justificación se basa en los componentes reales
            # que empujaron al equipo hacia arriba.
            combined = base.loc[[team]].copy()
            combined = combined.reset_index()
            combined = combined.rename(
                columns={"index": "Equipo"}
            )

            for item in components:
                combined[
                    item["field"] + "_percentil"
                ] = top_row.get(
                    item["field"] + "_percentil",
                    np.nan,
                )

            justification = team_justification(
                top_row,
                components,
            )

            ws.cell(
                excel_row,
                4,
                justification,
            )

        end_row = row + len(ordered)
        style_table_body(
            ws,
            row + 1,
            end_row,
            1,
            len(headers),
        )

        row = end_row + 3

    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 95


def format_workbook(wb):
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, (float, np.floating)):
                    cell.number_format = "0.00"

        # Separación visual entre bloques.
        for row in range(1, ws.max_row + 1):
            ws.row_dimensions[row].height = max(
                ws.row_dimensions[row].height or 15,
                18,
            )

        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 90)
    print("RANKING DE EQUIPOS - BLOQUES DE PODERÍO")
    print("=" * 90)

    if not DATASET.exists():
        raise FileNotFoundError(
            f"No existe {DATASET}"
        )

    df = pd.read_csv(
        DATASET,
        low_memory=False,
    )

    print(
        f"Dataset: {df.shape[0]} filas x "
        f"{df.shape[1]} columnas"
    )

    cols = {
        key: find_col(df, names)
        for key, names in ALIASES.items()
    }

    required = [
        "team",
        "date",
        "match",
        "minutes",
    ]

    missing = [
        key
        for key in required
        if not cols[key]
    ]

    if missing:
        raise ValueError(
            "Faltan columnas obligatorias: "
            + ", ".join(missing)
        )

    df[cols["date"]] = pd.to_datetime(
        df[cols["date"]],
        errors="coerce",
    )

    df[cols["minutes"]] = numeric(
        df,
        cols["minutes"],
    ).fillna(0)

    for key, col in cols.items():
        if (
            col
            and key not in {
                "team",
                "date",
                "match",
            }
        ):
            df[col] = numeric(
                df,
                col,
            )

    team_matches = build_team_match(
        df,
        cols,
    )

    team_matches = add_derived_metrics(
        team_matches,
    )

    team_matches["fecha"] = pd.to_datetime(
        team_matches["fecha"],
        errors="coerce",
    )

    team_matches = team_matches.dropna(
        subset=[
            "equipo",
            "fecha",
            "match_id",
        ]
    )

    team_matches = team_matches.sort_values(
        [
            "equipo",
            "fecha",
            "match_id",
        ]
    )

    hist = aggregate_period(
        team_matches,
    )

    recent_matches = make_recent(
        team_matches,
    )

    recent = aggregate_period(
        recent_matches,
    )

    print(
        f"Equipos histórico: "
        f"{hist['equipo'].nunique() if not hist.empty else 0}"
    )

    print(
        f"Equipos últimos 5: "
        f"{recent['equipo'].nunique() if not recent.empty else 0}"
    )

    hist_blocks = calculate_all_blocks(
        hist,
    )

    recent_blocks = calculate_all_blocks(
        recent,
    )

    # CSV resumido por bloques.
    hist_csv = pd.DataFrame(
        {"Equipo": hist["equipo"]}
    )

    recent_csv = pd.DataFrame(
        {"Equipo": recent["equipo"]}
    )

    for block in BLOCKS:
        key = block["key"]

        hist_csv[key] = hist_blocks[key]["data"]["Puntaje"].values
        recent_csv[key] = recent_blocks[key]["data"]["Puntaje"].values

    hist_csv.to_csv(
        DATOS / "ranking_equipos_bloques_historico.csv",
        index=False,
        encoding="utf-8-sig",
    )

    recent_csv.to_csv(
        DATOS / "ranking_equipos_bloques_ultimos_5.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # Excel final: solo las 3 hojas que pediste.
    wb = Workbook()
    wb.remove(wb.active)

    ws_hist = wb.create_sheet(
        "HISTORICO_GENERAL"
    )
    ws_top_hist = wb.create_sheet(
        "TOP5_HISTORICO"
    )
    ws_top_recent = wb.create_sheet(
        "TOP5_ULTIMOS_5"
    )

    write_general_sheet(
        ws_hist,
        hist,
        hist_blocks,
        "HISTÓRICO GENERAL - PODERÍO DE EQUIPOS",
    )

    write_top_sheet(
        ws_top_hist,
        hist,
        hist_blocks,
        "TOP 5 HISTÓRICO POR BLOQUE",
    )

    write_top_sheet(
        ws_top_recent,
        recent,
        recent_blocks,
        "TOP 5 - ÚLTIMOS 5 PARTIDOS POR BLOQUE",
    )

    format_workbook(wb)

    wb.save(
        OUTPUT_XLSX
    )

    print()
    print(
        f"OK Excel: {OUTPUT_XLSX}"
    )
    print(
        "OK CSV histórico: "
        f"{DATOS / 'ranking_equipos_bloques_historico.csv'}"
    )
    print(
        "OK CSV últimos 5: "
        f"{DATOS / 'ranking_equipos_bloques_ultimos_5.csv'}"
    )
    print()
    print("BLOQUES CALCULADOS:")
    for block in BLOCKS:
        components = hist_blocks[
            block["key"]
        ]["components"]

        print(
            f"- {block['key']}: "
            f"{len(components)} variables disponibles"
        )

    print()
    print(
        "No se inventan variables: si un campo no existe "
        "en PitchAPI, no entra en el cálculo."
    )


if __name__ == "__main__":
    main()
