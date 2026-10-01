import json
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

# ============================================================
# RANKING DE EQUIPOS - WINNING AI
# ============================================================
# No modifica el motor funcional. Solo construye un archivo de
# análisis estadístico a partir del dataset existente.
#
# Hojas:
#   1 HISTORICO
#   2 ULTIMOS_5
#   3 TOPS_HISTORICO
#   4 TOPS_ULTIMOS_5
#   5 MATCHUP
#   6 DICCIONARIO_VARIABLES
#
# PitchAPI = fuente principal.
# SofaScore solo queda preparado como complemento futuro.
# ============================================================

BASE = Path(__file__).resolve().parent
DATOS = BASE / "datos"
DATASET = DATOS / "dataset_winning_pitchapi.csv"
MATCHES_DIR = DATOS / "pitchapi" / "matches"
EVENTS_DIR = DATOS / "pitchapi"

OUTPUT_XLSX = DATOS / "ranking_equipos.xlsx"
OUTPUT_CSV = DATOS / "ranking_equipos.csv"

ULTIMOS_5 = 5
TOP_N = 5

# Estadísticas directas que ya usamos en jugadores.
BASE_METRICS = {
    "pases_precisos": ("Pases precisos", "accurate_passes", "CREACION"),
    "pases_progresivos": ("Pases progresivos", "progressive_passes", "CREACION"),
    "pases_ultimo_tercio": ("Pases al último tercio", "passes_into_final_third", "CREACION"),
    "conducciones_progresivas": ("Conducciones progresivas", "progressive_carries", "CREACION"),
    "ocasiones_creadas": ("Ocasiones creadas", "chances_created", "OPORTUNIDADES"),
    "tiros_al_arco": ("Tiros al arco", "shots_on_target", "OPORTUNIDADES"),
    "duelos_ganados": ("Duelos ganados", "duels_won", "DUELOS"),
    "intercepciones": ("Intercepciones", "interceptions", "DEFENSA"),
    "tackles": ("Entradas / tackles", "tackles", "DEFENSA"),
    "recuperaciones": ("Recuperaciones", "recoveries", "RECUPERACION"),
    "despejes": ("Despejes", "clearances", "DEFENSA"),
    "bloqueos": ("Bloqueos", "blocks", "DEFENSA"),
    "regates_exitosos": ("Regates exitosos", "take_ons_won", "ATAQUE"),
    "centros_precisos": ("Centros precisos", "accurate_crosses", "ATAQUE"),
    "balones_largos_precisos": ("Balones largos precisos", "long_balls_accurate", "CREACION"),
    "asistencias": ("Asistencias", "assists", "ATAQUE"),
    "goles": ("Goles", "goals", "ATAQUE"),
    "atajadas": ("Atajadas", "saves", "DEFENSA"),
}

ALIASES = {
    "player_id": ["player_id"],
    "player_name": ["player_name", "nombre_jugador", "name"],
    "team": ["team_name", "club", "team", "equipo"],
    "date": ["match_date", "date", "fecha", "fecha_partido"],
    "match": ["match_id", "fixture_id", "partido_id"],
    "minutes": ["minutes_played", "minutes"],
    "position": ["position", "posicion", "position_group", "perfil"],
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
    "take_ons": ["take_ons", "dribbles"],
    "take_ons_won": ["take_ons_won"],
    "accurate_crosses": ["accurate_crosses"],
    "long_balls_accurate": ["long_balls_accurate"],
    "assists": ["assists"],
    "goals": ["goals"],
    "saves": ["saves"],
    "possession": ["possession", "possession_percentage"],
    "fouls": ["fouls", "fouls_committed"],
    "yellow": ["yellow_cards", "yellowcards", "yellow"],
    "red": ["red_cards", "redcards", "red"],
}

def find_col(df, names):
    for name in names:
        if name in df.columns:
            return name
    return None

def numeric(df, col):
    if col is None:
        return pd.Series(0.0, index=df.index)
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)

def safe_div(a, b):
    a = pd.to_numeric(a, errors="coerce").fillna(0.0)
    b = pd.to_numeric(b, errors="coerce").fillna(0.0)
    return np.where(b > 0, a / b, np.nan)

def normalize_team(x):
    return str(x).strip()

def load_match_info():
    rows = []
    if not MATCHES_DIR.exists():
        return pd.DataFrame(columns=["match_id", "home_team", "away_team", "home_goals", "away_goals"])

    for p in sorted(MATCHES_DIR.glob("*.json")):
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            m = payload.get("data", payload)
            if not isinstance(m, dict):
                continue
            home = m.get("home_team", {}) or {}
            away = m.get("away_team", {}) or {}
            mid = str(m.get("id") or p.stem)
            def extract_score(side):
                value = m.get(f"score_{side}")
                if value is None:
                    value = m.get(f"{side}_score")
                if isinstance(value, dict):
                    value = value.get("current", value.get("display", value.get("value")))
                return pd.to_numeric(value, errors="coerce")

            rows.append({
                "match_id": mid,
                "home_team": home.get("name", ""),
                "away_team": away.get("name", ""),
                "home_goals": extract_score("home"),
                "away_goals": extract_score("away"),
            })
        except Exception:
            continue
    return pd.DataFrame(rows)

def build_team_match(df, cols):
    team_col, date_col, match_col, min_col = cols["team"], cols["date"], cols["match"], cols["minutes"]

    # La unidad base es equipo-partido. Los stats de jugadores se suman.
    numeric_cols = {}
    for key, col in cols.items():
        if col and key not in {"team", "date", "match", "minutes", "player_id", "player_name", "position"}:
            numeric_cols[key] = col

    group_cols = [team_col, match_col, date_col]
    agg = {c: "sum" for c in numeric_cols.values()}
    agg[min_col] = "sum"

    tm = df.groupby(group_cols, as_index=False).agg(agg)
    tm = tm.rename(columns={team_col: "equipo", match_col: "match_id", date_col: "fecha", min_col: "minutos"})

    # Si existe posesión a nivel jugador, no se suma: usamos promedio ponderado
    # únicamente cuando el campo existe; de lo contrario queda ausente.
    if cols.get("possession"):
        pc = cols["possession"]
        vals = df.groupby(group_cols)[pc].mean().reset_index(name="posesion")
        vals = vals.rename(columns={team_col: "equipo", match_col: "match_id", date_col: "fecha"})
        tm = tm.merge(vals, on=["equipo", "match_id", "fecha"], how="left")

    matches = load_match_info()
    if not matches.empty:
        tm["match_id"] = tm["match_id"].astype(str)
        matches["match_id"] = matches["match_id"].astype(str)
        tm = tm.merge(matches, on="match_id", how="left")

        def own_score(r):
            if str(r["equipo"]).strip() == str(r["home_team"]).strip():
                return r["home_goals"]
            if str(r["equipo"]).strip() == str(r["away_team"]).strip():
                return r["away_goals"]
            return np.nan

        def opp_score(r):
            if str(r["equipo"]).strip() == str(r["home_team"]).strip():
                return r["away_goals"]
            if str(r["equipo"]).strip() == str(r["away_team"]).strip():
                return r["home_goals"]
            return np.nan

        tm["goles_equipo"] = tm.apply(own_score, axis=1)
        tm["goles_recibidos"] = tm.apply(opp_score, axis=1)
        tm["local"] = tm.apply(
            lambda r: 1 if str(r["equipo"]).strip() == str(r["home_team"]).strip() else 0,
            axis=1,
        )
        tm["rival"] = np.where(
            tm["local"].eq(1), tm["away_team"], tm["home_team"]
        )
    else:
        tm["goles_equipo"] = np.nan
        tm["goles_recibidos"] = np.nan
        tm["local"] = np.nan
        tm["rival"] = ""

    return tm

def add_derived_metrics(tm, cols):
    minutes = tm["minutos"].clip(lower=0)

    # Métricas por 90: evitamos que un equipo con más minutos acumulados
    # aparezca arriba solo por volumen.

    for metric_key, (_, raw_col, _) in BASE_METRICS.items():
        if raw_col in tm.columns:
            tm[metric_key] = tm[raw_col]
            tm[metric_key + "_p90"] = safe_div(tm[raw_col] * 90, minutes)

    if "accurate_passes" in tm.columns and "passes" in tm.columns:
        tm["efectividad_pases"] = safe_div(tm["accurate_passes"] * 100, tm["passes"])
    if "passes_into_final_third" in tm.columns and "passes" in tm.columns:
        tm["efectividad_ultimo_tercio"] = safe_div(
            tm["passes_into_final_third"] * 100, tm["passes"]
        )
    if "duels_won" in tm.columns and "duels" in tm.columns:
        tm["efectividad_duelos"] = safe_div(tm["duels_won"] * 100, tm["duels"])
    if "shots_on_target" in tm.columns and "shots" in tm.columns:
        tm["efectividad_tiros_al_arco"] = safe_div(tm["shots_on_target"] * 100, tm["shots"])
    if "goals" in tm.columns and "shots_on_target" in tm.columns:
        tm["conversion_tiros_arco"] = safe_div(tm["goals"] * 100, tm["shots_on_target"])
    if "assists" in tm.columns and "chances_created" in tm.columns:
        tm["asistencias_por_ocasion"] = safe_div(tm["assists"] * 100, tm["chances_created"])

    if "goles_equipo" in tm.columns:
        tm["goles_p90"] = safe_div(tm["goles_equipo"] * 90, minutes)
    if "goles_recibidos" in tm.columns:
        tm["goles_recibidos_p90"] = safe_div(tm["goles_recibidos"] * 90, minutes)

    if "goles_equipo" in tm.columns and "goles_recibidos" in tm.columns:
        tm["balance_goles"] = tm["goles_equipo"] - tm["goles_recibidos"]

    if "recuperaciones" in tm.columns:
        tm["recuperaciones_p90"] = safe_div(tm["recuperaciones"] * 90, minutes)

    # Índices simples, transparentes: promedio de percentiles de variables
    # disponibles. No se inventan valores para campos ausentes.
    groups = {
        "indice_creacion": ["pases_progresivos_p90", "pases_ultimo_tercio_p90", "conducciones_progresivas_p90", "efectividad_ultimo_tercio"],
        "indice_posesion": ["posesion", "pases_ultimo_tercio_p90"],
        "indice_oportunidades": ["ocasiones_creadas_p90", "tiros_al_arco_p90", "chances_created_p90"],
        "indice_ataque": ["goles_p90", "asistencias_p90", "tiros_al_arco_p90", "ocasiones_creadas_p90"],
        "indice_defensa": ["intercepciones_p90", "bloqueos_p90", "tackles_p90", "despejes_p90", "goles_recibidos_p90"],
        "indice_recuperacion": ["recuperaciones_p90", "intercepciones_p90", "tackles_p90"],
        "indice_duelos": ["efectividad_duelos", "duelos_ganados_p90"],
        "indice_eficiencia": ["efectividad_pases", "efectividad_duelos", "conversion_tiros_arco"],
    }

    for idx_name, fields in groups.items():
        available = [f for f in fields if f in tm.columns]
        if not available:
            continue
        ranks = []
        for f in available:
            s = pd.to_numeric(tm[f], errors="coerce")
            # Para goles recibidos menos es mejor.
            if f == "goles_recibidos_p90":
                ranks.append(s.rank(pct=True, ascending=False))
            else:
                ranks.append(s.rank(pct=True))
        tm[idx_name] = pd.concat(ranks, axis=1).mean(axis=1) * 100

    return tm

def aggregate_period(tm, matches):
    if tm.empty:
        return pd.DataFrame()

    # Solo agregamos métricas de volumen reales. Las métricas por 90,
    # porcentajes e índices se recalculan después sobre el período completo.
    raw_cols = []
    for raw in ["passes", "duels", "shots"]:
        if raw in tm.columns:
            raw_cols.append(raw)
    for _, raw, _ in BASE_METRICS.values():
        if raw in tm.columns and raw not in raw_cols:
            raw_cols.append(raw)

    for c in ["minutos", "goles_equipo", "goles_recibidos"]:
        if c in tm.columns and c not in raw_cols:
            raw_cols.append(c)

    out = tm.groupby("equipo", as_index=False)[raw_cols].sum()

    if "posesion" in tm.columns:
        pos = tm.groupby("equipo")["posesion"].mean().reset_index()
        out = out.merge(pos, on="equipo", how="left")

    mins = out["minutos"].clip(lower=0)

    # Recalcular por 90 sobre el total del período.
    for _, raw, _ in BASE_METRICS.values():
        if raw in out.columns:
            out[raw + "_p90"] = safe_div(out[raw] * 90, mins)

    if "goles_equipo" in out.columns:
        out["goles_p90"] = safe_div(out["goles_equipo"] * 90, mins)
    if "goles_recibidos" in out.columns:
        out["goles_recibidos_p90"] = safe_div(out["goles_recibidos"] * 90, mins)

    if "accurate_passes" in out.columns and "passes" in out.columns:
        out["efectividad_pases"] = safe_div(out["accurate_passes"] * 100, out["passes"])
    if "passes_into_final_third" in out.columns and "passes" in out.columns:
        out["efectividad_ultimo_tercio"] = safe_div(out["passes_into_final_third"] * 100, out["passes"])
    if "duels_won" in out.columns and "duels" in out.columns:
        out["efectividad_duelos"] = safe_div(out["duels_won"] * 100, out["duels"])
    if "shots_on_target" in out.columns and "shots" in out.columns:
        out["efectividad_tiros_al_arco"] = safe_div(out["shots_on_target"] * 100, out["shots"])
    if "goals" in out.columns and "shots_on_target" in out.columns:
        out["conversion_tiros_arco"] = safe_div(out["goals"] * 100, out["shots_on_target"])
    if "assists" in out.columns and "chances_created" in out.columns:
        out["asistencias_por_ocasion"] = safe_div(out["assists"] * 100, out["chances_created"])

    if "goals" in out.columns and "assists" in out.columns:
        out["g_a"] = out["goals"] + out["assists"]
        out["g_a_p90"] = safe_div(out["g_a"] * 90, mins)

    if "goles_equipo" in out.columns and "goles_recibidos" in out.columns:
        out["balance_goles"] = out["goles_equipo"] - out["goles_recibidos"]

    index_groups = {
        "indice_creacion": ["progressive_passes_p90", "passes_into_final_third_p90", "progressive_carries_p90", "efectividad_ultimo_tercio"],
        "indice_posesion": ["posesion", "passes_into_final_third_p90"],
        "indice_oportunidades": ["chances_created_p90", "shots_on_target_p90"],
        "indice_ataque": ["goles_p90", "assists_p90", "g_a_p90", "shots_on_target_p90", "chances_created_p90"],
        "indice_defensa": ["interceptions_p90", "blocks_p90", "tackles_p90", "clearances_p90", "goles_recibidos_p90"],
        "indice_recuperacion": ["recoveries_p90", "interceptions_p90", "tackles_p90"],
        "indice_duelos": ["efectividad_duelos", "duels_won_p90"],
        "indice_eficiencia": ["efectividad_pases", "efectividad_duelos", "conversion_tiros_arco"],
    }

    for idx_name, fields in index_groups.items():
        available = [f for f in fields if f in out.columns]
        if not available:
            continue
        ranks = []
        for f in available:
            s = pd.to_numeric(out[f], errors="coerce")
            ranks.append(s.rank(pct=True, ascending=(f != "goles_recibidos_p90")))
        out[idx_name] = pd.concat(ranks, axis=1).mean(axis=1) * 100

    return out

def make_recent(tm):
    if tm.empty:
        return pd.DataFrame()
    tm = tm.copy()
    tm["fecha"] = pd.to_datetime(tm["fecha"], errors="coerce")
    pieces = []
    for team, g in tm.groupby("equipo"):
        g = g.sort_values(["fecha", "match_id"]).tail(ULTIMOS_5)
        pieces.append(g)
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()

def display_metric_name(col):
    mapping = {
        "efectividad_pases": "Efectividad de pases (%)",
        "efectividad_ultimo_tercio": "Efectividad de pases al último tercio (%)",
        "efectividad_duelos": "Efectividad en duelos (%)",
        "efectividad_tiros_al_arco": "Efectividad de tiros al arco (%)",
        "conversion_tiros_arco": "Conversión de tiros al arco (%)",
        "asistencias_por_ocasion": "Asistencias por ocasión (%)",
        "goles_p90": "Goles por 90",
        "goles_recibidos_p90": "Goles recibidos por 90",
        "balance_goles": "Balance de goles",
        "g_a": "G+A",
        "g_a_p90": "G+A por 90",
        "posesion": "Posesión (%)",
        "indice_creacion": "Índice de creación",
        "indice_posesion": "Índice de posesión",
        "indice_oportunidades": "Índice de oportunidades",
        "indice_ataque": "Índice de ataque",
        "indice_defensa": "Índice de defensa",
        "indice_recuperacion": "Índice de recuperación",
        "indice_duelos": "Índice de duelos",
        "indice_eficiencia": "Índice de eficiencia",
    }
    if col in mapping:
        return mapping[col]
    for key, (name, raw, _) in BASE_METRICS.items():
        if col == key:
            return name
        if col == raw + "_p90":
            return name + " por 90"
    return col.replace("_", " ").title()

def phase_for(col):
    for key, (_, raw, phase) in BASE_METRICS.items():
        if col in {key, raw, raw + "_p90"}:
            return phase
    if col in {"efectividad_pases", "efectividad_ultimo_tercio", "conversion_tiros_arco", "asistencias_por_ocasion", "indice_eficiencia"}:
        return "EFICIENCIA"
    if col in {"posesion", "indice_posesion"}:
        return "POSESION"
    if col in {"goles_equipo", "goles_p90", "goles_recibidos", "goles_recibidos_p90", "balance_goles", "g_a", "g_a_p90", "indice_ataque"}:
        return "ATAQUE"
    if col.startswith("indice_"):
        return col.replace("indice_", "").upper()
    return "OTROS"

def build_output_table(period):
    if period.empty:
        return pd.DataFrame()

    # Seleccionamos columnas útiles y las renombramos a nombres legibles.
    preferred = [
        "equipo", "minutos", "goles_equipo", "goles_recibidos", "balance_goles",
        "posesion", "efectividad_pases", "efectividad_ultimo_tercio",
        "efectividad_duelos", "efectividad_tiros_al_arco", "conversion_tiros_arco",
        "goles_p90", "goles_recibidos_p90", "g_a", "g_a_p90",
    ]
    for key, (_, raw, _) in BASE_METRICS.items():
        preferred += [raw, raw + "_p90", key]
    preferred += [
        "indice_creacion", "indice_posesion", "indice_oportunidades",
        "indice_ataque", "indice_eficiencia", "indice_defensa",
        "indice_recuperacion", "indice_duelos",
    ]

    seen = set()
    cols = []
    for c in preferred:
        if c in period.columns and c not in seen:
            cols.append(c)
            seen.add(c)

    out = period[cols].copy()
    rename = {c: display_metric_name(c) for c in cols if c != "equipo"}
    rename["equipo"] = "Equipo"
    out = out.rename(columns=rename)
    return out

def build_tops(period):
    rows = []
    if period.empty:
        return pd.DataFrame()

    candidates = []
    for c in period.columns:
        if c in {"equipo", "minutos", "local"}:
            continue
        if not pd.api.types.is_numeric_dtype(period[c]):
            continue
        if c.endswith("_p90") or c.startswith("indice_") or c.startswith("efectividad_") or c in {
            "posesion", "conversion_tiros_arco", "asistencias_por_ocasion", "balance_goles", "g_a"
        }:
            candidates.append(c)

    # Los rankings de "goles recibidos" y "goles recibidos por 90" son mejores
    # cuanto más bajo. El resto, cuanto más alto.
    for c in candidates:
        s = pd.to_numeric(period[c], errors="coerce").dropna()
        if s.empty:
            continue
        ascending = c in {"goles_recibidos", "goles_recibidos_p90"}
        top = period[["equipo", c]].dropna().sort_values(c, ascending=ascending).head(TOP_N)
        for rank, (_, row) in enumerate(top.iterrows(), 1):
            rows.append({
                "Fase": phase_for(c),
                "Variable": display_metric_name(c),
                "Puesto": rank,
                "Equipo": row["equipo"],
                "Valor": row[c],
                "Mejor cuando": "MENOR" if ascending else "MAYOR",
            })
    return pd.DataFrame(rows)

def matchup_table(hist, recent):
    if hist.empty:
        return pd.DataFrame()

    h = hist.copy()
    r = recent.copy()

    # Índices principales; si alguno no existe, simplemente no se muestra.
    wanted = [
        "indice_creacion", "indice_posesion", "indice_oportunidades",
        "indice_ataque", "indice_eficiencia", "indice_defensa",
        "indice_recuperacion", "indice_duelos",
    ]
    teams = sorted(h["equipo"].dropna().astype(str).unique())
    rows = []
    for _, a in h.iterrows():
        for _, b in h.iterrows():
            if a["equipo"] == b["equipo"]:
                continue
            row = {
                "Equipo A": a["equipo"],
                "Equipo B": b["equipo"],
            }
            for c in wanted:
                if c in h.columns:
                    row[display_metric_name(c) + " A"] = a[c]
                    row[display_metric_name(c) + " B"] = b[c]
                    row[display_metric_name(c) + " Δ A-B"] = a[c] - b[c]
            rows.append(row)
    return pd.DataFrame(rows)

def dictionary_rows(available_cols):
    rows = [
        ["CREACION", "Pases precisos por 90", "Volumen de pases precisos normalizado por minutos.", "TOP = mayor volumen de circulación precisa.", "Contexto para equipos que construyen mediante pase.", "Directa/derivada"],
        ["CREACION", "Pases progresivos por 90", "Capacidad de avanzar mediante pases.", "TOP = mayor progresión por pase.", "Contexto de construcción y avance.", "Directa/derivada"],
        ["CREACION", "Pases al último tercio por 90", "Veces que el equipo lleva la pelota hacia el último tercio.", "TOP = mayor llegada territorial.", "Contexto ofensivo y de generación.", "Directa/derivada"],
        ["CREACION", "Efectividad de pases al último tercio", "Relación entre pases precisos disponibles y volumen de pase.", "TOP = mayor precisión/efectividad.", "Distingue volumen de calidad de ejecución.", "Derivada"],
        ["POSESION", "Posesión", "Porcentaje de posesión cuando el dato existe.", "TOP = mayor control de pelota.", "Contexto de dominio territorial.", "Directa"],
        ["OPORTUNIDADES", "Ocasiones creadas por 90", "Ocasiones creadas normalizadas por minutos.", "TOP = mayor generación de oportunidades.", "Contexto para atacantes y volantes ofensivos.", "Derivada"],
        ["OPORTUNIDADES", "Tiros al arco por 90", "Finalizaciones que llegan al arco.", "TOP = mayor amenaza directa.", "Contexto ofensivo.", "Derivada"],
        ["ATAQUE", "Goles por 90", "Goles producidos por el equipo normalizados.", "TOP = mayor producción goleadora.", "Contexto ofensivo.", "Derivada"],
        ["ATAQUE", "G+A", "Goles más asistencias.", "TOP = mayor producción directa de gol.", "Contexto para generación de puntos ofensivos.", "Derivada"],
        ["EFICIENCIA", "Efectividad de duelos", "Duelos ganados / duelos totales.", "TOP = mayor proporción de duelos ganados.", "Mide calidad, no solo volumen.", "Derivada"],
        ["DEFENSA", "Intercepciones por 90", "Intercepciones normalizadas.", "TOP = mayor cantidad de cortes.", "Contexto defensivo.", "Derivada"],
        ["DEFENSA", "Bloqueos por 90", "Acciones de bloqueo normalizadas.", "TOP = mayor capacidad de impedir finalizaciones.", "Contexto defensivo.", "Derivada"],
        ["DEFENSA", "Goles recibidos por 90", "Goles concedidos normalizados.", "TOP = MENOR cantidad.", "Contexto de solidez defensiva.", "Derivada"],
        ["RECUPERACION", "Recuperaciones por 90", "Recuperaciones de posesión normalizadas.", "TOP = mayor capacidad de recuperar.", "Contexto de presión/transición.", "Derivada"],
        ["DUELOS", "Duelos ganados por 90", "Volumen de duelos ganados.", "TOP = mayor volumen.", "Contexto físico.", "Derivada"],
        ["PELOTA PARADA", "Goles de pelota parada", "Se incluirá solo cuando la fuente identifique la acción de forma confiable.", "TOP = mayor producción identificada.", "Contexto específico de ABP.", "Fuente dependiente"],
        ["TRANSICIONES", "Recuperación alta", "Recuperaciones en zona alta, si el campo está disponible.", "TOP = mayor recuperación cerca del arco rival.", "Contexto de presión y contraataque.", "Fuente dependiente"],
        ["DISCIPLINA", "Tarjetas/faltas", "Volumen disciplinario cuando esté disponible.", "TOP depende de la variable: para faltas/tarjetas, mayor = mayor riesgo.", "Contexto de interrupciones y riesgo disciplinario.", "Fuente dependiente"],
        ["INDICES", "Índices de fase", "Promedios de percentiles de las variables disponibles de cada fase.", "TOP = mejor posición relativa dentro de la muestra.", "Resumen contextual, no reemplaza las métricas originales.", "Índice"],
        ["REGLA", "Por 90", "Normaliza por minutos acumulados.", "Permite comparar equipos con distinto volumen de minutos.", "Evita que el volumen bruto domine el ranking.", "Derivada"],
        ["REGLA", "Últimos 5", "Usa exclusivamente los cinco partidos más recientes disponibles de cada equipo.", "TOP = mejor rendimiento reciente.", "Mide forma actual.", "Derivada"],
    ]
    return pd.DataFrame(rows, columns=["Bloque", "Variable", "Qué mide", "Qué significa estar TOP", "Utilidad para WINNING AI", "Tipo"])

def write_interactive_ranking(ws, period, title):
    """Panel Excel con selector de variable y ranking dinámico."""
    if period is None or period.empty:
        ws.append(["SIN DATOS DISPONIBLES"])
        return

    candidates = []
    for c in period.columns:
        if c in {"equipo", "minutos", "local"}:
            continue
        if not pd.api.types.is_numeric_dtype(period[c]):
            continue
        if c.endswith("_p90") or c.startswith("indice_") or c.startswith("efectividad_") or c in {
            "posesion", "conversion_tiros_arco", "asistencias_por_ocasion", "balance_goles", "g_a"
        } and c not in candidates:
            candidates.append(c)

    candidates = sorted(candidates, key=lambda c: (phase_for(c), display_metric_name(c)))
    if not candidates:
        ws.append(["SIN VARIABLES NUMÉRICAS DISPONIBLES"])
        return

    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=16, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor="001E5F")
    ws.merge_cells("A1:E1")
    ws["A3"] = "Variable"; ws["A3"].font = Font(bold=True)
    ws["B3"] = display_metric_name(candidates[0])
    ws["D3"] = "Fase"; ws["D3"].font = Font(bold=True)
    ws["E3"] = phase_for(candidates[0])
    ws["D4"] = "Criterio TOP"; ws["D4"].font = Font(bold=True)
    ws["E4"] = "MENOR" if candidates[0] in {"goles_recibidos", "goles_recibidos_p90"} else "MAYOR"

    from openpyxl.worksheet.datavalidation import DataValidation
    helper_col = 30  # AD
    end_helper = helper_col + len(candidates)
    ws.cell(1, helper_col, "Equipo")
    for j, c in enumerate(candidates, helper_col + 1):
        ws.cell(1, j, display_metric_name(c))
    for i, (_, row) in enumerate(period.sort_values("equipo").iterrows(), 2):
        ws.cell(i, helper_col, row["equipo"])
        for j, c in enumerate(candidates, helper_col + 1):
            value = row[c] if c in period.columns else np.nan
            ws.cell(i, j, None if pd.isna(value) else float(value))
    helper_end_row = len(period) + 1
    for col in range(helper_col, end_helper + 1):
        ws.column_dimensions[get_column_letter(col)].hidden = True

    start_letter = get_column_letter(helper_col + 1)
    end_letter = get_column_letter(end_helper)
    dv = DataValidation(type="list", formula1=f"=${start_letter}$1:${end_letter}$1", allow_blank=False)
    dv.error = "Elegí una variable de la lista."
    dv.errorTitle = "Variable no válida"
    dv.prompt = "Seleccioná qué variable querés ordenar."
    dv.promptTitle = "Ranking por variable"
    ws.add_data_validation(dv); dv.add(ws["B3"])
    ws["E3"] = f'=IFERROR(INDEX(${start_letter}$1:${end_letter}$1,1,MATCH($B$3,${start_letter}$1:${end_letter}$1,0)),"")'
    ws["E4"] = '=IF(OR($B$3="Goles recibidos por 90",$B$3="Goles recibidos"),"MENOR","MAYOR")'
    for cell, value in [("A6", "Puesto"), ("B6", "Equipo"), ("C6", "Valor")]:
        ws[cell] = value; ws[cell].font = Font(bold=True, color="FFFFFF"); ws[cell].fill = PatternFill("solid", fgColor="001E5F")
    formula = (
        f'=LET(equipos,$AD$2:$AD${helper_end_row},'
        f'valores,CHOOSECOLS(${start_letter}$2:${end_letter}${helper_end_row},XMATCH($B$3,${start_letter}$1:${end_letter}$1)),'
        f'dir,IF($E$4="MENOR",1,-1),orden,SORTBY(HSTACK(equipos,valores),valores,dir),'
        f'HSTACK(SEQUENCE(ROWS(orden)),orden))'
    )
    ws["A7"] = formula
    ws["A39"] = "Nota: 0 = valor estadístico real cuando la fuente lo registra."
    ws["A40"] = "Los datos no disponibles no se convierten en 0; quedan fuera de la métrica/ranking cuando corresponde."
    ws.merge_cells("A39:E39"); ws.merge_cells("A40:E40")
    ws["A39"].font = Font(italic=True); ws["A40"].font = Font(italic=True)
    ws.freeze_panes = "A7"; ws.sheet_view.showGridLines = False
    for col, width in {"A":10, "B":30, "C":18, "D":16, "E":18}.items(): ws.column_dimensions[col].width = width


def style_block_sheet(ws):
    ws.freeze_panes = "A2"; ws.sheet_view.showGridLines = False
    thin = Side(style="thin"); thick = Side(style="medium")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="001E5F")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(top=thick, bottom=thick)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.border = Border(bottom=thin); cell.alignment = Alignment(vertical="top", wrap_text=True)
    for col in range(1, ws.max_column + 1):
        letter = get_column_letter(col)
        width = min(max(12, max((len(str(ws.cell(r, col).value or "")) for r in range(1, min(ws.max_row, 100) + 1)), default=10) + 2), 36)
        ws.column_dimensions[letter].width = width
    ws.auto_filter.ref = ws.dimensions

def style_sheet(ws, freeze="A2"):
    ws.freeze_panes = freeze
    ws.sheet_view.showGridLines = False
    thin = Side(style="thin")
    medium = Side(style="medium")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="001E5F")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(bottom=medium)
    for row in ws.iter_rows():
        for c in row:
            c.alignment = Alignment(vertical="center", wrap_text=False)
            c.border = Border(bottom=thin)
    for col in range(1, ws.max_column + 1):
        letter = get_column_letter(col)
        width = min(max(12, max((len(str(ws.cell(r, col).value or "")) for r in range(1, min(ws.max_row, 100) + 1)), default=10) + 2), 34)
        ws.column_dimensions[letter].width = width
    ws.auto_filter.ref = ws.dimensions

def write_df(ws, df):
    if df is None or df.empty:
        ws.append(["SIN DATOS DISPONIBLES"])
        return
    ws.append(list(df.columns))
    for row in df.itertuples(index=False):
        ws.append(list(row))

def main():
    print("=" * 90)
    print("RANKING DE EQUIPOS - WINNING AI")
    print("=" * 90)

    if not DATASET.exists():
        raise FileNotFoundError(f"No existe {DATASET}")

    df = pd.read_csv(DATASET, low_memory=False)
    print(f"Dataset: {df.shape[0]} filas x {df.shape[1]} columnas")

    cols = {k: find_col(df, v) for k, v in ALIASES.items()}
    required = ["team", "date", "match", "minutes"]
    missing = [x for x in required if not cols[x]]
    if missing:
        raise ValueError("Faltan columnas obligatorias: " + ", ".join(missing))

    df[cols["date"]] = pd.to_datetime(df[cols["date"]], errors="coerce")
    df[cols["minutes"]] = numeric(df, cols["minutes"])

    for k, c in cols.items():
        if c and k not in {"team", "date", "match", "player_id", "player_name", "position"}:
            df[c] = numeric(df, c)

    tm = build_team_match(df, cols)
    tm = add_derived_metrics(tm, cols)
    tm["fecha"] = pd.to_datetime(tm["fecha"], errors="coerce")
    tm = tm.dropna(subset=["equipo", "fecha", "match_id"])
    tm = tm.sort_values(["equipo", "fecha", "match_id"])

    hist = aggregate_period(tm, tm)
    recent_matches = make_recent(tm)
    recent = aggregate_period(recent_matches, recent_matches)

    # Evolución de índices recientes vs históricos.
    if not hist.empty and not recent.empty:
        idx_cols = [c for c in hist.columns if c.startswith("indice_")]
        for c in idx_cols:
            if c in recent.columns:
                recent = recent.merge(hist[["equipo", c]].rename(columns={c: c + "_historico"}), on="equipo", how="left")
                recent[c + "_evolucion"] = recent[c] - recent[c + "_historico"]

    hist_out = build_output_table(hist)
    recent_out = build_output_table(recent)
    tops_hist = build_tops(hist)
    tops_recent = build_tops(recent)
    matchup = matchup_table(hist, recent)
    dictionary = dictionary_rows(set(hist.columns) | set(recent.columns))

    # CSV general combinado.
    hist_out.to_csv(DATOS / "ranking_equipos_historico.csv", index=False, encoding="utf-8-sig")
    recent_out.to_csv(DATOS / "ranking_equipos_ultimos_5.csv", index=False, encoding="utf-8-sig")
    tops_hist.to_csv(DATOS / "ranking_equipos_tops_historico.csv", index=False, encoding="utf-8-sig")
    tops_recent.to_csv(DATOS / "ranking_equipos_tops_ultimos_5.csv", index=False, encoding="utf-8-sig")

    wb = Workbook()
    default = wb.active
    wb.remove(default)

    sheets = [
        ("HISTORICO", hist_out),
        ("ULTIMOS_5", recent_out),
        ("TOPS_HISTORICO", tops_hist),
        ("TOPS_ULTIMOS_5", tops_recent),
        ("MATCHUP", matchup),
        ("DICCIONARIO_VARIABLES", dictionary),
    ]

    for name, data in sheets:
        ws = wb.create_sheet(name)
        if name == "HISTORICO":
            write_interactive_ranking(ws, hist, "RANKING HISTÓRICO DE EQUIPOS")
        elif name == "ULTIMOS_5":
            write_interactive_ranking(ws, recent, "RANKING DE EQUIPOS - ÚLTIMOS 5")
        else:
            write_df(ws, data)
            style_block_sheet(ws)

    # Formato numérico.
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, float):
                    cell.number_format = "0.00"

    wb.save(OUTPUT_XLSX)

    print()
    print(f"OK Excel: {OUTPUT_XLSX}")
    print(f"OK CSV histórico: {DATOS / 'ranking_equipos_historico.csv'}")
    print(f"OK CSV últimos 5: {DATOS / 'ranking_equipos_ultimos_5.csv'}")
    print(f"Equipos histórico: {len(hist_out)}")
    print(f"Equipos últimos 5: {len(recent_out)}")
    print(f"Top histórico: {len(tops_hist)} registros")
    print(f"Top últimos 5: {len(tops_recent)} registros")
    print("Las métricas inexistentes en el dataset no se inventan: quedan fuera del cálculo.")

if __name__ == "__main__":
    main()
