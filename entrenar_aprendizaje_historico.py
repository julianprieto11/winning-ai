"""
Entrenamiento histórico del cerebro de aprendizaje.

Simula las fechas en orden cronológico:
Fecha N -> predicción usando solo memoria de 1..N-1
        -> resultado real de N
        -> actualización de memoria
        -> siguiente fecha

NO utiliza resultados futuros para predecir una fecha anterior.
"""

import argparse
from pathlib import Path

import pandas as pd

import aprendizaje_fecha
import backtest_fecha10 as motor


ROOT = Path(__file__).resolve().parent
DATOS = ROOT / "datos"


def fecha_real_del_round(fecha_numero):
    fechas = aprendizaje_fecha._fechas_de_fecha(fecha_numero)
    if not fechas:
        raise RuntimeError(
            f"No se encontró una fecha real del Clausura para Fecha {fecha_numero}."
        )
    return pd.Timestamp(min(fechas))


def limpiar_memoria():
    for archivo in [
        aprendizaje_fecha.EXPERIENCIA_FILE,
        aprendizaje_fecha.MEMORIA_FILE,
    ]:
        if archivo.exists():
            archivo.unlink()

    print("[HISTÓRICO] Memoria de aprendizaje reiniciada.")


def ejecutar_fecha_historica(numero):
    corte = fecha_real_del_round(numero)

    motor.FECHA_OBJETIVO = int(numero)
    motor.COMPETENCIA_OBJETIVO = "Clausura"
    motor.CORTE_HISTORICO = corte

    # El Modelo C también debe entrenarse solamente con información
    # disponible antes de la fecha que estamos simulando.
    motor.FECHA_CORTE_MODELO_C = corte

    sufijo = f"fecha{int(numero)}"

    motor.SALIDA_CANDIDATOS = f"datos/candidatos_{sufijo}_final.csv"
    motor.SALIDA_EQUIPOS = f"datos/{sufijo}_equipos_predichos.csv"
    motor.SALIDA_EQUIPOS_EXCEL = f"datos/{sufijo}_equipos_predichos_excel.csv"
    motor.SALIDA_EQUIPOS_XLSX = f"datos/{sufijo}_equipos_predichos_excel.xlsx"
    motor.SALIDA_SIMULACIONES = f"datos/{sufijo}_simulaciones.csv"
    motor.SALIDA_TAPADOS = f"datos/{sufijo}_tapados.csv"

    print()
    print("=" * 78)
    print(f"ENTRENAMIENTO HISTÓRICO — FECHA {numero}")
    print("=" * 78)
    print(f"Corte histórico: {corte.date()}")
    print("Memoria disponible: solo fechas anteriores")

    motor.main()

    # Los TAPADOS se integran después del motor principal para no alterar
    # la selección de TITULARES ni FLEX. Luego quedan disponibles para
    # el mismo cierre de aprendizaje de la fecha.
    import integrar_tapados_fecha
    integrar_tapados_fecha.integrar_fecha(numero, corte)

    aprendizaje_fecha.registrar_resultados_fecha(numero)


def resumen():
    experiencia = aprendizaje_fecha._leer_experiencia()
    memoria = aprendizaje_fecha._leer_memoria()

    print()
    print("=" * 78)
    print("RESUMEN DEL APRENDIZAJE")
    print("=" * 78)

    if experiencia.empty:
        print("No hay experiencia registrada.")
    else:
        experiencia["error_abs_base"] = pd.to_numeric(
            experiencia["error_abs_base"], errors="coerce"
        )
        experiencia["error_abs_final"] = pd.to_numeric(
            experiencia["error_abs_final"], errors="coerce"
        )

        resumen_fechas = (
            experiencia.groupby("fecha")
            .agg(
                casos=("player_id", "size"),
                error_base=("error_abs_base", "mean"),
                error_final=("error_abs_final", "mean"),
            )
            .reset_index()
        )

        resumen_fechas["mejora"] = (
            resumen_fechas["error_base"]
            - resumen_fechas["error_final"]
        )

        print(resumen_fechas.to_string(index=False))
        print()
        print(
            "Error medio absoluto BASE:",
            round(experiencia["error_abs_base"].mean(), 4),
        )
        print(
            "Error medio absoluto FINAL:",
            round(experiencia["error_abs_final"].mean(), 4),
        )

    if memoria.empty:
        print()
        print("La memoria todavía no tiene patrones con casos suficientes.")
    else:
        memoria = memoria.sort_values(
            ["casos", "error_abs_medio"],
            ascending=[False, True],
        )

        print()
        print("Patrones aprendidos:", len(memoria))
        print(
            memoria[
                [
                    "patron_tipo",
                    "patron",
                    "casos",
                    "error_medio",
                    "correccion",
                    "consistencia",
                ]
            ]
            .head(30)
            .to_string(index=False)
        )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--desde", type=int, default=1)
    parser.add_argument("--hasta", type=int, default=11)
    parser.add_argument(
        "--reiniciar",
        action="store_true",
        help="Borra la memoria anterior antes de comenzar.",
    )

    args = parser.parse_args()

    if args.desde < 1:
        raise SystemExit("--desde debe ser >= 1.")

    if args.hasta < args.desde:
        raise SystemExit("--hasta debe ser >= --desde.")

    if args.reiniciar:
        limpiar_memoria()

    for numero in range(args.desde, args.hasta + 1):
        ejecutar_fecha_historica(numero)

    resumen()


if __name__ == "__main__":
    main()
