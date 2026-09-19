import pandas as pd

df = pd.read_csv("datos/dataset_jugadores.csv")


# ============================================================
# UTILIDAD
# ============================================================

def valor(fila, columna):
    if columna not in fila.index:
        return 0

    valor = fila[columna]

    if pd.isna(valor):
        return 0

    return valor


# ============================================================
# PARTICIPACIÓN
# ============================================================

def calcular_participacion(fila):

    puntos_minutos = (
        valor(fila, "minutesPlayed") * 0.03
    )

    puntos_duelos = (
        valor(fila, "duelWon") * 0.20
        - valor(fila, "duelLost") * 0.20
    )

    puntos_perdidas = (
        valor(fila, "unsuccessfulTouch") * -0.20
        - valor(fila, "dispossessed") * 0.20
    )

    puntos_progresion = (
        valor(fila, "progressiveBallCarriesCount") * 0.05
    )

    puntos_errores = (
        valor(fila, "errorLeadToAShot") * -1.0
        + valor(fila, "errorLeadToAGoal") * -2.0
    )

    return (
        puntos_minutos
        + puntos_duelos
        + puntos_perdidas
        + puntos_progresion
        + puntos_errores
    )


# ============================================================
# PASES
# ============================================================

def calcular_pases(fila):

    accurate_pass = valor(fila, "accuratePass")
    total_pass = valor(fila, "totalPass")

    if total_pass <= 0:
        return 0

    precision = accurate_pass / total_pass

    puntos_pases = (
        accurate_pass * 0.02
    )

    puntos_campo_rival = (
        valor(fila, "accurateOppositionHalfPasses") * 0.05
    )

    puntos_pases_largos = (
        valor(fila, "accurateLongBalls") * 0.05
    )

    puntos_centros = (
        valor(fila, "accurateCross") * 0.20
    )

    puntos_pases = (
        puntos_pases
        + puntos_campo_rival
        + puntos_pases_largos
        + puntos_centros
    )

    puntos_pases *= precision

    return min(puntos_pases, 4)


# ============================================================
# ATAJADAS
# ============================================================

def calcular_atajadas(fila):

    saves = valor(fila, "saves")

    return saves * 0.40


# ============================================================
# GOLES / ASISTENCIAS
# ============================================================

def calcular_goles_asistencias(fila):

    goles = valor(fila, "goals")
    goles_penal = valor(fila, "penalty_goals")

    goles_normales = max(
        goles - goles_penal,
        0
    )

    puntos_goles_normales = (
        goles_normales * 6.0
    )

    puntos_goles_penal = (
        goles_penal * 4.5
    )

    puntos_goles = (
        puntos_goles_normales
        + puntos_goles_penal
    )

    puntos_asistencias = (
        valor(fila, "goalAssist") * 3.0
    )

    puntos_own_goals = (
        valor(fila, "ownGoals") * -6.0
    )

    puntos_penales_errados = (
        valor(fila, "penaltyMiss") * -4.0
    )

    return (
        puntos_goles
        + puntos_asistencias
        + puntos_own_goals
        + puntos_penales_errados
    )


# ============================================================
# RESULTADO
# ============================================================

def calcular_resultado(fila):

    # --------------------------------------------------------
    # Goles del propio equipo mientras estaba en cancha
    # --------------------------------------------------------

    goles_favor = valor(
        fila,
        "goals_for_while_playing"
    )

    puntos_favor = goles_favor * 1.0


    # --------------------------------------------------------
    # Goles recibidos mientras estaba en cancha
    # --------------------------------------------------------

    goles_contra = valor(
        fila,
        "goals_conceded_while_playing"
    )

    posicion = str(
        fila["position"]
    ).upper()


    if posicion == "G":
        penalizacion_por_gol = 1.5

    elif posicion == "D":
        penalizacion_por_gol = 1.0

    else:
        penalizacion_por_gol = 0.5


    puntos_contra = (
        goles_contra * -penalizacion_por_gol
    )


    # --------------------------------------------------------
    # Resultado total
    # Tope +3 / -3
    # --------------------------------------------------------

    puntos_resultado = (
        puntos_favor
        + puntos_contra
    )

    puntos_resultado = max(
        min(puntos_resultado, 3),
        -3
    )

    return puntos_resultado


# ============================================================
# CALCULAR BLOQUES
# ============================================================

df["puntos_participacion"] = (
    df.apply(
        calcular_participacion,
        axis=1
    )
)

df["puntos_pases"] = (
    df.apply(
        calcular_pases,
        axis=1
    )
)

df["puntos_atajadas"] = (
    df.apply(
        calcular_atajadas,
        axis=1
    )
)

df["puntos_goles_asistencias"] = (
    df.apply(
        calcular_goles_asistencias,
        axis=1
    )
)

df["puntos_resultado"] = (
    df.apply(
        calcular_resultado,
        axis=1
    )
)


# ============================================================
# TOTAL
# ============================================================

df["puntos_winning_v1"] = (
    df["puntos_participacion"]
    + df["puntos_pases"]
    + df["puntos_atajadas"]
    + df["puntos_goles_asistencias"]
    + df["puntos_resultado"]
)


# ============================================================
# RESULTADOS
# ============================================================

columnas = [
    "player_name",
    "team_name",
    "position",
    "minutesPlayed",
    "goals",
    "goalAssist",
    "goals_for_while_playing",
    "goals_conceded_while_playing",
    "ownGoals",
    "penaltyMiss",
    "saves",
    "puntos_participacion",
    "puntos_pases",
    "puntos_atajadas",
    "puntos_goles_asistencias",
    "puntos_resultado",
    "puntos_winning_v1"
]


resultado = df[
    df["minutesPlayed"].notna()
].copy()

resultado = resultado.sort_values(
    "puntos_winning_v1",
    ascending=False
)


# ============================================================
# TOP 20
# ============================================================

print()
print("=" * 110)
print("TOP 20 - WINNING AI V1 + RESULTADO")
print("=" * 110)

print(
    resultado[
        columnas
    ].head(20).to_string(index=False)
)


# ============================================================
# TOP 10 ARQUEROS
# ============================================================

print()
print("=" * 110)
print("TOP 10 ARQUEROS")
print("=" * 110)

print(
    resultado[
        resultado["position"] == "G"
    ][
        columnas
    ].head(10).to_string(index=False)
)


# ============================================================
# TOP 10 GOLEADORES
# ============================================================

print()
print("=" * 110)
print("TOP 10 ACTUACIONES GOLEADORAS")
print("=" * 110)

print(
    resultado[
        resultado["goals"] > 0
    ][
        columnas
    ].head(10).to_string(index=False)
)