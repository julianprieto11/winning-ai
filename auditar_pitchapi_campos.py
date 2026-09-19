import json
import glob
import os


BASE = "datos/pitchapi"


# ============================================================
# BUSCAR UN PARTIDO QUE TENGA PLAYERS + ADVANCED
# ============================================================

players_files = glob.glob(
    os.path.join(BASE, "*_players.json")
)

partido = None
players = None
advanced_players = None

for players_file in players_files:

    try:

        with open(players_file, encoding="utf-8") as f:
            players_json = json.load(f)

        players_data = players_json.get("data", [])

        if not isinstance(players_data, list):
            continue

        if not players_data:
            continue

        match_id = os.path.basename(
            players_file
        ).replace(
            "_players.json",
            ""
        )

        advanced_file = os.path.join(
            BASE,
            f"{match_id}_advanced_players.json"
        )

        if not os.path.exists(advanced_file):
            continue

        with open(advanced_file, encoding="utf-8") as f:
            advanced_json = json.load(f)

        advanced_data = (
            advanced_json
            .get("data", {})
            .get("players", [])
        )

        if not advanced_data:
            continue

        partido = match_id
        players = players_data
        advanced_players = advanced_data

        break

    except Exception:
        continue


if partido is None:

    print("No se encontró un partido válido.")
    raise SystemExit


# ============================================================
# INFORMACIÓN GENERAL
# ============================================================

print()
print("=" * 100)
print("AUDITORÍA REAL DE PITCHAPI")
print("=" * 100)

print()
print(f"Partido: {partido}")
print(f"Players: {len(players)}")
print(f"Advanced: {len(advanced_players)}")


# ============================================================
# PRIMER JUGADOR
# ============================================================

p = players[0]

print()
print("=" * 100)
print("ESTRUCTURA PLAYERS")
print("=" * 100)

print()
print("Jugador:")

for clave, valor in p.items():

    if isinstance(valor, dict):

        print()
        print(f"[{clave}]")

        for subclave, subvalor in valor.items():

            print(
                f"  {subclave}: {subvalor}"
            )

    else:

        print(
            f"{clave}: {valor}"
        )


# ============================================================
# ENCONTRAR EL MISMO JUGADOR EN ADVANCED
# ============================================================

player_id = None

if isinstance(p.get("player"), dict):

    player_id = p["player"].get("id")


a = None

for jugador in advanced_players:

    jugador_info = jugador.get(
        "player",
        {}
    )

    if str(
        jugador_info.get("id")
    ) == str(player_id):

        a = jugador
        break


if a is None:

    print()
    print(
        "No se encontró el mismo jugador en advanced."
    )

    raise SystemExit


# ============================================================
# ADVANCED
# ============================================================

print()
print("=" * 100)
print("ESTRUCTURA ADVANCED")
print("=" * 100)

print()

for clave, valor in a.items():

    if isinstance(valor, dict):

        print()
        print(f"[{clave}]")

        for subclave, subvalor in valor.items():

            print(
                f"  {subclave}: {subvalor}"
            )

    else:

        print(
            f"{clave}: {valor}"
        )


# ============================================================
# BUSCADOR RECURSIVO
# ============================================================

def buscar(obj, objetivo, ruta=""):

    encontrados = []

    if isinstance(obj, dict):

        for clave, valor in obj.items():

            nueva_ruta = (
                f"{ruta}.{clave}"
                if ruta
                else clave
            )

            if clave.lower() == objetivo.lower():

                encontrados.append(
                    (
                        nueva_ruta,
                        valor
                    )
                )

            encontrados.extend(
                buscar(
                    valor,
                    objetivo,
                    nueva_ruta
                )
            )

    elif isinstance(obj, list):

        for i, valor in enumerate(obj):

            encontrados.extend(
                buscar(
                    valor,
                    objetivo,
                    f"{ruta}[{i}]"
                )
            )

    return encontrados


# ============================================================
# CAMPOS IMPORTANTES PARA WINNING
# ============================================================

objetivos = [

    # PASES
    "passes",
    "accurate_passes",
    "progressive_passes",
    "passes_into_final_third",
    "accurate_long_balls",
    "accurate_crosses",

    # ATAQUE / CREACIÓN
    "chances_created",
    "key_passes",
    "assists",
    "total_shots",
    "ShotsOnTarget",
    "ShotsOffTarget",
    "shots_woodwork",
    "expected_goals",
    "expected_assists",
    "big_chance_created_team_title",
    "big_chance_missed_title",
    "dribbles_succeeded",

    # DUELOS / CONDUCCIÓN
    "duels_won",
    "duels_lost",
    "take_ons",
    "take_ons_won",
    "progressive_carries",
    "miscontrols",
    "dispossessed",

    # DEFENSA
    "tackles",
    "interceptions",
    "recoveries",
    "clearances",
    "blocks",
    "dribbled_past",

    # ARQUERO
    "saves",
    "saved_penalties",
    "goals_conceded",

    # DISCIPLINA
    "fouls",
    "was_fouled",
    "conceded_penalties",
    "missed_penalty",
    "penalties_won",

]


print()
print("=" * 100)
print("CAMPOS ENCONTRADOS")
print("=" * 100)


for objetivo in objetivos:

    encontrados = []

    encontrados.extend(
        buscar(
            p,
            objetivo
        )
    )

    encontrados.extend(
        buscar(
            a,
            objetivo
        )
    )

    print()
    print(f"### {objetivo}")

    if not encontrados:

        print("  NO ENCONTRADO")

    else:

        for ruta, valor in encontrados:

            print(
                f"  {ruta} = {valor}"
            )


print()
print("=" * 100)
print("FIN")
print("=" * 100)
print()