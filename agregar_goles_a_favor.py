import json
import glob
import pandas as pd


# ============================================================
# FUNCIONES
# ============================================================

def cargar_partido(archivo):
    with open(archivo, "r", encoding="utf-8") as f:
        return json.load(f)


def obtener_jugadores_participacion(lineups, incidentes):
    """
    Reconstruye quién estaba en cancha en cada momento.

    Devuelve:
        {
            player_id: {
                "team_id": ...,
                "entrada": ...,
                "salida": ...
            }
        }
    """

    jugadores = {}

    # --------------------------------------------------------
    # Jugadores que aparecen en las alineaciones
    # --------------------------------------------------------

    for lado in ["home", "away"]:

        for jugador in lineups[lado]["players"]:

            player = jugador["player"]
            player_id = player["id"]
            team_id = jugador["teamId"]

            stats = jugador.get("statistics", {})

            minutos = stats.get("minutesPlayed")

            if minutos is None:
                continue

            # Titular
            if not jugador.get("substitute", False):
                entrada = 0
            else:
                entrada = None

            jugadores[player_id] = {
                "team_id": team_id,
                "entrada": entrada,
                "salida": None,
            }

    # --------------------------------------------------------
    # Sustituciones
    # --------------------------------------------------------

    for incidente in incidentes:

        if incidente.get("incidentType") != "substitution":
            continue

        minuto = incidente.get("time")

        if minuto is None:
            continue

        jugador_in = incidente.get("playerIn")
        jugador_out = incidente.get("playerOut")

        if jugador_in:

            player_id = jugador_in.get("id")

            if player_id in jugadores:
                jugadores[player_id]["entrada"] = minuto

        if jugador_out:

            player_id = jugador_out.get("id")

            if player_id in jugadores:
                jugadores[player_id]["salida"] = minuto

    return jugadores


def jugador_estaba_en_cancha(jugador, minuto):
    """
    Determina si el jugador estaba en cancha
    en el momento del gol.
    """

    entrada = jugador["entrada"]
    salida = jugador["salida"]

    if entrada is None:
        return False

    # Entró después del gol
    if minuto < entrada:
        return False

    # Salió antes del gol
    if salida is not None and minuto > salida:
        return False

    return True


def obtener_goles_a_favor(incidentes, jugadores):

    goles_por_jugador = {}

    for incidente in incidentes:

        if incidente.get("incidentType") != "goal":
            continue

        # No contar penales errados
        if incidente.get("incidentClass") == "missed":
            continue

        jugador_gol = incidente.get("player")

        if not jugador_gol:
            continue

        goleador_id = jugador_gol.get("id")

        if goleador_id not in jugadores:
            continue

        equipo_goleador = jugadores[goleador_id]["team_id"]

        minuto = incidente.get("time")

        if minuto is None:
            continue

        for player_id, jugador in jugadores.items():

            if jugador["team_id"] != equipo_goleador:
                continue

            if not jugador_estaba_en_cancha(jugador, minuto):
                continue

            goles_por_jugador[player_id] = (
                goles_por_jugador.get(player_id, 0) + 1
            )

    return goles_por_jugador


# ============================================================
# PROCESAMIENTO
# ============================================================

print()
print("=" * 100)
print("CALCULANDO GOLES A FAVOR MIENTRAS ESTABA EN CANCHA")
print("=" * 100)

archivos = glob.glob("datos/partidos/*.json")

resultados = {}

total_goles = 0
total_asignaciones = 0

for archivo in archivos:

    datos = cargar_partido(archivo)

    event = datos["event"]["event"]
    match_id = event["id"]

    lineups = datos["lineups"]
    incidentes = datos["incidents"]["incidents"]

    jugadores = obtener_jugadores_participacion(
        lineups,
        incidentes
    )

    goles = obtener_goles_a_favor(
        incidentes,
        jugadores
    )

    for player_id, cantidad in goles.items():

        resultados[
            (match_id, player_id)
        ] = cantidad

        total_asignaciones += cantidad

    total_goles += sum(
        1
        for incidente in incidentes
        if (
            incidente.get("incidentType") == "goal"
            and incidente.get("incidentClass") != "missed"
        )
    )


# ============================================================
# ACTUALIZAR DATASET
# ============================================================

df = pd.read_csv("datos/dataset_jugadores.csv")

df["goals_for_while_playing"] = 0

for indice, fila in df.iterrows():

    clave = (
        int(fila["match_id"]),
        int(fila["player_id"])
    )

    if clave in resultados:
        df.at[
            indice,
            "goals_for_while_playing"
        ] = resultados[clave]


df.to_csv(
    "datos/dataset_jugadores.csv",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# VALIDACIÓN
# ============================================================

print()
print("=" * 100)
print("RESULTADO")
print("=" * 100)

print("Partidos procesados:", len(archivos))
print("Goles detectados:", total_goles)
print("Asignaciones jugador-gol:", total_asignaciones)

print()
print("Nueva columna:")
print("goals_for_while_playing")

print()
print("Máximo de goles de equipo recibidos por un jugador:")
print(
    df["goals_for_while_playing"].max()
)

print()
print("Jugadores con goles de equipo mientras estaban en cancha:")

print(
    df[
        df["goals_for_while_playing"] > 0
    ][
        [
            "match_id",
            "player_id",
            "player_name",
            "team_name",
            "minutesPlayed",
            "goals",
            "goals_for_while_playing"
        ]
    ]
    .head(30)
    .to_string(index=False)
)

print()
print("=" * 100)
print("LISTO")
print("=" * 100)