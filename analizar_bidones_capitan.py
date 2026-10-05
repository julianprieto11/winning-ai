import argparse
import os
import numpy as np
import pandas as pd

DATASET_DEFAULT = "datos/dataset_winning_pitchapi.csv"
OUTPUT_DEFAULT = "datos/analisis_bidones_capitan.xlsx"


def num(df, col, default=0.0):
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").fillna(default)
    return pd.Series(default, index=df.index, dtype=float)


def first_existing(df, names):
    for name in names:
        if name in df.columns:
            return name
    return None


def calcular_capitan(df):
    out = df.copy()

    goles = num(out, "goals")
    assists = num(out, "assists")
    shots = num(out, "shots_on_target")
    chances = num(out, "chances_created")
    big_created_col = first_existing(
        out,
        ["big_chance_created", "big_chance_created_team_title"]
    )
    big_created = num(out, big_created_col) if big_created_col else num(out, "__none__")

    # En el motor Winning AI actual, remates al arco sin gol aportan
    # 0.60 puntos cada uno dentro de Peligro Creado.
    shots_without_goal = np.maximum(0, shots - goles)
    danger_shots = shots_without_goal * 0.60

    # Las asistencias no vuelven a contar como pase clave.
    key_passes_without_assist = np.maximum(0, chances - assists)
    danger_key_passes = key_passes_without_assist * 0.50
    danger_big_chances = big_created * 1.50

    danger_delta = (
        danger_shots
        + danger_key_passes
        + danger_big_chances
    )

    valla = num(out, "valla_invicta")
    disciplina = num(out, "disciplina")

    # Capitán: +3 por partido completo.
    # Para histórico usamos >=90 min como proxy de partido completo.
    full_match = (num(out, "minutes_played") >= 90).astype(float)
    full_match_delta = full_match * 3.0

    goal_delta = goles * 2.0
    assist_delta = assists * 1.0

    # El reglamento indica que las tarjetas se duplican.
    # Por eso la ganancia incremental es igual al castigo/base
    # ya registrado en disciplina (normalmente <= 0).
    cards_delta = disciplina

    clean_sheet_delta = valla

    out["capitan_bonus_partido_completo"] = full_match_delta
    out["capitan_bonus_goles"] = goal_delta
    out["capitan_bonus_asistencias"] = assist_delta
    out["capitan_extra_peligro"] = danger_delta
    out["capitan_extra_valla_invicta"] = clean_sheet_delta
    out["capitan_extra_tarjetas"] = cards_delta

    out["capitan_delta"] = (
        full_match_delta
        + goal_delta
        + assist_delta
        + danger_delta
        + clean_sheet_delta
        + cards_delta
    )

    out["winning_con_capitan"] = (
        num(out, "winning_total")
        + out["capitan_delta"]
    )

    return out


def calcular_bidones(df):
    out = df.copy()

    pos = (
        out["position"].astype(str).str.upper()
        if "position" in out.columns
        else pd.Series("", index=out.index)
    )

    recoveries = num(out, "recoveries")
    dispossessed = num(out, "dispossessed")
    take_ons_won = num(out, "take_ons_won")

    out["bidon_lirico"] = np.where(
        take_ons_won >= 3,
        3.0,
        0.0,
    )

    # El reglamento define pérdidas del Recuperador como aquellas
    # donde el rival le quita la pelota. En PitchAPI, dispossessed
    # es la variable disponible que representa esa acción.
    out["bidon_recuperador"] = np.where(
        pos.isin(["DEF", "VOL", "DEL"]),
        np.maximum(0, recoveries - dispossessed) / 5.0,
        0.0,
    )

    out["bidon_mejor_medible"] = out[
        ["bidon_lirico", "bidon_recuperador"]
    ].max(axis=1)

    out["bidon_mejor_nombre"] = np.where(
        out["bidon_recuperador"] > out["bidon_lirico"],
        "RECUPERADOR",
        np.where(
            out["bidon_lirico"] > 0,
            "LÍRICO",
            "",
        ),
    )

    out["winning_con_mejor_bidon_medible"] = (
        num(out, "winning_total")
        + out["bidon_mejor_medible"]
    )

    return out


def construir_disponibilidad(df):
    columnas = set(df.columns)

    checks = [
        (
            "CAPITÁN",
            "Disponible",
            [
                "winning_total",
                "minutes_played",
                "goals",
                "assists",
                "shots_on_target",
                "chances_created",
                "valla_invicta",
                "disciplina",
            ],
        ),
        (
            "LÍRICO",
            "Disponible",
            ["take_ons_won"],
        ),
        (
            "RECUPERADOR",
            "Disponible",
            ["recoveries", "dispossessed", "position"],
        ),
        (
            "AGUA BENDITA",
            "Parcial",
            ["yellow_cards", "second_yellow", "red_cards_direct"],
        ),
        (
            "RÚSTICO",
            "Pendiente",
            ["fouls_committed"],
        ),
        (
            "LEY DEL EX",
            "Pendiente",
            [],
        ),
        (
            "DEL SUPLENTE",
            "Pendiente",
            ["is_starter"],
        ),
        (
            "PELOTA PARADA",
            "Pendiente",
            [],
        ),
    ]

    rows = []

    for nombre, estado_base, required in checks:
        faltantes = [c for c in required if c not in columnas]

        if estado_base == "Disponible":
            estado = "DISPONIBLE" if not faltantes else "PENDIENTE"
        elif estado_base == "Parcial":
            estado = "PARCIAL" if not faltantes else "PARCIAL / FALTAN DATOS"
        else:
            estado = estado_base

        rows.append({
            "mecanica": nombre,
            "estado": estado,
            "columnas_disponibles": ", ".join(c for c in required if c in columnas),
            "columnas_faltantes": ", ".join(faltantes),
        })

    return pd.DataFrame(rows)


def resumen_por_jugador(df):
    keys = [
        c for c in ["player_id", "player_name", "position", "team_name"]
        if c in df.columns
    ]

    agg = (
        df.groupby(keys, dropna=False)
        .agg(
            partidos=("winning_total", "size"),
            winning_promedio=("winning_total", "mean"),
            capitan_delta_promedio=("capitan_delta", "mean"),
            capitan_delta_p90=("capitan_delta", lambda s: s.quantile(0.90)),
            capitan_activacion=("capitan_delta", lambda s: (s > 0).mean()),
            mejor_bidon_promedio=("bidon_mejor_medible", "mean"),
            mejor_bidon_p90=("bidon_mejor_medible", lambda s: s.quantile(0.90)),
            mejor_bidon_activacion=("bidon_mejor_medible", lambda s: (s > 0).mean()),
        )
        .reset_index()
    )

    agg["winning_promedio_con_capitan"] = (
        agg["winning_promedio"] + agg["capitan_delta_promedio"]
    )
    agg["winning_promedio_con_mejor_bidon_medible"] = (
        agg["winning_promedio"] + agg["mejor_bidon_promedio"]
    )

    return agg.sort_values(
        ["capitan_delta_promedio", "winning_promedio"],
        ascending=False,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Analiza impacto histórico de Capitán y Bidones sin modificar el optimizador."
    )
    parser.add_argument(
        "--dataset",
        default=DATASET_DEFAULT,
        help="CSV histórico Winning AI",
    )
    parser.add_argument(
        "--salida",
        default=OUTPUT_DEFAULT,
        help="Excel de salida",
    )
    args = parser.parse_args()

    if not os.path.exists(args.dataset):
        raise FileNotFoundError(
            f"No existe el dataset: {args.dataset}"
        )

    df = pd.read_csv(args.dataset, low_memory=False)

    required = ["winning_total", "player_name"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "Faltan columnas obligatorias: " + ", ".join(missing)
        )

    df["winning_total"] = pd.to_numeric(
        df["winning_total"], errors="coerce"
    )
    df = df.dropna(subset=["winning_total"]).copy()

    df = calcular_capitan(df)
    df = calcular_bidones(df)

    disponibilidad = construir_disponibilidad(df)
    resumen = resumen_por_jugador(df)

    detalle = df[
        [
            c for c in [
                "date",
                "match_id",
                "player_id",
                "player_name",
                "team_name",
                "position",
                "minutes_played",
                "winning_total",
                "capitan_bonus_partido_completo",
                "capitan_bonus_goles",
                "capitan_bonus_asistencias",
                "capitan_extra_peligro",
                "capitan_extra_valla_invicta",
                "capitan_extra_tarjetas",
                "capitan_delta",
                "winning_con_capitan",
                "take_ons_won",
                "recoveries",
                "dispossessed",
                "bidon_lirico",
                "bidon_recuperador",
                "bidon_mejor_nombre",
                "bidon_mejor_medible",
                "winning_con_mejor_bidon_medible",
            ]
            if c in df.columns
        ]
    ].copy()

    os.makedirs(os.path.dirname(args.salida) or ".", exist_ok=True)

    with pd.ExcelWriter(args.salida, engine="openpyxl") as writer:
        resumen.to_excel(
            writer,
            sheet_name="RESUMEN_JUGADORES",
            index=False,
        )
        detalle.to_excel(
            writer,
            sheet_name="DETALLE_HISTORICO",
            index=False,
        )
        disponibilidad.to_excel(
            writer,
            sheet_name="DISPONIBILIDAD",
            index=False,
        )

    print("=" * 80)
    print("ANÁLISIS BIDONES + CAPITÁN")
    print("=" * 80)
    print(f"Registros analizados: {len(df):,}")
    print(f"Jugadores únicos: {df['player_name'].nunique():,}")
    print()
    print("CAPITÁN")
    print(
        f"Delta promedio por actuación: "
        f"{df['capitan_delta'].mean():.3f}"
    )
    print(
        f"Delta P90: "
        f"{df['capitan_delta'].quantile(0.90):.3f}"
    )
    print(
        f"Máximo histórico: "
        f"{df['capitan_delta'].max():.3f}"
    )
    print()
    print("BIDONES MEDIBLES")
    print(
        f"Bonus promedio: "
        f"{df['bidon_mejor_medible'].mean():.3f}"
    )
    print(
        f"Bonus P90: "
        f"{df['bidon_mejor_medible'].quantile(0.90):.3f}"
    )
    print(
        f"Máximo histórico: "
        f"{df['bidon_mejor_medible'].max():.3f}"
    )
    print()
    print(f"Excel generado: {args.salida}")


if __name__ == "__main__":
    main()
