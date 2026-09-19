import pandas as pd
import json
import glob
import os

# =========================
# DATOS HISTORICOS
# =========================

df = pd.read_csv("datos/dataset_jugadores.csv")

# Solo jugadores que participaron
hist = df[df["minutesPlayed"].notna()].copy()

# =========================
# CALCULAR WINNING V1
# =========================

def v(fila, col):
    if col not in fila.index or pd.isna(fila[col]):
        return 0
    return fila[col]

def participacion(f):
    return (
        v(f, "minutesPlayed") * 0.03
        + v(f, "duelWon") * 0.20
        - v(f, "duelLost") * 0.20
        - v(f, "unsuccessfulTouch") * 0.20
        - v(f, "dispossessed") * 0.20
        + v(f, "progressiveBallCarriesCount") * 0.05
        - v(f, "errorLeadToAShot") * 1
        - v(f, "errorLeadToAGoal") * 2
    )

def pases(f):
    total = v(f, "totalPass")
    if total <= 0:
        return 0

    precision = v(f, "accuratePass") / total

    puntos = (
        v(f, "accuratePass") * 0.02
        + v(f, "accurateOppositionHalfPasses") * 0.05
        + v(f, "accurateLongBalls") * 0.05
        + v(f, "accurateCross") * 0.20
    )

    return min(puntos * precision, 4)

def goles_asistencias(f):
    goles = v(f, "goals")
    penales = v(f, "penalty_goals")

    normales = max(goles - penales, 0)

    return (
        normales * 6
        + penales * 4.5
        + v(f, "goalAssist") * 3
        - v(f, "ownGoals") * 6
        - v(f, "penaltyMiss") * 4
    )

def atajadas(f):
    return v(f, "saves") * 0.40

def resultado(f):
    favor = v(f, "goals_for_while_playing")
    contra = v(f, "goals_conceded_while_playing")

    pos = str(f["position"]).upper()

    if pos == "G":
        contra_pts = contra * -1.5
    elif pos == "D":
        contra_pts = contra * -1
    else:
        contra_pts = contra * -0.5

    return max(min(favor + contra_pts, 3), -3)

hist["winning"] = (
    hist.apply(participacion, axis=1)
    + hist.apply(pases, axis=1)
    + hist.apply(goles_asistencias, axis=1)
    + hist.apply(atajadas, axis=1)
    + hist.apply(resultado, axis=1)
)

# =========================
# RENDIMIENTO POR 90
# =========================

hist["winning_por90"] = (
    hist["winning"] / hist["minutesPlayed"] * 90
)

# =========================
# PROMEDIO DEL JUGADOR
# =========================

jugadores = (
    hist.groupby(
        ["player_id", "player_name", "position", "team_name"],
        as_index=False
    )
    .agg(
        partidos=("match_id", "count"),
        minutos=("minutesPlayed", "sum"),
        winning_promedio=("winning", "mean"),
        winning_por90=("winning_por90", "mean"),
    )
)

# =========================
# FECHA 10
# =========================

ids_fecha10 = [
    "16667329",
    "16667338",
    "16667328",
    "16667336",
    "16667325",
    "16667327",
    "16667333",
    "16667340",
    "16667330",
    "16667332",
    "16667326",
    "16671623",
    "16667335",
    "16667331",
    "16667337",
]

candidatos = []

for event_id in ids_fecha10:

    archivo = f"datos/partidos/{event_id}.json"

    if not os.path.exists(archivo):
        continue

    with open(archivo, encoding="utf-8") as f:
        partido = json.load(f)

    event = partido["event"]["event"]

    for lado in ["home", "away"]:

        equipo = event[f"{lado}Team"]["name"]

        for p in partido["lineups"][lado]["players"]:

            nombre = p["player"]["name"]
            player_id = p["player"]["id"]

            encontrado = jugadores[
                jugadores["player_id"] == player_id
            ]

            if encontrado.empty:
                continue

            r = encontrado.iloc[0]

            candidatos.append({
                "event_id": event_id,
                "equipo": equipo,
                "jugador": nombre,
                "posicion": r["position"],
                "partidos_hist": int(r["partidos"]),
                "minutos_hist": int(r["minutos"]),
                "promedio": r["winning_promedio"],
                "winning_por90": r["winning_por90"],
            })

cand = pd.DataFrame(candidatos)

# =========================
# PROYECCION
# =========================

# Primera prueba:
# proyectamos 90 minutos para comparar jugadores
cand["proyeccion"] = cand["winning_por90"]

cand = cand.sort_values(
    "proyeccion",
    ascending=False
)

# =========================
# RESULTADOS
# =========================

print()
print("=" * 80)
print("WINNING AI - PRIMERA PRUEBA FECHA 10")
print("=" * 80)

print()
print("TOP 30 CANDIDATOS")
print()

for i, (_, r) in enumerate(cand.head(30).iterrows(), 1):

    print(
        f"{i:2}. "
        f"{r['jugador']} | "
        f"{r['equipo']} | "
        f"{r['posicion']} | "
        f"Partidos: {r['partidos_hist']} | "
        f"Promedio: {r['promedio']:.2f} | "
        f"Pts/90: {r['winning_por90']:.2f}"
    )

# =========================
# TOP POR POSICION
# =========================

print()
print("=" * 80)
print("TOP POR POSICION")
print("=" * 80)

for posicion in ["G", "D", "M", "F"]:

    print()
    print("POSICION", posicion)

    grupo = cand[cand["posicion"] == posicion]

    for i, (_, r) in enumerate(grupo.head(5).iterrows(), 1):

        print(
            f"{i}. {r['jugador']} | "
            f"{r['equipo']} | "
            f"{r['winning_por90']:.2f} pts/90"
        )

# =========================
# GUARDAR
# =========================

cand.to_csv(
    "datos/proyeccion_fecha10.csv",
    index=False,
    encoding="utf-8-sig"
)

print()
print("Archivo generado:")
print("datos/proyeccion_fecha10.csv")