import json
import os
import re
import sys
import time
import subprocess
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from curl_cffi import requests


ROOT = Path(__file__).resolve().parent
DATOS = ROOT / "datos"
SOFA_DIR = DATOS / "partidos"
PITCH_DIR = DATOS / "pitchapi"
PITCH_MATCHES_DIR = PITCH_DIR / "matches"
PITCH_LINEUPS_DIR = PITCH_DIR / "lineups"

SOFA_TOURNAMENT_ID = 155
SOFA_SEASON_ID = 87913
PITCH_LEAGUE_ID = "l_45VZuL"
PITCH_SEASON = "2026"

SOFA_BASE = "https://www.sofascore.com/api/v1"
PITCH_BASE = "https://api.pitchapi.dev/v1"

REQUEST_TIMEOUT = 40
SLEEP_SOFA = 0.35
SLEEP_PITCH = 0.15


def normalizar(texto):
    if texto is None:
        return ""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.replace("&", " y ")
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    aliases = {
        "instituto": "instituto de cordoba",
        "instituto de cordoba": "instituto de cordoba",
        "independiente": "ca independiente",
        "ca independiente": "ca independiente",
        "union": "club atletico union de santa fe",
        "club atletico union de santa fe": "club atletico union de santa fe",
        "talleres": "ca talleres",
        "ca talleres": "ca talleres",
        "gimnasia lp": "gimnasia y esgrima",
        "gimnasia y esgrima": "gimnasia y esgrima",
        "central cordoba de santiago": "central cordoba",
        "central cordoba": "central cordoba",
        "belgrano": "club atletico belgrano",
        "club atletico belgrano": "club atletico belgrano",
        "lanus": "ca lanus",
        "ca lanus": "ca lanus",
        "estudiantes": "estudiantes de la plata",
        "estudiantes de la plata": "estudiantes de la plata",
        "gimnasia mendoza": "gimnasia y esgrima mendoza",
        "gimnasia y esgrima mendoza": "gimnasia y esgrima mendoza",
    }
    return aliases.get(texto, texto)


def request_json(url, *, headers=None, params=None, retries=3, impersonate=True):
    ultimo = None
    for intento in range(1, retries + 1):
        try:
            kwargs = {"timeout": REQUEST_TIMEOUT}
            if headers:
                kwargs["headers"] = headers
            if params:
                kwargs["params"] = params
            if impersonate:
                kwargs["impersonate"] = "chrome"
            response = requests.get(url, **kwargs)
            if response.status_code == 200:
                return response.json()
            ultimo = RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
        except Exception as error:
            ultimo = error
        if intento < retries:
            time.sleep(1.5 * intento)
    raise RuntimeError(f"No se pudo descargar {url}: {ultimo}")


def cargar_pitch_key():
    env_key = os.getenv("PITCHAPI_API_KEY", "").strip()
    if env_key:
        return env_key
    script = ROOT / "probar_pitchapi.py"
    if script.exists():
        for linea in script.read_text(encoding="utf-8-sig").splitlines():
            if linea.strip().startswith("API_KEY") and "=" in linea:
                return linea.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(
        "No se encontró la API key de PitchAPI. "
        "Definí PITCHAPI_API_KEY o configurá probar_pitchapi.py."
    )


def obtener_round_sofascore(round_num):
    url = (
        f"{SOFA_BASE}/unique-tournament/{SOFA_TOURNAMENT_ID}/"
        f"season/{SOFA_SEASON_ID}/events/round/{round_num}"
    )
    data = request_json(url)
    eventos = data.get("events", [])
    if not eventos:
        raise RuntimeError(f"SofaScore no devolvió partidos para la Fecha {round_num}.")
    return eventos


def descargar_sofascore_round(round_num):
    eventos = obtener_round_sofascore(round_num)
    SOFA_DIR.mkdir(parents=True, exist_ok=True)
    print()
    print("=" * 78)
    print(f"SOFASCORE - FECHA {round_num} - {len(eventos)} PARTIDOS")
    print("=" * 78)
    for i, evento in enumerate(eventos, 1):
        event_id = str(evento["id"])
        local = evento.get("homeTeam", {}).get("name", "")
        visitante = evento.get("awayTeam", {}).get("name", "")
        print(f"{i:02d}/{len(eventos):02d} | {event_id} | {local} - {visitante}")
        try:
            lineups = request_json(f"{SOFA_BASE}/event/{event_id}/lineups")
        except Exception as error:
            print(f"  [AVISO] lineups: {error}")
            lineups = {"error": str(error)}
        try:
            incidents = request_json(f"{SOFA_BASE}/event/{event_id}/incidents")
        except Exception as error:
            print(f"  [AVISO] incidents: {error}")
            incidents = {"error": str(error)}
        try:
            statistics = request_json(f"{SOFA_BASE}/event/{event_id}/statistics")
        except Exception as error:
            print(f"  [AVISO] statistics: {error}")
            statistics = {"error": str(error)}
        payload = {
            "event": {"event": evento},
            "lineups": lineups,
            "incidents": incidents,
            "statistics": statistics,
        }
        (SOFA_DIR / f"{event_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        time.sleep(SLEEP_SOFA)
    return eventos


def obtener_pitch_matches(api_key):
    headers = {"X-API-KEY": api_key}
    data = request_json(
        f"{PITCH_BASE}/leagues/{PITCH_LEAGUE_ID}/matches",
        headers=headers,
        params={"season": PITCH_SEASON, "status": "all"},
        impersonate=False,
    )
    matches = data.get("data", {}).get("matches", [])
    if not matches:
        raise RuntimeError("PitchAPI no devolvió partidos de la temporada.")
    return matches


def fecha_sofa(evento):
    timestamp = evento.get("startTimestamp")
    if timestamp is None:
        return ""
    try:
        import datetime as _dt
        return _dt.datetime.fromtimestamp(
            int(timestamp), tz=_dt.timezone.utc
        ).strftime("%Y-%m-%d")
    except Exception:
        return ""


def match_score(sofa, pitch):
    if fecha_sofa(sofa) != str(pitch.get("date") or "")[:10]:
        return 0.0
    s_home = normalizar(sofa.get("homeTeam", {}).get("name"))
    s_away = normalizar(sofa.get("awayTeam", {}).get("name"))
    p_home = normalizar(pitch.get("home_team", {}).get("name"))
    p_away = normalizar(pitch.get("away_team", {}).get("name"))
    directo = (
        SequenceMatcher(None, s_home, p_home).ratio()
        + SequenceMatcher(None, s_away, p_away).ratio()
    ) / 2
    invertido = (
        SequenceMatcher(None, s_home, p_away).ratio()
        + SequenceMatcher(None, s_away, p_home).ratio()
    ) / 2
    return max(directo, invertido)


def construir_mapeo(eventos, pitch_matches):
    resultado = {}
    for evento in eventos:
        event_id = str(evento["id"])
        candidatos = [
            p for p in pitch_matches
            if fecha_sofa(evento) == str(p.get("date") or "")[:10]
        ]
        puntuados = sorted(
            ((match_score(evento, p), p) for p in candidatos),
            key=lambda x: x[0],
            reverse=True,
        )
        if not puntuados or puntuados[0][0] < 0.90:
            local = evento.get("homeTeam", {}).get("name", "")
            visitante = evento.get("awayTeam", {}).get("name", "")
            raise RuntimeError(
                f"No se pudo mapear con seguridad SofaScore {event_id}: "
                f"{local} - {visitante}"
            )
        score, pitch = puntuados[0]
        if len(puntuados) > 1 and score == puntuados[1][0]:
            raise RuntimeError(
                f"Mapeo ambiguo para SofaScore {event_id}: "
                f"dos partidos PitchAPI con score {score:.3f}"
            )
        resultado[event_id] = str(pitch["id"])
    return resultado


def descargar_pitchapi_match(match_id, api_key):
    headers = {"X-API-KEY": api_key}
    PITCH_MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    PITCH_LINEUPS_DIR.mkdir(parents=True, exist_ok=True)
    endpoints = {
        "match": f"{PITCH_BASE}/matches/{match_id}",
        "players": f"{PITCH_BASE}/matches/{match_id}/players",
        "advanced_players": f"{PITCH_BASE}/matches/{match_id}/advanced/players",
        "events": f"{PITCH_BASE}/matches/{match_id}/events",
        "lineups": f"{PITCH_BASE}/matches/{match_id}/lineups",
    }
    destinos = {
        "match": PITCH_MATCHES_DIR / f"{match_id}.json",
        "players": PITCH_DIR / f"{match_id}_players.json",
        "advanced_players": PITCH_DIR / f"{match_id}_advanced_players.json",
        "events": PITCH_DIR / f"{match_id}_events.json",
        "lineups": PITCH_LINEUPS_DIR / f"{match_id}_lineups.json",
    }
    for tipo, url in endpoints.items():
        try:
            data = request_json(url, headers=headers, impersonate=False)
            destinos[tipo].write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"    OK {tipo}")
        except Exception as error:
            print(f"    AVISO {tipo}: {error}")
        time.sleep(SLEEP_PITCH)


def guardar_mapeo(mapeo):
    (DATOS / "mapeo_sofascore_pitchapi.json").write_text(
        json.dumps(mapeo, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def ejecutar_script(nombre):
    print()
    print("=" * 78)
    print(f"EJECUTANDO {nombre}")
    print("=" * 78)
    subprocess.run([sys.executable, str(ROOT / nombre)], cwd=ROOT, check=True)


def calcular_corte(eventos_objetivo):
    import datetime as _dt
    fechas = []
    for evento in eventos_objetivo:
        ts = evento.get("startTimestamp")
        if ts is not None:
            fechas.append(
                _dt.datetime.fromtimestamp(
                    int(ts), tz=_dt.timezone.utc
                ).date()
            )
    if not fechas:
        raise RuntimeError("No se pudo determinar la fecha de la Fecha objetivo.")
    return min(fechas).isoformat()


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python ejecutar_fecha.py <numero_fecha>")
    try:
        fecha_objetivo = int(sys.argv[1])
    except ValueError:
        raise SystemExit("La fecha debe ser un número entero.")
    if fecha_objetivo < 2:
        raise SystemExit("La primera fecha automatizable es la Fecha 2.")

    fecha_anterior = fecha_objetivo - 1

    print()
    print("=" * 78)
    print(f"WINNING AI - ACTUALIZACIÓN Y PREDICCIÓN FECHA {fecha_objetivo}")
    print("=" * 78)
    print()
    print(
        f"Se actualizará la Fecha {fecha_anterior} "
        f"y se preparará la Fecha {fecha_objetivo}."
    )

    api_key = cargar_pitch_key()

    eventos_anterior = descargar_sofascore_round(fecha_anterior)
    eventos_objetivo = descargar_sofascore_round(fecha_objetivo)

    pitch_matches = obtener_pitch_matches(api_key)
    todos = eventos_anterior + eventos_objetivo
    mapeo = construir_mapeo(todos, pitch_matches)
    guardar_mapeo(mapeo)

    print()
    print("=" * 78)
    print("MAPEO SOFASCORE -> PITCHAPI")
    print("=" * 78)
    for sofa_id, pitch_id in sorted(mapeo.items()):
        print(f"{sofa_id} -> {pitch_id}")

    for pitch_id in sorted(set(mapeo.values())):
        print()
        print(f"PITCHAPI {pitch_id}")
        descargar_pitchapi_match(pitch_id, api_key)

    ejecutar_script("puntuacion_winning_pitchapi.py")
    ejecutar_script("crear_contexto_equipos.py")
    ejecutar_script("calcular_forma_reciente.py")
    ejecutar_script("calcular_forma_local_visitante.py")
    ejecutar_script("calcular_rendimiento_reciente.py")
    ejecutar_script("crear_matchup.py")

    corte = calcular_corte(eventos_objetivo)

    import pandas as pd
    import backtest_fecha10 as motor

    motor.FECHA_OBJETIVO = fecha_objetivo
    motor.CORTE_HISTORICO = pd.Timestamp(corte)
    motor.MAPEO_PITCHAPI = mapeo

    sufijo = f"fecha{fecha_objetivo}"
    motor.SALIDA_CANDIDATOS = f"datos/candidatos_{sufijo}_final.csv"
    motor.SALIDA_EQUIPOS = f"datos/{sufijo}_equipos_predichos.csv"
    motor.SALIDA_EQUIPOS_EXCEL = f"datos/{sufijo}_equipos_predichos_excel.csv"
    motor.SALIDA_SIMULACIONES = f"datos/{sufijo}_simulaciones.csv"

    motor.main()

    print()
    print("=" * 78)
    print("PROCESO TERMINADO")
    print("=" * 78)
    print(f"Fecha objetivo: {fecha_objetivo}")
    print(f"Fecha actualizada: {fecha_anterior}")
    print(f"Corte histórico: {corte}")
    print()
    print("Archivos:")
    print(f" - {motor.SALIDA_CANDIDATOS}")
    print(f" - {motor.SALIDA_EQUIPOS}")
    print(f" - {motor.SALIDA_EQUIPOS_EXCEL}")
    print(f" - {motor.SALIDA_SIMULACIONES}")


if __name__ == "__main__":
    main()
