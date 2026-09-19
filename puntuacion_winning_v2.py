import pandas as pd
import numpy as np


# ============================================================
# CONFIGURACIÓN
# ============================================================

ENTRADA = "datos/dataset_jugadores.csv"
SALIDA = "datos/dataset_winning_v2.csv"


# ============================================================
# CARGAR DATASET
# ============================================================

df = pd.read_csv(ENTRADA)


# ============================================================
# UTILIDADES
# ============================================================

def v(fila, columna):
    """
    Devuelve 0 cuando el dato realmente está ausente.
    Un 0 existente sigue siendo 0.
    """
    if columna not in fila.index:
        return 0

    valor = fila[columna]

    if pd.isna(valor):
        return 0

    return float(valor)


def posicion(fila):
    return str(fila.get("position", "")).upper()


# ============================================================
# 1. PARTICIPACIÓN
# ============================================================

def calcular_participacion(fila):

    puntos = 0

    # Minutos
    puntos += v(fila, "minutesPlayed") * 0.03

    # Duelo ganado / perdido
    puntos += v(fila, "duelWon") * 0.20
    puntos -= v(fila, "duelLost") * 0.20

    # Mal control
    puntos -= v(fila, "unsuccessfulTouch") * 0.20

    # Disposición / pérdida por ser despojado
    puntos -= v(fila, "dispossessed") * 0.20

    # Conducción progresiva
    puntos += v(fila, "progressiveBallCarriesCount") * 0.05

    return puntos


# ============================================================
# 2. ERRORES
# ============================================================

def calcular_errores(fila):

    puntos = 0

    # Error que termina en remate
    puntos -= v(fila, "errorLeadToAShot") * 1.0

    # Error que termina en gol
    puntos -= v(fila, "errorLeadToAGoal") * 2.0

    return puntos


# ============================================================
# 3. PASES
# ============================================================

def calcular_pases(fila):

    pases = v(fila, "totalPass")
    pases_accurate = v(fila, "accuratePass")

    if pases <= 0:
        return 0

    precision = pases_accurate / pases

    puntos = 0

    # Pases precisos
    puntos += pases_accurate * 0.02

    # Pases hacia adelante precisos
    #
    # Este dato será incorporado cuando esté disponible
    # en el dataset final.
    if "progressive_passes" in fila.index:
        puntos += v(fila, "progressive_passes") * 0.02

    # Pases al último tercio
    puntos += v(fila, "accurateOppositionHalfPasses") * 0.05

    # Pases largos precisos
    puntos += v(fila, "accurateLongBalls") * 0.05

    # Centros precisos
    puntos += v(fila, "accurateCross") * 0.20

    # Precisión general
    puntos *= precision

    # TOPE DE PASES
    return min(puntos, 4.0)


# ============================================================
# 4. PELIGRO CREADO
# ============================================================

def calcular_peligro(fila):

    puntos = 0

    goles = v(fila, "goals")

    # --------------------------------------------------------
    # Remate al arco que NO termina en gol
    # +0.6
    # --------------------------------------------------------

    remates_arco = v(fila, "onTargetScoringAttempt")

    remates_arco_sin_gol = max(
        remates_arco - goles,
        0
    )

    puntos += remates_arco_sin_gol * 0.6


    # --------------------------------------------------------
    # Remate peligroso
    #
    # No existe actualmente en nuestro dataset.
    # --------------------------------------------------------


    # --------------------------------------------------------
    # Pase clave SIN asistencia
    # +0.5
    # --------------------------------------------------------

    pases_clave = v(fila, "keyPass")
    asistencias = v(fila, "goalAssist")

    pases_clave_sin_asistencia = max(
        pases_clave - asistencias,
        0
    )

    puntos += pases_clave_sin_asistencia * 0.5


    # --------------------------------------------------------
    # Ocasión clara creada
    # +1.5
    # --------------------------------------------------------

    puntos += v(fila, "bigChanceCreated") * 1.5


    # --------------------------------------------------------
    # Ocasión clara errada
    # -1
    # --------------------------------------------------------

    puntos -= v(fila, "bigChanceMissed") * 1.0


    # --------------------------------------------------------
    # Remate al palo
    # +0.6
    # --------------------------------------------------------

    puntos += v(fila, "hitWoodwork") * 0.6


    # --------------------------------------------------------
    # Regate ganado
    # +0.6
    # --------------------------------------------------------

    if "dribbles_succeeded" in fila.index:
        puntos += v(fila, "dribbles_succeeded") * 0.6


    # --------------------------------------------------------
    # Penal errado
    # -4
    # --------------------------------------------------------

    puntos -= v(fila, "penaltyMiss") * 4.0


    # --------------------------------------------------------
    # Offside
    # -0.2
    # --------------------------------------------------------

    puntos -= v(fila, "totalOffside") * 0.2


    # --------------------------------------------------------
    # TOPE DE ACCIONES OFENSIVAS
    # --------------------------------------------------------

    return min(puntos, 7.0)


# ============================================================
# 5. DEFENSA
# ============================================================

def calcular_defensa(fila):

    puntos = 0

    # Entrada ganada
    puntos += v(fila, "wonTackle") * 0.5

    # Intercepción
    puntos += v(fila, "interceptionWon") * 0.4

    # Recuperación
    puntos += v(fila, "ballRecovery") * 0.2

    # Despeje
    puntos += v(fila, "totalClearance") * 0.12

    # Remate bloqueado
    puntos += v(fila, "blockedScoringAttempt") * 0.5

    # Ser regateado
    puntos -= v(fila, "challengeLost") * 0.3

    # --------------------------------------------------------
    # VALLA INVICTA
    # --------------------------------------------------------

    minutos = v(fila, "minutesPlayed")
    pos = posicion(fila)

    if pos == "D":
        if v(fila, "team_clean_sheet") == 1:
            puntos += (minutos / 90) * 1.0

        puntos -= v(
            fila,
            "goals_conceded_while_playing"
        ) * 0.5


    # --------------------------------------------------------
    # TOPE DE ACCIONES DEFENSIVAS
    #
    # El bloque defensivo de acciones se limita a +8.
    # La valla invicta / goles recibidos se mantienen
    # como componente separado.
    # --------------------------------------------------------

    acciones = (
        v(fila, "wonTackle") * 0.5
        + v(fila, "interceptionWon") * 0.4
        + v(fila, "ballRecovery") * 0.2
        + v(fila, "totalClearance") * 0.12
        + v(fila, "blockedScoringAttempt") * 0.5
        - v(fila, "challengeLost") * 0.3
    )

    acciones = min(acciones, 8.0)

    contexto = 0

    if pos == "D":

        if v(fila, "team_clean_sheet") == 1:
            contexto += (minutos / 90) * 1.0

        contexto -= (
            v(fila, "goals_conceded_while_playing")
            * 0.5
        )

    return acciones + contexto


# ============================================================
# 6. ARQUERO
# ============================================================

def calcular_arquero(fila):

    if posicion(fila) != "G":
        return 0

    puntos = 0

    minutos = v(fila, "minutesPlayed")

    # Atajada
    puntos += v(fila, "saves") * 0.4

    # Valla invicta
    if v(fila, "team_clean_sheet") == 1:
        puntos += (minutos / 90) * 2.0

    # Gol recibido
    puntos -= (
        v(fila, "goals_conceded_while_playing")
        * 1.0
    )

    return puntos


# ============================================================
# 7. GOLES Y ASISTENCIAS
# ============================================================

def calcular_goles_asistencias(fila):

    goles = v(fila, "goals")
    penales = v(fila, "penalty_goals")

    goles_normales = max(
        goles - penales,
        0
    )

    puntos = 0

    # Gol normal
    puntos += goles_normales * 6.0

    # Gol de penal
    puntos += penales * 4.5

    # Asistencia
    puntos += v(fila, "goalAssist") * 3.0

    # Gol en contra
    puntos -= v(fila, "ownGoals") * 6.0

    # Penal errado
    puntos -= v(fila, "penaltyMiss") * 4.0

    return puntos


# ============================================================
# 8. RESULTADO DEL PARTIDO
# ============================================================

def calcular_resultado(fila):

    resultado = str(
        fila.get("result", "")
    ).lower()

    if resultado in ("win", "w", "ganado"):
        return 3.0

    if resultado in ("draw", "d", "empate"):
        return 1.0

    return 0.0


# ============================================================
# 9. DISCIPLINA
# ============================================================

def calcular_disciplina(fila):

    # La clasificación de roja directa / doble amarilla
    # ya está almacenada en el dataset.
    #
    # Por ahora dejamos este bloque separado para no
    # inventar equivalencias con eventos que no tengan
    # correspondencia exacta con las reglas Winning.

    return v(fila, "discipline_points")


# ============================================================
# CALCULAR TODO
# ============================================================

print()
print("=" * 80)
print("CALCULANDO WINNING V2")
print("=" * 80)
print()

df["puntos_participacion"] = df.apply(
    calcular_participacion,
    axis=1
)

df["puntos_errores"] = df.apply(
    calcular_errores,
    axis=1
)

df["puntos_pases"] = df.apply(
    calcular_pases,
    axis=1
)

df["puntos_peligro"] = df.apply(
    calcular_peligro,
    axis=1
)

df["puntos_defensa"] = df.apply(
    calcular_defensa,
    axis=1
)

df["puntos_arquero"] = df.apply(
    calcular_arquero,
    axis=1
)

df["puntos_goles_asistencias"] = df.apply(
    calcular_goles_asistencias,
    axis=1
)

df["puntos_resultado"] = df.apply(
    calcular_resultado,
    axis=1
)

df["puntos_disciplina"] = df.apply(
    calcular_disciplina,
    axis=1
)


# ============================================================
# TOTAL
# ============================================================

columnas_puntos = [
    "puntos_participacion",
    "puntos_errores",
    "puntos_pases",
    "puntos_peligro",
    "puntos_defensa",
    "puntos_arquero",
    "puntos_goles_asistencias",
    "puntos_resultado",
    "puntos_disciplina",
]

df["winning_v2"] = df[columnas_puntos].sum(axis=1)


# ============================================================
# WINNING POR 90
# ============================================================

df["winning_por90_v2"] = np.where(
    df["minutesPlayed"] > 0,
    df["winning_v2"] / df["minutesPlayed"] * 90,
    np.nan
)


# ============================================================
# GUARDAR
# ============================================================

df.to_csv(
    SALIDA,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# RESUMEN
# ============================================================

print(f"Filas procesadas: {len(df)}")
print(f"Columnas finales: {len(df.columns)}")
print()
print(f"Archivo generado: {SALIDA}")
print()

print("Promedio Winning V2:")
print(
    df["winning_v2"].mean()
)

print()
print("Top 20 actuaciones:")
print(
    df[
        [
            "player_name",
            "team_name",
            "position",
            "minutesPlayed",
            "winning_v2",
            "winning_por90_v2",
        ]
    ]
    .sort_values("winning_v2", ascending=False)
    .head(20)
    .to_string(index=False)
)

print()