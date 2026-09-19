import json
from pathlib import Path

CARPETA_PLAYERS = Path("datos/pitchapi")
CARPETA_EVENTS = Path("datos/pitchapi")

archivos = sorted(
    archivo
    for archivo in CARPETA_PLAYERS.glob("*_players.json")
    if not archivo.name.endswith("_advanced_players.json")
)

print()
print("=" * 100)
print("AUDITORÍA — MINUTOS Y TITULARIDAD")
print("=" * 100)
print()

print(f"Partidos encontrados: {len(archivos)}")
print()

# Buscar un partido que tenga jugadores y sustituciones
archivo_players = None
jugadores = None
match_id = None

for archivo in archivos:

    try:
        data = json.loads(
            archivo.read_text(encoding="utf-8")
        )
    except Exception:
        continue

    lista = data.get("data")

    if isinstance(lista, list) and len(lista) > 0:

        archivo_players = archivo
        jugadores = lista
        match_id = archivo.stem.replace("_players", "")
        break

if archivo_players is None:
    print("No se encontró ningún partido con jugadores.")
    exit()

print(f"Partido seleccionado: {match_id}")
print(f"Archivo: {archivo_players.name}")
print(f"Jugadores: {len(jugadores)}")
print()

# ============================================================
# JUGADORES
# ============================================================

print("=" * 100)
print("JUGADORES Y MINUTOS")
print("=" * 100)

for jugador in jugadores:

    player = jugador.get("player", {})
    stats = jugador.get("stats", [])

    nombre = player.get("name")
    player_id = player.get("id")
    team_id = jugador.get("team_id")

    minutos = None

    for grupo in stats:

        stats_grupo = grupo.get("stats", {})

        for nombre_stat, contenido in stats_grupo.items():

            key = contenido.get("key")

            if key == "minutes_played":

                stat = contenido.get("stat", {})
                minutos = stat.get("value")

    print(
        f"{nombre:<30} "
        f"id={player_id:<12} "
        f"team={team_id:<10} "
        f"minutos={minutos}"
    )

# ============================================================
# EVENTOS
# ============================================================

archivo_events = CARPETA_EVENTS / f"{match_id}_events.json"

print()
print("=" * 100)
print("SUSTITUCIONES")
print("=" * 100)

if not archivo_events.exists():

    print("No existe archivo de eventos para este partido.")
    exit()

try:
    data_events = json.loads(
        archivo_events.read_text(encoding="utf-8")
    )
except Exception as e:

    print(f"Error leyendo eventos: {e}")
    exit()

eventos = data_events.get("data", {}).get("events", [])

sustituciones = [
    evento
    for evento in eventos
    if evento.get("event_type") == "substitution"
]

print(f"Sustituciones: {len(sustituciones)}")
print()

for i, evento in enumerate(sustituciones, start=1):

    print(f"SUSTITUCIÓN #{i}")
    print("-" * 80)

    print(json.dumps(
        evento,
        indent=2,
        ensure_ascii=False
    ))

    print()

print("=" * 100)
print("FIN")
print("=" * 100)