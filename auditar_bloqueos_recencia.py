import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATOS = ROOT / "datos"


def num(series):
    return pd.to_numeric(series, errors="coerce")


def cargar_candidatos(hasta):
    bloques = []

    for archivo in sorted(DATOS.glob("fecha*_pre_simulacion_candidatos.csv")):
        try:
            fecha = int(archivo.stem.replace("fecha", "").replace("_pre_simulacion_candidatos", ""))
        except ValueError:
            continue

        if fecha > hasta:
            continue

        df = pd.read_csv(archivo, low_memory=False)
        if df.empty or "player_id" not in df.columns:
            continue

        df = df.copy()
        df["fecha"] = fecha
        df["player_id"] = df["player_id"].astype(str).str.replace(r"\.0$", "", regex=True)

        for c in [
            "titulares_ultimos_2",
            "participaciones_ultimos_2",
            "titulares_ultimos_3",
            "participaciones_ultimos_3",
            "titulares_ultimos_4",
            "participaciones_ultimos_4",
            "titular_ultimos_2",
            "titular_2_de_3",
            "elegible_titular_flex",
            "elegible_tapado",
            "activo_tapado_2_de_4_o_3_de_4",
        ]:
            if c not in df.columns:
                df[c] = np.nan

        bloques.append(df)

    if not bloques:
        return pd.DataFrame()

    return pd.concat(bloques, ignore_index=True, sort=False)


def cargar_auditoria():
    archivo = DATOS / "auditoria_ranking_global.csv"
    if not archivo.exists():
        raise FileNotFoundError(
            f"No existe {archivo}. Ejecuta primero auditar_ranking_global.py."
        )

    df = pd.read_csv(archivo, low_memory=False)
    if df.empty:
        return df

    df["player_id"] = df["player_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    df["fecha"] = pd.to_numeric(df["fecha"], errors="coerce")
    df["puntos_reales"] = num(df["puntos_reales"])
    df["rank_final"] = num(df["rank_final"])
    return df


def resumen_bloqueos(fn):
    total = len(fn)
    if total == 0:
        return pd.DataFrame()

    filas = []

    reglas = [
        (
            "TITULAR_FLEX",
            "elegible_titular_flex",
            lambda x: x.fillna(False).astype(bool),
        ),
        (
            "TAPADO",
            "elegible_tapado",
            lambda x: x.fillna(False).astype(bool),
        ),
        (
            "TITULAR_2_ULTIMOS",
            "titular_ultimos_2",
            lambda x: x.fillna(False).astype(bool),
        ),
        (
            "ACTIVO_TAPADO",
            "activo_tapado_2_de_4_o_3_de_4",
            lambda x: x.fillna(False).astype(bool),
        ),
    ]

    for nombre, columna, conv in reglas:
        elegibles = conv(fn[columna])
        filas.append(
            {
                "regla": nombre,
                "casos": total,
                "cumplen": int(elegibles.sum()),
                "no_cumplen": int((~elegibles).sum()),
                "pct_no_cumplen": round(float((~elegibles).mean() * 100), 1),
            }
        )

    for n, columna in [
        (2, "titulares_ultimos_2"),
        (2, "participaciones_ultimos_2"),
        (3, "titulares_ultimos_3"),
        (3, "participaciones_ultimos_3"),
        (4, "titulares_ultimos_4"),
        (4, "participaciones_ultimos_4"),
    ]:
        valores = num(fn[columna])
        filas.append(
            {
                "regla": columna,
                "casos": int(valores.notna().sum()),
                "cumplen": int((valores >= max(1, n // 2)).sum()),
                "no_cumplen": int((valores < max(1, n // 2)).sum()),
                "pct_no_cumplen": round(
                    float((valores < max(1, n // 2)).mean() * 100), 1
                ),
            }
        )

    return pd.DataFrame(filas)


def resumen_por_posicion(fn):
    if fn.empty:
        return pd.DataFrame()

    rows = []
    for posicion, g in fn.groupby("position", dropna=False):
        rows.append(
            {
                "position": posicion,
                "casos": len(g),
                "real_promedio": round(g["puntos_reales"].mean(), 3),
                "titular_flex_no_elegible_pct": round(
                    (~g["elegible_titular_flex"].fillna(False).astype(bool)).mean() * 100, 1
                ),
                "tapado_no_elegible_pct": round(
                    (~g["elegible_tapado"].fillna(False).astype(bool)).mean() * 100, 1
                ),
                "titular_2_ultimos_no_pct": round(
                    (~g["titular_ultimos_2"].fillna(False).astype(bool)).mean() * 100, 1
                ),
                "activo_tapado_no_pct": round(
                    (~g["activo_tapado_2_de_4_o_3_de_4"].fillna(False).astype(bool)).mean() * 100, 1
                ),
                "titulares_ultimos_3_prom": round(num(g["titulares_ultimos_3"]).mean(), 3),
                "participaciones_ultimos_3_prom": round(num(g["participaciones_ultimos_3"]).mean(), 3),
                "titulares_ultimos_4_prom": round(num(g["titulares_ultimos_4"]).mean(), 3),
                "participaciones_ultimos_4_prom": round(num(g["participaciones_ultimos_4"]).mean(), 3),
            }
        )
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hasta", type=int, default=11)
    args = parser.parse_args()

    auditoria = cargar_auditoria()
    candidatos = cargar_candidatos(args.hasta)

    if auditoria.empty or candidatos.empty:
        raise RuntimeError("No hay datos suficientes para auditar.")

    # Falsos negativos reales: puntuaron >=15 y quedaron fuera del Top 10.
    fn = auditoria[
        (auditoria["puntos_reales"] >= 15.0)
        & (auditoria["rank_final"] > 10)
    ].copy()

    # Solo el universo de candidatos, nunca decisiones ya seleccionadas.
    fn = fn[fn["tipo_registro"].eq("CANDIDATO")].copy()

    columnas = [
        "fecha",
        "player_id",
        "player_name",
        "team_name",
        "position",
        "titulares_ultimos_2",
        "participaciones_ultimos_2",
        "titulares_ultimos_3",
        "participaciones_ultimos_3",
        "titulares_ultimos_4",
        "participaciones_ultimos_4",
        "titular_ultimos_2",
        "titular_2_de_3",
        "elegible_titular_flex",
        "elegible_tapado",
        "activo_tapado_2_de_4_o_3_de_4",
    ]
    disponibles = [c for c in columnas if c in candidatos.columns]

    snap = candidatos[disponibles].drop_duplicates(
        ["fecha", "player_id"], keep="last"
    )

    fn = fn.merge(
        snap,
        on=["fecha", "player_id"],
        how="left",
        suffixes=("", "_snapshot"),
    )

    # Preferimos siempre las columnas del snapshot.
    for c in columnas:
        if c in fn.columns and f"{c}_snapshot" in fn.columns:
            fn[c] = fn[f"{c}_snapshot"].combine_first(fn[c])
            fn.drop(columns=[f"{c}_snapshot"], inplace=True)

    salida = DATOS / "auditoria_bloqueos_recencia_falsos_negativos.csv"
    fn.sort_values(["position", "puntos_reales"], ascending=[True, False]).to_csv(
        salida, index=False, encoding="utf-8-sig"
    )

    print("=" * 110)
    print("WINNING AI — AUDITORÍA DE BLOQUEOS POR RECENCIA / MINUTOS")
    print("=" * 110)
    print(f"Fechas: 1 -> {args.hasta}")
    print(f"Falsos negativos reales >=15 fuera del Top 10: {len(fn)}")
    print()

    print("--- CUÁNTOS FALSOS NEGATIVOS ESTABAN BLOQUEADOS POR RECENCIA ---")
    print(
        resumen_bloqueos(fn).to_string(index=False)
        if not fn.empty
        else "Sin falsos negativos."
    )
    print()

    print("--- FALSOS NEGATIVOS POR POSICIÓN ---")
    print(
        resumen_por_posicion(fn).to_string(index=False)
        if not fn.empty
        else "Sin falsos negativos."
    )
    print()

    cols_mostrar = [
        "fecha",
        "position",
        "player_name",
        "team_name",
        "puntos_reales",
        "prediccion_final",
        "rank_final",
        "titulares_ultimos_2",
        "participaciones_ultimos_2",
        "titulares_ultimos_3",
        "participaciones_ultimos_3",
        "titulares_ultimos_4",
        "participaciones_ultimos_4",
        "elegible_titular_flex",
        "elegible_tapado",
    ]
    cols_mostrar = [c for c in cols_mostrar if c in fn.columns]

    print("--- FALSOS NEGATIVOS: DETALLE ---")
    print(
        fn.sort_values("puntos_reales", ascending=False)[cols_mostrar]
        .head(60)
        .to_string(index=False)
    )

    print()
    print(f"Archivo generado: {salida}")
    print("AUDITORÍA TERMINADA — NO MODIFICA EL MOTOR.")


if __name__ == "__main__":
    main()
