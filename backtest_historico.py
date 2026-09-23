import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO = "datos/backtest_dataset.csv"

# Dos pruebas históricas:
# PRUEBA 1: entrenar hasta mayo -> predecir julio
# PRUEBA 2: entrenar hasta agosto -> predecir septiembre

PRUEBAS = [
    {
        "nombre": "MAYO -> JULIO",
        "fin_entrenamiento": "2026-05-31",
        "inicio_test": "2026-07-01",
        "fin_test": "2026-07-31",
    },
    {
        "nombre": "AGOSTO -> SEPTIEMBRE",
        "fin_entrenamiento": "2026-08-31",
        "inicio_test": "2026-09-01",
        "fin_test": "2026-09-30",
    },
]


# ============================================================
# MODELO
# ============================================================

def crear_modelo(columnas_numericas, columnas_categoricas):

    preprocesador = ColumnTransformer(
        transformers=[
            (
                "numericas",
                Pipeline([
                    ("imputer", SimpleImputer(strategy="median")),
                ]),
                columnas_numericas,
            ),
            (
                "categoricas",
                Pipeline([
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(
                        handle_unknown="ignore",
                        sparse_output=False
                    )),
                ]),
                columnas_categoricas,
            ),
        ],
        remainder="drop",
    )

    modelo = HistGradientBoostingRegressor(
        max_iter=300,
        learning_rate=0.05,
        max_leaf_nodes=31,
        l2_regularization=1.0,
        random_state=42,
    )

    return Pipeline([
        ("preprocesador", preprocesador),
        ("modelo", modelo),
    ])


# ============================================================
# VARIABLES
# ============================================================

def seleccionar_variables(df):

    # Columnas que NO deben entrar al modelo.
    # Incluyen IDs, target y variables que pueden generar leakage.
    excluir = {
        "winning_total",
        "date",
        "match_id",
        "player_id",
        "team_id",
        "team_name",
        "player_name",
        "rival_team_id",
        "rival_team_name",
        "round_name",
    }

    # Leakage / información del partido que estamos intentando predecir.
    patrones_excluir = [
        "current_",
        "post_",
        "resultado_",
        "ganador_",
    ]

    variables = []

    for col in df.columns:

        if col in excluir:
            continue

        col_lower = col.lower()

        if any(patron in col_lower for patron in patrones_excluir):
            continue

        variables.append(col)

    # position es la única categórica que utilizamos.
    categoricas = []

    if "position" in variables:
        categoricas.append("position")

    numericas = [
        col for col in variables
        if col not in categoricas
        and pd.api.types.is_numeric_dtype(df[col])
    ]

    return numericas, categoricas


# ============================================================
# MÉTRICAS
# ============================================================

def calcular_metricas(y_real, y_pred):

    mae = mean_absolute_error(y_real, y_pred)

    rmse = np.sqrt(
        mean_squared_error(y_real, y_pred)
    )

    r2 = r2_score(y_real, y_pred)

    correlacion = np.corrcoef(
        y_real,
        y_pred
    )[0, 1]

    return {
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
        "Correlacion": correlacion,
    }


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("WINNING AI - BACKTEST HISTÓRICO")
print("=" * 70)

print("\nCargando dataset...")

df = pd.read_csv(ARCHIVO)

df["date"] = pd.to_datetime(df["date"])

print(f"Filas totales: {len(df):,}")
print(
    f"Fecha inicial: {df['date'].min().date()}"
)
print(
    f"Fecha final:   {df['date'].max().date()}"
)


# ============================================================
# DEFINIR MODELOS A / B / C
# ============================================================

# BASE = historial de jugadores + historial de minutos
columnas_historial = [
    col for col in df.columns
    if col.startswith("prom_ultimos_5_")
    or col == "partidos_historial"
]

columnas_minutos = [
    "minutos_promedio_historico",
    "partidos_historicos_minutos",
    "minutos_promedio_ultimos_5",
]

base_columns = (
    columnas_historial
    + columnas_minutos
)

base_columns = [
    c for c in base_columns
    if c in df.columns
]

base_columns = list(dict.fromkeys(base_columns))


# CONTEXTO = historial propio + historial rival
context_columns_final = [
    col for col in df.columns
    if col.startswith("historico_")
    or col.startswith("rival_historico_")
]

context_columns_final = list(
    dict.fromkeys(context_columns_final)
)


# MATCHUP = diferencias + ratios + interacciones
matchup_columns = [
    col for col in df.columns
    if col.startswith("matchup_")
]

matchup_columns = list(
    dict.fromkeys(matchup_columns)
)


# ============================================================
# EVITAR TARGET LEAKAGE
# ============================================================

columnas_prohibidas = [
    "winning_total",
    "minutes_played",
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
    "resultado_puntos",
    "bonus_resultado_jugador",
    "valla_invicta",
]

base_columns = [
    c for c in base_columns
    if c not in columnas_prohibidas
]

context_columns_final = [
    c for c in context_columns_final
    if c not in columnas_prohibidas
]

matchup_columns = [
    c for c in matchup_columns
    if c not in columnas_prohibidas
]


# ============================================================
# GRUPOS DE MODELOS
# ============================================================

grupos = {
    "A - BASE": base_columns,
    "B - BASE + CONTEXTO":
        base_columns + context_columns_final,
    "C - BASE + CONTEXTO + MATCHUP":
        base_columns
        + context_columns_final
        + matchup_columns,
}


# position forma parte de la identificación
# y se incorpora como variable categórica
for nombre in grupos:

    if "position" in df.columns:
        grupos[nombre] = list(
            dict.fromkeys(
                grupos[nombre] + ["position"]
            )
        )


print("\nVariables detectadas:")
print(f"BASE:      {len(base_columns)}")
print(f"CONTEXTO:  {len(context_columns_final)}")
print(f"MATCHUP:   {len(matchup_columns)}")


# ============================================================
# VALIDAR VARIABLES
# ============================================================

resultados = []


for prueba in PRUEBAS:

    nombre_prueba = prueba["nombre"]

    fin_entrenamiento = pd.Timestamp(
        prueba["fin_entrenamiento"]
    )

    inicio_test = pd.Timestamp(
        prueba["inicio_test"]
    )

    fin_test = pd.Timestamp(
        prueba["fin_test"]
    )

    train = df[
        df["date"] <= fin_entrenamiento
    ].copy()

    test = df[
        (df["date"] >= inicio_test)
        & (df["date"] <= fin_test)
    ].copy()

    print("\n")
    print("=" * 70)
    print(nombre_prueba)
    print("=" * 70)

    print(
        f"TRAIN: {train['date'].min().date()} "
        f"-> {train['date'].max().date()}"
    )

    print(
        f"TEST:  {test['date'].min().date()} "
        f"-> {test['date'].max().date()}"
    )

    print(f"Filas TRAIN: {len(train):,}")
    print(f"Filas TEST:  {len(test):,}")

    y_train = train["winning_total"]
    y_test = test["winning_total"]


    # ========================================================
    # A / B / C
    # ========================================================

    for nombre_modelo, variables in grupos.items():

        variables_validas = [
            col for col in variables
            if col in train.columns
        ]

        if not variables_validas:
            print(
                f"\n{nombre_modelo}: "
                f"NO HAY VARIABLES"
            )
            continue

        categoricas = [
            col for col in variables_validas
            if col == "position"
        ]

        numericas = [
            col for col in variables_validas
            if col not in categoricas
            and pd.api.types.is_numeric_dtype(
                train[col]
            )
        ]

        X_train = train[
            numericas + categoricas
        ]

        X_test = test[
            numericas + categoricas
        ]

        print("\n" + "-" * 70)
        print(nombre_modelo)
        print("-" * 70)

        print(
            f"Variables utilizadas: "
            f"{len(numericas) + len(categoricas)}"
        )

        modelo = crear_modelo(
            numericas,
            categoricas
        )

        modelo.fit(
            X_train,
            y_train
        )

        predicciones = modelo.predict(
            X_test
        )

        metricas = calcular_metricas(
            y_test,
            predicciones
        )

        print(
            f"MAE:         {metricas['MAE']:.4f}"
        )

        print(
            f"RMSE:        {metricas['RMSE']:.4f}"
        )

        print(
            f"R²:          {metricas['R2']:.4f}"
        )

        print(
            f"Correlación: {metricas['Correlacion']:.4f}"
        )

        resultados.append({
            "prueba": nombre_prueba,
            "fin_entrenamiento":
                fin_entrenamiento.date(),
            "inicio_test":
                inicio_test.date(),
            "fin_test":
                fin_test.date(),
            "filas_train":
                len(train),
            "filas_test":
                len(test),
            "modelo":
                nombre_modelo,
            "variables":
                len(variables_validas),
            "MAE":
                metricas["MAE"],
            "RMSE":
                metricas["RMSE"],
            "R2":
                metricas["R2"],
            "Correlacion":
                metricas["Correlacion"],
        })


# ============================================================
# RESULTADOS FINALES
# ============================================================

resultados_df = pd.DataFrame(
    resultados
)

print("\n")
print("=" * 70)
print("RESUMEN FINAL")
print("=" * 70)

if not resultados_df.empty:

    columnas_mostrar = [
        "prueba",
        "modelo",
        "filas_train",
        "filas_test",
        "variables",
        "MAE",
        "RMSE",
        "R2",
        "Correlacion",
    ]

    print(
        resultados_df[
            columnas_mostrar
        ].to_string(index=False)
    )


# ============================================================
# COMPARACIÓN CONTRA BASE
# ============================================================

print("\n")
print("=" * 70)
print("MEJORAS VS A - BASE")
print("=" * 70)

for prueba in resultados_df["prueba"].unique():

    datos_prueba = resultados_df[
        resultados_df["prueba"] == prueba
    ]

    base = datos_prueba[
        datos_prueba["modelo"] == "A - BASE"
    ]

    if base.empty:
        continue

    mae_base = base.iloc[0]["MAE"]

    print(f"\n{prueba}")

    for modelo in [
        "B - BASE + CONTEXTO",
        "C - BASE + CONTEXTO + MATCHUP",
    ]:

        fila = datos_prueba[
            datos_prueba["modelo"] == modelo
        ]

        if fila.empty:
            continue

        mae = fila.iloc[0]["MAE"]

        mejora = (
            (mae_base - mae)
            / mae_base
            * 100
        )

        print(
            f"{modelo}: "
            f"{mejora:+.2f}% MAE"
        )


# ============================================================
# GUARDAR
# ============================================================

SALIDA = "datos/backtest_historico_resultados.csv"

resultados_df.to_csv(
    SALIDA,
    index=False
)

print("\n")
print("=" * 70)
print("BACKTEST TERMINADO")
print("=" * 70)

print(
    f"\nResultados guardados en:\n{SALIDA}"
)