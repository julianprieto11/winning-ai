"""
WINNING AI - MOTOR DE ANALISIS DE PARTIDOS
==========================================

Uso:
    python analizar_partidos.py --fecha 11

Genera:
    datos/analisis_partidos_fecha11.xlsx

El motor:
- toma los partidos de la Fecha solicitada desde datos/partidos/*.json
- usa los partidos terminados para medir forma reciente e histórico de localía
- calcula expectativas de goles, remates, remates al arco, posesión,
  corners y tiros libres
- calcula probabilidades 1X2 y resultados exactos más probables
- intenta identificar la zona territorial dominante
- usa candidatos_fechaN_final.csv cuando existe para informar el matchup
  de jugador más favorable
- no modifica el motor Winning ni ranking_equipos.py

IMPORTANTE:
SofaScore aparece como fuente de complemento para las métricas de partido
que están dentro de datos/partidos/*.json. PitchAPI sigue siendo la fuente
principal del proyecto para las estadísticas Winning.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter


BASE = Path(__file__).resolve().parent
DATOS = BASE / "datos"
PARTIDOS_DIR = DATOS / "partidos"

# En la Liga Profesional 2026 el Clausura comenzó el 23/07/2026.
# roundInfo.round se reinicia en 1, por lo que NO alcanza para distinguir
# Apertura y Clausura. La fecha del partido es el criterio de competencia.
CLAUSURA_INICIO = pd.Timestamp("2026-07-23")

NAVY = "001E5F"
LIGHT = "EAF1FB"
MID = "B4C7E7"
WHITE = "FFFFFF"
GREEN = "E2F0D9"
YELLOW = "FFF2CC"
RED = "FCE4D6"


def num(v):
    try:
        if v is None or v == "":
            return np.nan
        return float(v)
    except Exception:
        return np.nan


def find_event(obj):
    if isinstance(obj, dict):
        if "event" in obj and isinstance(obj["event"], dict):
            e = obj["event"]
            if "homeTeam" in e and "awayTeam" in e:
                return e
        for v in obj.values():
            found = find_event(v)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_event(v)
            if found is not None:
                return found
    return None


def find_statistics_lists(obj):
    found = []
    if isinstance(obj, dict):
        if isinstance(obj.get("statistics"), list):
            found.append(obj["statistics"])
        if isinstance(obj.get("statisticsItems"), list):
            found.append([obj])
        for v in obj.values():
            found.extend(find_statistics_lists(v))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(find_statistics_lists(v))
    return found


def extract_period_items(payload):
    """
    Devuelve las estadísticas del período ALL si existe.
    Si no existe, usa la última lista de estadísticas disponible.
    """
    candidates = find_statistics_lists(payload)
    best = None

    for seq in candidates:
        for block in seq:
            if isinstance(block, dict) and block.get("period") == "ALL":
                best = block
                break
        if best is not None:
            break

    if best is not None:
        return best.get("groups", [])

    for seq in reversed(candidates):
        for block in reversed(seq):
            if isinstance(block, dict) and isinstance(block.get("groups"), list):
                return block["groups"]

    return []


def flatten_stat_items(groups):
    out = {}
    for group in groups:
        for item in group.get("statisticsItems", []) if isinstance(group, dict) else []:
            key = item.get("key")
            if not key:
                continue
            out[key] = item
    return out


def stat_pair(stats, key):
    item = stats.get(key)
    if not item:
        return np.nan, np.nan
    return num(item.get("homeValue")), num(item.get("awayValue"))


def parse_match(path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    event = find_event(payload)
    if not event:
        return None

    home = event.get("homeTeam", {}).get("name")
    away = event.get("awayTeam", {}).get("name")
    if not home or not away:
        return None

    round_info = event.get("roundInfo", {}) or {}
    round_no = round_info.get("round")

    competencia = "Clausura" if pd.notna(date) and date >= CLAUSURA_INICIO else "Apertura"

    status = event.get("status", {}) or {}
    status_type = str(status.get("type", "")).lower()
    status_desc = str(status.get("description", "")).lower()
    finished = status_type in {"finished", "ended"} or status_desc in {"ended", "finished"}

    start_ts = event.get("startTimestamp")
    date = pd.NaT
    if start_ts:
        date = pd.to_datetime(start_ts, unit="s", errors="coerce")

    hs = event.get("homeScore", {}) or {}
    aws = event.get("awayScore", {}) or {}
    home_goals = num(hs.get("current"))
    away_goals = num(aws.get("current"))

    groups = extract_period_items(payload)
    stats = flatten_stat_items(groups)

    mapping = {
        "xg": "expectedGoals",
        "shots": "totalShotsOnGoal",
        "shots_on_target": "shotsOnGoal",
        "possession": "ballPossession",
        "corners": "cornerKicks",
        "free_kicks": "freeKicks",
        "final_third": "finalThirdEntries",
        "accurate_passes": "accuratePasses",
        "passes": "passes",
        "tackles": "totalTackle",
        "interceptions": "interceptionWon",
        "recoveries": "ballRecovery",
    }

    row = {
        "match_id": str(event.get("id") or path.stem),
        "fecha": date,
        "round": round_no,
        "competencia": competencia,
        "home": home,
        "away": away,
        "finished": finished,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "source": "SofaScore / datos/partidos",
    }

    for out_key, source_key in mapping.items():
        h, a = stat_pair(stats, source_key)
        row["home_" + out_key] = h
        row["away_" + out_key] = a

    return row


def load_matches():
    rows = []
    for path in PARTIDOS_DIR.glob("*.json"):
        row = parse_match(path)
        if row:
            rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    return df.sort_values(["fecha", "match_id"]).drop_duplicates("match_id")


def team_history(matches):
    rows = []
    for _, r in matches[matches["finished"]].iterrows():
        base = {
            "match_id": r["match_id"],
            "fecha": r["fecha"],
        }

        for side, venue in [("home", "LOCAL"), ("away", "VISITANTE")]:
            team = r[side]
            opp = r["away" if side == "home" else "home"]

            row = {
                **base,
                "equipo": team,
                "rival": opp,
                "venue": venue,
                "goles": r[f"{side}_goals"],
                "goles_recibidos": r[f'{"away" if side == "home" else "home"}_goals'],
            }

            for metric in [
                "xg", "shots", "shots_on_target", "possession",
                "corners", "free_kicks", "final_third",
                "accurate_passes", "passes", "tackles",
                "interceptions", "recoveries",
            ]:
                row[metric] = r.get(f"{side}_{metric}", np.nan)
                row[metric + "_recibido"] = r.get(
                    f'{"away" if side == "home" else "home"}_{metric}',
                    np.nan,
                )

            rows.append(row)

    return pd.DataFrame(rows)


def avg_last5(hist, team):
    g = hist[hist["equipo"] == team].sort_values(["fecha", "match_id"]).tail(5)
    return g


def mean_col(df, col, default=np.nan):
    if df.empty or col not in df:
        return default
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return float(s.mean()) if len(s) else default


def venue_history(hist, team, venue):
    return hist[(hist["equipo"] == team) & (hist["venue"] == venue)]


def blend(values, weights):
    pairs = [(v, w) for v, w in zip(values, weights) if pd.notna(v)]
    if not pairs:
        return np.nan
    total_w = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / total_w


def expected_metric(hist, team, venue, opponent, metric):
    recent = avg_last5(hist, team)
    venue_hist = venue_history(hist, team, venue)
    opp_venue = venue_history(hist, opponent, "VISITANTE" if venue == "LOCAL" else "LOCAL")

    attack_recent = mean_col(recent, metric)
    attack_venue = mean_col(venue_hist, metric)
    opp_allowed = mean_col(opp_venue, metric + "_recibido")

    # Actualidad 50%, comportamiento en esa condición 25%,
    # lo que suele permitir el rival en esa condición 25%.
    return blend(
        [attack_recent, attack_venue, opp_allowed],
        [0.50, 0.25, 0.25],
    )


def expected_possession(hist, home, away):
    hr = mean_col(avg_last5(hist, home), "possession")
    ar = mean_col(avg_last5(hist, away), "possession")
    hv = mean_col(venue_history(hist, home, "LOCAL"), "possession")
    av = mean_col(venue_history(hist, away, "VISITANTE"), "possession")

    home_raw = blend([hr, hv, 100 - av if pd.notna(av) else np.nan], [0.50, 0.25, 0.25])
    away_raw = blend([ar, av, 100 - hv if pd.notna(hv) else np.nan], [0.50, 0.25, 0.25])

    total = home_raw + away_raw if pd.notna(home_raw) and pd.notna(away_raw) else np.nan
    if pd.notna(total) and total > 0:
        return 100 * home_raw / total, 100 * away_raw / total
    return home_raw, away_raw


def poisson_pmf(k, lam):
    if not pd.notna(lam) or lam <= 0:
        return 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def score_probabilities(home_xg, away_xg, max_goals=7):
    rows = []
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson_pmf(h, home_xg) * poisson_pmf(a, away_xg)
            rows.append((h, a, p))

    df = pd.DataFrame(rows, columns=["home_goals", "away_goals", "prob"])
    total = df["prob"].sum()
    if total > 0:
        df["prob"] = df["prob"] / total
    return df.sort_values("prob", ascending=False)


def result_probabilities(home_xg, away_xg):
    grid = score_probabilities(home_xg, away_xg)
    home = grid.loc[grid.home_goals > grid.away_goals, "prob"].sum()
    draw = grid.loc[grid.home_goals == grid.away_goals, "prob"].sum()
    away = grid.loc[grid.home_goals < grid.away_goals, "prob"].sum()
    return home, draw, away


def territory_label(h, a):
    if pd.isna(h) or pd.isna(a):
        return "No hay datos suficientes"

    if h >= a * 1.25 and h >= 28:
        return "Último tercio del local"
    if a >= h * 1.25 and a >= 28:
        return "Último tercio del visitante"
    if h >= a * 1.12:
        return "Más cerca del último tercio local"
    if a >= h * 1.12:
        return "Más cerca del último tercio visitante"
    return "Partido bastante repartido por la cancha"


def simple_explanation(row):
    home = row["Local"]
    away = row["Visitante"]

    if row["Prob. local"] >= row["Prob. visitante"] + 12:
        result_phrase = f"{home} parte con una ventaja estadística clara."
    elif row["Prob. visitante"] >= row["Prob. local"] + 12:
        result_phrase = f"{away} parte con una ventaja estadística clara aun jugando afuera."
    else:
        result_phrase = "Las probabilidades están bastante parejas."

    if row["xG local"] >= row["xG visitante"] + 0.45:
        goal_phrase = f"{home} proyecta bastante más gol."
    elif row["xG visitante"] >= row["xG local"] + 0.45:
        goal_phrase = f"{away} proyecta bastante más gol."
    else:
        goal_phrase = "La producción de gol esperada es bastante pareja."

    if row["Remates al arco local"] >= row["Remates al arco visitante"] + 1.2:
        shot_phrase = f"{home} debería llegar más seguido con peligro."
    elif row["Remates al arco visitante"] >= row["Remates al arco local"] + 1.2:
        shot_phrase = f"{away} debería llegar más seguido con peligro."
    else:
        shot_phrase = "Los dos deberían tener una cantidad parecida de llegadas claras."

    return f"{result_phrase} {goal_phrase} {shot_phrase}"


def load_matchup(fecha):
    path = DATOS / f"candidatos_fecha{fecha}_final.csv"
    if not path.exists():
        return pd.DataFrame()

    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()

    needed = {"player_name", "team_name", "rival", "position", "matchup_score", "fecha_partido"}
    if not needed.issubset(df.columns):
        return pd.DataFrame()

    df["matchup_score"] = pd.to_numeric(df["matchup_score"], errors="coerce")
    df["fecha_partido"] = pd.to_datetime(df["fecha_partido"], errors="coerce")

    # Para cada partido buscamos el jugador de campo con mayor matchup_score.
    return df.sort_values("matchup_score", ascending=False)


def matchup_for_game(matchup_df, home, away):
    if matchup_df.empty:
        return None

    g = matchup_df[
        (
            (matchup_df["team_name"] == home) &
            (matchup_df["rival"] == away)
        )
        |
        (
            (matchup_df["team_name"] == away) &
            (matchup_df["rival"] == home)
        )
    ].copy()

    if g.empty:
        return None

    # Priorizamos VOL/DEL/DEF, porque el pedido es un matchup futbolístico
    # y no simplemente el arquero con mejor número.
    g["priority"] = g["position"].map({"DEL": 3, "VOL": 2, "DEF": 2, "ARQ": 1}).fillna(0)
    g = g.sort_values(["matchup_score", "priority"], ascending=False)

    r = g.iloc[0]
    return {
        "jugador": r["player_name"],
        "equipo": r["team_name"],
        "posicion": r["position"],
        "score": r["matchup_score"],
        "variables": r.get("matchup_variables_usadas", ""),
    }


def matchup_explanation(m):
    if not m:
        return "No hay archivo de candidatos/matchup para esta Fecha."
    name = m["jugador"]
    team = m["equipo"]
    score = m["score"]
    if pd.isna(score):
        return f"{name} ({team}) aparece como matchup favorable según los datos disponibles."
    return (
        f"{name} ({team}) aparece como el matchup más favorable de este partido "
        f"entre los jugadores disponibles, con un índice de {score:.2f}. "
        "El índice cruza su perfil reciente con el rival; no es una garantía de rendimiento."
    )


def make_predictions(matches, hist, fecha, matchup_df):
    games = matches[
        (matches["competencia"] == "Clausura")
        & (matches["round"].astype(str) == str(fecha))
    ].copy()
    if games.empty:
        return pd.DataFrame()

    rows = []

    for _, r in games.iterrows():
        home, away = r["home"], r["away"]

        hxg = expected_metric(hist, home, "LOCAL", away, "xg")
        axg = expected_metric(hist, away, "VISITANTE", home, "xg")

        # Si xG no está disponible, usamos goles recientes como fallback.
        if pd.isna(hxg):
            hxg = expected_metric(hist, home, "LOCAL", away, "goles")
        if pd.isna(axg):
            axg = expected_metric(hist, away, "VISITANTE", home, "goles")

        hs = expected_metric(hist, home, "LOCAL", away, "shots")
        ass = expected_metric(hist, away, "VISITANTE", home, "shots")
        hot = expected_metric(hist, home, "LOCAL", away, "shots_on_target")
        aot = expected_metric(hist, away, "VISITANTE", home, "shots_on_target")
        hc = expected_metric(hist, home, "LOCAL", away, "corners")
        ac = expected_metric(hist, away, "VISITANTE", home, "corners")
        hf = expected_metric(hist, home, "LOCAL", away, "free_kicks")
        af = expected_metric(hist, away, "VISITANTE", home, "free_kicks")
        hft = expected_metric(hist, home, "LOCAL", away, "final_third")
        aft = expected_metric(hist, away, "VISITANTE", home, "final_third")

        hp, ap = expected_possession(hist, home, away)
        ph, pd_, pa = result_probabilities(hxg, axg)

        grid = score_probabilities(hxg, axg).head(5)
        scores = " | ".join(
            f"{int(x.home_goals)}-{int(x.away_goals)} ({x.prob:.1%})"
            for _, x in grid.iterrows()
        )

        matchup = matchup_for_game(matchup_df, home, away)

        row = {
            "Fecha": fecha,
            "Local": home,
            "Visitante": away,
            "Prob. local": ph,
            "Prob. empate": pd_,
            "Prob. visitante": pa,
            "xG local": hxg,
            "xG visitante": axg,
            "Remates local": hs,
            "Remates visitante": ass,
            "Remates al arco local": hot,
            "Remates al arco visitante": aot,
            "Posesión local": hp,
            "Posesión visitante": ap,
            "Corners local": hc,
            "Corners visitante": ac,
            "Tiros libres local": hf,
            "Tiros libres visitante": af,
            "Último tercio local": hft,
            "Último tercio visitante": aft,
            "Zona esperada": territory_label(hft, aft),
            "Resultados más probables": scores,
            "Matchup favorable": matchup["jugador"] if matchup else "No disponible",
            "Equipo matchup": matchup["equipo"] if matchup else "",
            "Posición matchup": matchup["posicion"] if matchup else "",
            "Índice matchup": matchup["score"] if matchup else np.nan,
        }
        row["Explicación en criollo"] = simple_explanation(row)
        row["Explicación matchup"] = matchup_explanation(matchup)
        rows.append(row)

    return pd.DataFrame(rows)


def team_form_table(hist, teams):
    rows = []
    for team in teams:
        recent = avg_last5(hist, team)
        local = venue_history(hist, team, "LOCAL")
        away = venue_history(hist, team, "VISITANTE")

        rows.append({
            "Equipo": team,
            "Partidos últimos 5": len(recent),
            "Goles últimos 5": mean_col(recent, "goles"),
            "Goles recibidos últimos 5": mean_col(recent, "goles_recibidos"),
            "xG últimos 5": mean_col(recent, "xg"),
            "Remates últimos 5": mean_col(recent, "shots"),
            "Remates al arco últimos 5": mean_col(recent, "shots_on_target"),
            "Posesión últimos 5": mean_col(recent, "possession"),
            "Corners últimos 5": mean_col(recent, "corners"),
            "Tiros libres últimos 5": mean_col(recent, "free_kicks"),
            "Goles como local": mean_col(local, "goles"),
            "Goles como visitante": mean_col(away, "goles"),
        })
    return pd.DataFrame(rows)


def write_sheet(ws, title, df, widths=None):
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"

    ws.cell(1, 1, title)
    ws.cell(1, 1).font = Font(bold=True, size=15, color=WHITE)
    ws.cell(1, 1).fill = PatternFill("solid", fgColor=NAVY)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(1, len(df.columns)))

    if df.empty:
        ws.cell(3, 1, "No hay datos suficientes para esta sección.")
        return

    header_row = 3
    for c, col in enumerate(df.columns, 1):
        cell = ws.cell(header_row, c, col)
        cell.font = Font(bold=True, color=WHITE)
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for r_idx, (_, row) in enumerate(df.iterrows(), header_row + 1):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(r_idx, c_idx, value)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(bottom=Side(style="thin"))

    for c in range(1, len(df.columns) + 1):
        ws.column_dimensions[get_column_letter(c)].width = 22

    if widths:
        for c, width in widths.items():
            ws.column_dimensions[get_column_letter(c)].width = width

    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(df.columns))}{header_row + len(df)}"


def write_excel(pred, form, fecha, output):
    wb = Workbook()
    wb.remove(wb.active)

    ws = wb.create_sheet("RESUMEN_FECHA")
    if not pred.empty:
        summary = pred.copy()
        summary["Prob. local"] = summary["Prob. local"].map(lambda x: f"{x:.1%}")
        summary["Prob. empate"] = summary["Prob. empate"].map(lambda x: f"{x:.1%}")
        summary["Prob. visitante"] = summary["Prob. visitante"].map(lambda x: f"{x:.1%}")
        for c in [
            "xG local", "xG visitante", "Remates local", "Remates visitante",
            "Remates al arco local", "Remates al arco visitante",
            "Posesión local", "Posesión visitante", "Corners local", "Corners visitante",
            "Tiros libres local", "Tiros libres visitante",
            "Último tercio local", "Último tercio visitante", "Índice matchup",
        ]:
            if c in summary:
                summary[c] = pd.to_numeric(summary[c], errors="coerce").round(2)

    write_sheet(
        ws,
        f"ANÁLISIS DE PARTIDOS - FECHA {fecha}",
        summary,
        widths={1: 10, 2: 26, 3: 26, 4: 14, 5: 14, 6: 14, 7: 12, 8: 12,
                9: 14, 10: 14, 11: 16, 12: 16, 13: 14, 14: 14,
                15: 14, 16: 14, 17: 16, 18: 16, 19: 20, 20: 42,
                21: 25, 22: 20, 23: 16, 24: 16, 25: 65, 26: 70},
    )

    if not pred.empty:
        for r in range(4, 4 + len(pred)):
            ws.row_dimensions[r].height = 72

    ws2 = wb.create_sheet("DETALLE_PARTIDOS")
    detail_cols = [
        "Local", "Visitante", "Prob. local", "Prob. empate", "Prob. visitante",
        "xG local", "xG visitante", "Remates local", "Remates visitante",
        "Remates al arco local", "Remates al arco visitante",
        "Posesión local", "Posesión visitante", "Corners local", "Corners visitante",
        "Tiros libres local", "Tiros libres visitante", "Zona esperada",
        "Resultados más probables", "Explicación en criollo",
    ]
    detail = pred[detail_cols].copy() if not pred.empty else pd.DataFrame(columns=detail_cols)
    write_sheet(ws2, f"DETALLE FUTBOLERO - FECHA {fecha}", detail,
                widths={1: 27, 2: 27, 18: 32, 19: 55, 20: 80})
    if not detail.empty:
        for r in range(4, 4 + len(detail)):
            ws2.row_dimensions[r].height = 80

    ws3 = wb.create_sheet("MATCHUPS")
    matchup_cols = [
        "Local", "Visitante", "Matchup favorable", "Equipo matchup",
        "Posición matchup", "Índice matchup", "Explicación matchup",
    ]
    matchups = pred[matchup_cols].copy() if not pred.empty else pd.DataFrame(columns=matchup_cols)
    write_sheet(ws3, f"MATCHUP MÁS FAVORABLE - FECHA {fecha}", matchups,
                widths={1: 27, 2: 27, 3: 28, 4: 24, 5: 18, 6: 18, 7: 80})
    if not matchups.empty:
        for r in range(4, 4 + len(matchups)):
            ws3.row_dimensions[r].height = 70

    teams = sorted(set(pred["Local"]).union(set(pred["Visitante"]))) if not pred.empty else []
    ws4 = wb.create_sheet("FORMA_ULTIMOS_5")
    form_df = team_form_table(form, teams)
    write_sheet(ws4, "FORMA DE LOS EQUIPOS - ÚLTIMOS 5", form_df)

    ws5 = wb.create_sheet("METODOLOGIA")
    method = pd.DataFrame([
        ["Qué hace", "Cruza actualidad, localía/visitante, producción del rival y datos de partido para estimar cómo puede darse el encuentro."],
        ["Actualidad", "Los últimos 5 partidos tienen el mayor peso en las expectativas."],
        ["Localía", "Se mira cómo rinde cada equipo específicamente de local o visitante."],
        ["Rival", "También se considera lo que el rival suele permitir en esa condición."],
        ["Probabilidades", "Se convierten los goles esperados en una distribución de resultados mediante un modelo Poisson."],
        ["Resultados", "Se muestran los cinco marcadores exactos con mayor probabilidad dentro de la distribución calculada."],
        ["Territorio", "Se compara la llegada esperada al último tercio para indicar dónde debería concentrarse el partido."],
        ["Matchup", "Cuando existe candidatos_fechaN_final.csv, se usa su índice de matchup para buscar el cruce individual más favorable."],
        ["Fuente", "PitchAPI sigue siendo la fuente principal del proyecto. Los JSON de datos/partidos se usan como complemento para métricas de partido disponibles allí."],
        ["Importante", "Las probabilidades son estimaciones del modelo, no certezas. Si falta un dato, se deja vacío o se usa un fallback explícito."],
    ], columns=["Tema", "Explicación"])
    write_sheet(ws5, "CÓMO LEER ESTE EXCEL", method, widths={1: 28, 2: 115})
    for r in range(4, 4 + len(method)):
        ws5.row_dimensions[r].height = 45

    wb.save(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fecha", type=int, required=True, help="Número de Fecha a analizar")
    args = parser.parse_args()

    fecha = args.fecha

    print("=" * 90)
    print(f"ANÁLISIS DE PARTIDOS - CLAUSURA - FECHA {fecha}")
    print("=" * 90)

    matches = load_matches()
    if matches.empty:
        raise SystemExit("No se encontraron datos en datos/partidos.")

    hist = team_history(matches)
    if hist.empty:
        raise SystemExit("No hay partidos terminados suficientes para construir histórico.")

    matchup_df = load_matchup(fecha)

    pred = make_predictions(matches, hist, fecha, matchup_df)

    if pred.empty:
        raise SystemExit(
            f"No encontré partidos para Clausura Fecha {fecha}. "
            "Revisá roundInfo en datos/partidos."
        )

    output = DATOS / f"analisis_partidos_fecha{fecha}.xlsx"
    teams = sorted(set(pred["Local"]).union(set(pred["Visitante"])))
    form = hist

    write_excel(pred, form, fecha, output)

    print()
    print(f"Partidos encontrados: {len(pred)}")
    print(f"Excel: {output}")
    print()
    print("Secciones:")
    print("- RESUMEN_FECHA")
    print("- DETALLE_PARTIDOS")
    print("- MATCHUPS")
    print("- FORMA_ULTIMOS_5")
    print("- METODOLOGIA")
    print()
    print("El modelo no modifica el motor Winning.")


if __name__ == "__main__":
    main()
