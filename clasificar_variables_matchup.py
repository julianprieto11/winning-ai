import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO = "datos/contexto_matchup.csv"

# ============================================================
# CARGAR DATASET
# ============================================================

df = pd.read_csv(ARCHIVO)

print("=" * 80)
print("WINNING AI - CLASIFICACIÓN DE VARIABLES MATCHUP")
print("=" * 80)

print(f"\nFilas: {len(df):,}")
print(f"Columnas: {len(df.columns)}")

# ============================================================
# VARIABLES POST-PARTIDO / LEAKAGE
# ============================================================

POST_PARTIDO = {
    # Resultado / puntuación
    "winning_total",
    "resultado_puntos",
    "bonus_resultado_jugador",
    "valla_invicta",

    # Rendimiento del jugador durante el partido
    "minutos_played",
    "participacion",
    "area_rival",
    "ultimo_tercio",
    "carreras_progresivas",
    "duelos",
    "perdidas",
    "regates_fallidos",
    "exceso_perdidas",
    "pases",
    "peligro_creado",
    "defensa",
    "arquero",
    "goles_asistencias",
    "disciplina",

    # PitchAPI
    "accurate_passes",
    "passes",
    "progressive_passes",
    "precision_pases",
    "passes_into_final_third",
    "long_balls_accurate",
    "accurate_crosses",
    "progressive_carries",
    "take_ons",
    "take_ons_won",
    "failed_dribbles",
    "miscontrols",
    "dispossessed",
    "duels_won",
    "duels_lost",
    "tackles",
    "interceptions",
    "recoveries",
    "clearances",
    "blocks",
    "dribbled_past",
    "shots_on_target",
    "goals",
    "assists",
    "second_assists",
    "chances_created",
    "saves",
    "saved_penalties",
    "goals_conceded",
    "yellow_cards",
    "second_yellow",
    "red_cards_direct",
    "match_finished",

    # SofaScore - rendimiento del partido
    "sofascore_ballPossession",
    "rival_ballPossession",
    "sofascore_totalShotsOnGoal",
    "rival_totalShotsOnGoal",
    "sofascore_shotsOnGoal",
    "rival_shotsOnGoal",
    "sofascore_shotsOffGoal",
    "rival_shotsOffGoal",
    "sofascore_blockedScoringAttempt",
    "rival_blockedScoringAttempt",
    "sofascore_totalShotsInsideBox",
    "rival_totalShotsInsideBox",
    "sofascore_totalShotsOutsideBox",
    "rival_totalShotsOutsideBox",
    "sofascore_expectedGoals",
    "rival_expectedGoals",
    "sofascore_expectedGoalsOnTarget",
    "rival_expectedGoalsOnTarget",
    "sofascore_bigChanceCreated",
    "rival_bigChanceCreated",
    "sofascore_bigChanceMissed",
    "rival_bigChanceMissed",
    "sofascore_touchesInOppBox",
    "rival_touchesInOppBox",
    "sofascore_finalThirdEntries",
    "rival_finalThirdEntries",
    "sofascore_fouledFinalThird",
    "rival_fouledFinalThird",
    "sofascore_cornerKicks",
    "rival_cornerKicks",
    "sofascore_fouls",
    "rival_fouls",
    "sofascore_passes",
    "rival_passes",
    "sofascore_accuratePasses",
    "rival_accuratePasses",
    "sofascore_accurateCross",
    "rival_accurateCross",
    "sofascore_accurateLongBalls",
    "rival_accurateLongBalls",
    "sofascore_duelWonPercent",
    "rival_duelWonPercent",
    "sofascore_dispossessed",
    "rival_dispossessed",
    "sofascore_groundDuelsPercentage",
    "rival_groundDuelsPercentage",
    "sofascore_aerialDuelsPercentage",
    "rival_aerialDuelsPercentage",
    "sofascore_dribblesPercentage",
    "rival_dribblesPercentage",
    "sofascore_wonTacklePercent",
    "rival_wonTacklePercent",
    "sofascore_totalTackle",
    "rival_totalTackle",
    "sofascore_interceptionWon",
    "rival_interceptionWon",
    "sofascore_ballRecovery",
    "rival_ballRecovery",
    "sofascore_totalClearance",
    "rival_totalClearance",
    "sofascore_goalkeeperSaves",
    "rival_goalkeeperSaves",
    "sofascore_freeKicks",
    "rival_freeKicks",
    "sofascore_offsides",
    "rival_offsides",
    "sofascore_yellowCards",
    "rival_yellowCards",
    "sofascore_errorsLeadToShot",
    "rival_errorsLeadToShot",
    "sofascore_errorsLeadToGoal",
    "rival_errorsLeadToGoal",
}

# ============================================================
# VARIABLES PRE-PARTIDO
# ============================================================

PRE_PARTIDO = {
    "match_id",
    "date",
    "round_name",
    "player_id",
    "player_name",
    "team_id",
    "team_name",
    "position",

    "pitchapi_home_team",
    "pitchapi_home_team_id",
    "pitchapi_away_team",
    "pitchapi_away_team_id",
    "pitchapi_fecha",
    "pitchapi_es_local",

    "sofascore_event_id",
    "sofascore_match",

    "rival_team_name",
    "rival_partidos_historicos",

    "matchup_arq",
    "matchup_def",
    "matchup_vol",
    "matchup_del",
    "matchup_score",
    "matchup_variables_usadas",
}

# ============================================================
# CLASIFICAR
# ============================================================

filas = []

for columna in df.columns:

    if columna in POST_PARTIDO:
        categoria = "POST_PARTIDO / LEAKAGE"

    elif columna in PRE_PARTIDO:
        categoria = "PRE_PARTIDO / IDENTIFICACION"

    else:
        categoria = "REVISAR"

    filas.append({
        "variable": columna,
        "categoria": categoria,
        "dtype": str(df[columna].dtype),
        "no_nulos": int(df[columna].notna().sum()),
        "porcentaje_no_nulo": round(df[columna].notna().mean() * 100, 2),
    })

resultado = pd.DataFrame(filas)

# ============================================================
# MOSTRAR
# ============================================================

print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)

print(
    resultado["categoria"]
    .value_counts()
    .to_string()
)

print("\n" + "=" * 80)
print("VARIABLES A REVISAR")
print("=" * 80)

revisar = resultado[
    resultado["categoria"] == "REVISAR"
]

if len(revisar) == 0:
    print("No hay variables pendientes de revisión.")
else:
    print(
        revisar[
            [
                "variable",
                "dtype",
                "no_nulos",
                "porcentaje_no_nulo",
            ]
        ].to_string(index=False)
    )

# ============================================================
# GUARDAR
# ============================================================

salida = "datos/clasificacion_variables_matchup.csv"

resultado.to_csv(
    salida,
    index=False,
    encoding="utf-8-sig"
)

print("\n" + "=" * 80)
print(f"Archivo generado: {salida}")
print("=" * 80)