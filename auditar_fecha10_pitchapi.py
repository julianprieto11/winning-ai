import json
import os


# ============================================================
# PARTIDOS FECHA 10 - PITCHAPI
# ============================================================

PITCH_IDS = [
    "m_1ABSM7",
    "m_0Z63wJ",
    "m_1rGQaB",
    "m_11PYwu",
    "m_17fjdr",
    "m_0BTFn7",
    "m_0jdOYm",
    "m_2EhjDn",
    "m_0sbdux",
    "m_0MCwqI",
    "m_0el541",
    "m_0bU15M",
    "m_0MXtuT",
    "m_0Feldm",
]


print()
print("AUDITORÍA PITCHAPI - FECHA 10")
print("=" * 100)
print()


total_matches = 0
total_players = 0
total_advanced = 0

players_disponibles = 0
advanced_disponibles = 0


for pitch_id in PITCH_IDS:

    archivo_match = (
        f"datos/pitchapi/matches/{pitch_id}.json"
    )

    archivo_players = (
        f"datos/pitchapi/{pitch_id}_players.json"
    )

    archivo_advanced = (
        f"datos/pitchapi/{pitch_id}_advanced_players.json"
    )


    # --------------------------------------------------------
    # MATCH
    # --------------------------------------------------------

    existe_match = os.path.exists(archivo_match)

    if existe_match:
        total_matches += 1


    # --------------------------------------------------------
    # PLAYERS
    # --------------------------------------------------------

    cantidad_players = 0

    if os.path.exists(archivo_players):

        with open(
            archivo_players,
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        jugadores = data.get("data", [])

        if isinstance(jugadores, list):

            cantidad_players = len(jugadores)

        if cantidad_players > 0:

            players_disponibles += 1
            total_players += cantidad_players


    # --------------------------------------------------------
    # ADVANCED PLAYERS
    # --------------------------------------------------------

    cantidad_advanced = 0

    if os.path.exists(archivo_advanced):

        with open(
            archivo_advanced,
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        jugadores = data.get("data", [])

        if isinstance(jugadores, dict):

            jugadores = jugadores.get("players", [])

        if isinstance(jugadores, list):

            cantidad_advanced = len(jugadores)

        if cantidad_advanced > 0:

            advanced_disponibles += 1
            total_advanced += cantidad_advanced


    # --------------------------------------------------------
    # MOSTRAR
    # --------------------------------------------------------

    print(
        f"{pitch_id:10} | "
        f"match={'SI' if existe_match else 'NO':2} | "
        f"players={cantidad_players:2} | "
        f"advanced={cantidad_advanced:2}"
    )


# ============================================================
# RESUMEN
# ============================================================

print()
print("=" * 100)
print()

print(
    f"Partidos con archivo match:       "
    f"{total_matches}/15"
)

print(
    f"Partidos con players disponibles: "
    f"{players_disponibles}/15"
)

print(
    f"Total jugadores PitchAPI:         "
    f"{total_players}"
)

print(
    f"Partidos con advanced disponibles:"
    f" {advanced_disponibles}/15"
)

print(
    f"Total registros advanced:          "
    f"{total_advanced}"
)

print()