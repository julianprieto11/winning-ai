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
MIN_PARTICIPACIONES_ULTIMOS_5 = 3
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
    # Para partidos ya jugados PitchAPI devuelve confirmed=True.
    # Nunca usamos una alineación predicha para reconstruir el histórico.
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

