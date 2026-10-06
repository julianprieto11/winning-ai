import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DATOS = Path("datos")
EXPERIENCIA = DATOS / "aprendizaje_predicciones.csv"


def numero(serie):
    return pd.to_numeric(serie, errors="coerce")


def main():
    parser = argparse.ArgumentParser(
        description="Audita el aprendizaje histórico de WINNING AI."
    )
    parser.add_argument("--hasta", type=int, default=None)
    parser.add_argument(
        "--umbral-falso-negativo",
        type=float,
        default=12.0,
        help="Puntos reales mínimos para considerar un falso negativo.",
    )
    args = parser.parse_args()

    if not EXPERIENCIA.exists():
        raise SystemExit(f"No existe {EXPERIENCIA}.")

    df = pd.read_csv(EXPERIENCIA, low_memory=False)
    if df.empty:
        raise SystemExit("El archivo de aprendizaje está vacío.")

    df["fecha"] = numero(df["fecha"])
    df["prediccion_base"] = numero(df["prediccion_base"])
    df["prediccion_final"] = numero(df["prediccion_final"])
    df["puntos_reales"] = numero(df["puntos_reales"])

    if args.hasta is not None:
        df = df[df["fecha"] <= args.hasta].copy()

    df = df.dropna(subset=["prediccion_base", "puntos_reales"]).copy()
    if df.empty:
        raise SystemExit("No hay registros numéricos para auditar.")

    df["error_base"] = df["puntos_reales"] - df["prediccion_base"]
    df["error_final"] = df["puntos_reales"] - df["prediccion_final"]
    df["abs_base"] = df["error_base"].abs()
    df["abs_final"] = df["error_final"].abs()

    print("=" * 90)
    print("WINNING AI - AUDITORÍA DEL APRENDIZAJE")
    print("=" * 90)
    print(f"Registros: {len(df)}")
    print(f"Fechas: {int(df['fecha'].min())} -> {int(df['fecha'].max())}")
    print()

    mae_base = df["abs_base"].mean()
    mae_final = df["abs_final"].mean()

    print(f"MAE BASE : {mae_base:.3f}")
    print(f"MAE FINAL: {mae_final:.3f}")
    print(
        f"Mejora MAE: {((mae_base - mae_final) / mae_base * 100):.2f}%"
        if mae_base
        else "Mejora MAE: n/a"
    )

    if len(df) >= 3:
        corr = df[["prediccion_final", "puntos_reales"]].corr().iloc[0, 1]
        print(f"Correlación predicción/real: {corr:.3f}")

    print()
    print("--- POR TIPO DE REGISTRO ---")
    resumen = (
        df.groupby("tipo_registro", dropna=False)
        .agg(
            casos=("puntos_reales", "size"),
            mae_base=("abs_base", "mean"),
            mae_final=("abs_final", "mean"),
            real_promedio=("puntos_reales", "mean"),
            pred_promedio=("prediccion_final", "mean"),
        )
        .sort_values("casos", ascending=False)
    )
    print(resumen.round(3).to_string())

    print()
    print("--- FALSOS NEGATIVOS ---")
    # Jugadores que el sistema subestimó fuertemente.
    fn = df[
        df["puntos_reales"] >= args.umbral_falso_negativo
    ].copy()
    fn["subestimacion"] = fn["puntos_reales"] - fn["prediccion_final"]
    fn = fn.sort_values(
        ["subestimacion", "puntos_reales"],
        ascending=False
    )

    columnas = [
        "fecha",
        "player_name",
        "team_name",
        "position",
        "tipo_registro",
        "perfil",
        "prediccion_base",
        "prediccion_final",
        "puntos_reales",
        "subestimacion",
    ]
    columnas = [c for c in columnas if c in fn.columns]
    if fn.empty:
        print("No se encontraron falsos negativos con ese umbral.")
    else:
        print(fn[columnas].head(30).round(3).to_string(index=False))

    print()
    print("--- MAYORES SOBREESTIMACIONES ---")
    fp = df.sort_values("error_final").copy()
    columnas_fp = [c for c in columnas if c in fp.columns]
    print(fp[columnas_fp].head(20).round(3).to_string(index=False))

    print()
    print("--- TOP REAL POR FECHA ---")
    top = (
        df.sort_values(
            ["fecha", "puntos_reales"],
            ascending=[True, False]
        )
        .groupby("fecha", as_index=False)
        .head(10)
    )
    cols_top = [
        "fecha",
        "player_name",
        "team_name",
        "position",
        "prediccion_final",
        "puntos_reales",
    ]
    cols_top = [c for c in cols_top if c in top.columns]
    print(top[cols_top].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
