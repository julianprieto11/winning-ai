import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO = "datos/backtest_dataset.csv"

TARGET = "winning_total"

# Todo lo anterior se usa para entrenar.
# Todo lo posterior se usa para evaluar.
FECHA_CORTE = "2026-08-01"


# ============================================================
# CARGAR DATASET
# ============================================================

print("=" * 70)
print("WINNING AI - COMPARACIÓN BACKTEST TEMPORAL")
print("=" * 70)

print("\n[1/8] Cargando dataset...")

df = pd.read_csv(
    ARCHIVO,
    low_memory=False
)

df["date"] = pd.to_datetime(df["date"])

print(f"Filas: {len(df):,}")
print(f"Fecha inicial: {df['date'].min().date()}")
print(f"Fecha final:   {df['date'].max().date()}")


# ============================================================
# IDENTIFICAR VARIABLES
# ============================================================

print("\n[2/8] Identificando variables...")


# ------------------------------------------------------------
# COLUMNAS QUE NUNCA PUEDEN SER PREDICTORAS
# ------------------------------------------------------------

columnas_prohibidas = {
    TARGET,
    "date",
    "match_id",
    "player_id",
    "player_name",
    "team_id",
    "team_name",
    "round_name",

    # Datos del partido que se está prediciendo
    "minutes_played",
    "winning_total",
    "match_finished",
}


# ------------------------------------------------------------
# VARIABLES BASE
# ------------------------------------------------------------

base_columns = [
    c for c in df.columns
    if (
        c.startswith("prom_ultimos_5_")
        or c in {
            "minutos_promedio_historico",
            "partidos_historicos_minutos",
            "minutos_promedio_ultimos_5",
            "position",
        }
    )
]


# ------------------------------------------------------------
# VARIABLES CONTEXTO
# ------------------------------------------------------------

context_columns = [
    c for c in df.columns
    if (
        c.startswith("historico_")
        or c.startswith("rival_historico_")
    )
]


# ------------------------------------------------------------
# VARIABLES MATCHUP
# ------------------------------------------------------------

matchup_columns = [
    c for c in df.columns
    if c.startswith("matchup_")
]


# ------------------------------------------------------------
# LIMPIAR
# ------------------------------------------------------------

def limpiar_columnas(columnas):

    resultado = []

    for c in columnas:

        if c not in df.columns:
            continue

        if c in columnas_prohibidas:
            continue

        # Evitamos cualquier columna que claramente
        # represente información posterior al partido.
        nombre = c.lower()

        palabras_prohibidas = [
            "sofascore_event",
            "sofascore_match",
            "resultado_puntos",
            "bonus_resultado",
            "valla_invicta",
            "goles_asistencias",
            "match_finished",
            "winning_total",
        ]

        if any(
            palabra in nombre
            for palabra in palabras_prohibidas
        ):
            continue

        resultado.append(c)

    return list(dict.fromkeys(resultado))


base_columns = limpiar_columnas(base_columns)

context_columns = limpiar_columnas(context_columns)

matchup_columns = limpiar_columnas(matchup_columns)


print(f"BASE:     {len(base_columns)} variables")
print(f"CONTEXTO: {len(context_columns)} variables")
print(f"MATCHUP:  {len(matchup_columns)} variables")


# ============================================================
# CONSTRUIR LOS TRES MODELOS
# ============================================================

modelo_A = list(
    dict.fromkeys(
        base_columns
    )
)

modelo_B = list(
    dict.fromkeys(
        base_columns
        + context_columns
    )
)

modelo_C = list(
    dict.fromkeys(
        base_columns
        + context_columns
        + matchup_columns
    )
)


print("\nVariables utilizadas:")

print(
    f"A - BASE: "
    f"{len(modelo_A)}"
)

print(
    f"B - BASE + CONTEXTO: "
    f"{len(modelo_B)}"
)

print(
    f"C - BASE + CONTEXTO + MATCHUP: "
    f"{len(modelo_C)}"
)


# ============================================================
# SEPARACIÓN TEMPORAL
# ============================================================

print("\n[3/8] Separando TRAIN / TEST...")


fecha_corte = pd.Timestamp(
    FECHA_CORTE
)

train = df[
    df["date"] < fecha_corte
].copy()

test = df[
    df["date"] >= fecha_corte
].copy()


print("\nTRAIN")
print(
    f"Desde: {train['date'].min().date()}"
)
print(
    f"Hasta: {train['date'].max().date()}"
)
print(
    f"Filas: {len(train):,}"
)

print("\nTEST")
print(
    f"Desde: {test['date'].min().date()}"
)
print(
    f"Hasta: {test['date'].max().date()}"
)
print(
    f"Filas: {len(test):,}"
)


# ============================================================
# PREPARAR FEATURES
# ============================================================

def preparar_X(data, columnas):

    X = data[columnas].copy()

    if "position" in X.columns:

        X["position"] = (
            X["position"]
            .fillna("DESCONOCIDA")
            .astype(str)
        )

    return X


# ============================================================
# CONSTRUIR MODELO
# ============================================================

def crear_pipeline(X):

    columnas_numericas = (
        X.select_dtypes(
            include=["number", "bool"]
        )
        .columns
        .tolist()
    )

    columnas_categoricas = (
        X.select_dtypes(
            exclude=["number", "bool"]
        )
        .columns
        .tolist()
    )


    transformers = []


    # --------------------------------------------------------
    # NUMÉRICAS
    # --------------------------------------------------------

    if columnas_numericas:

        transformers.append(
            (
                "numericas",

                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(
                                strategy="median"
                            )
                        )
                    ]
                ),

                columnas_numericas,
            )
        )


    # --------------------------------------------------------
    # CATEGÓRICAS
    # --------------------------------------------------------

    if columnas_categoricas:

        transformers.append(
            (
                "categoricas",

                Pipeline(
                    [
                        (
                            "imputer",
                            SimpleImputer(
                                strategy="most_frequent"
                            )
                        ),

                        (
                            "onehot",

                            OneHotEncoder(
                                handle_unknown="ignore",
                                sparse_output=False
                            )
                        ),
                    ]
                ),

                columnas_categoricas,
            )
        )


    preprocesador = ColumnTransformer(
        transformers=transformers,
        remainder="drop"
    )


    # --------------------------------------------------------
    # MODELO
    # --------------------------------------------------------

    modelo = HistGradientBoostingRegressor(
        max_iter=300,
        learning_rate=0.05,
        max_leaf_nodes=31,
        l2_regularization=1.0,
        random_state=42
    )


    pipeline = Pipeline(
        [
            (
                "preprocesador",
                preprocesador
            ),

            (
                "modelo",
                modelo
            ),
        ]
    )


    return pipeline


# ============================================================
# EVALUAR MODELO
# ============================================================

def evaluar(nombre, columnas):

    print("\n" + "=" * 70)
    print(f"MODELO: {nombre}")
    print("=" * 70)

    X_train = preparar_X(
        train,
        columnas
    )

    X_test = preparar_X(
        test,
        columnas
    )

    y_train = train[TARGET]

    y_test = test[TARGET]


    print(
        f"Variables: {len(columnas)}"
    )

    print(
        f"Train: {len(X_train):,}"
    )

    print(
        f"Test:  {len(X_test):,}"
    )


    # --------------------------------------------------------
    # ENTRENAR
    # --------------------------------------------------------

    print("Entrenando...")

    pipeline = crear_pipeline(
        X_train
    )

    pipeline.fit(
        X_train,
        y_train
    )


    # --------------------------------------------------------
    # PREDICCIÓN
    # --------------------------------------------------------

    print("Prediciendo...")

    pred = pipeline.predict(
        X_test
    )


    # --------------------------------------------------------
    # MÉTRICAS
    # --------------------------------------------------------

    mae = mean_absolute_error(
        y_test,
        pred
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            pred
        )
    )

    r2 = r2_score(
        y_test,
        pred
    )

    correlacion = np.corrcoef(
        y_test,
        pred
    )[0, 1]


    print("\nRESULTADO")

    print(
        f"MAE:         {mae:.4f}"
    )

    print(
        f"RMSE:        {rmse:.4f}"
    )

    print(
        f"R²:          {r2:.4f}"
    )

    print(
        f"Correlación: {correlacion:.4f}"
    )


    return {
        "modelo": nombre,
        "variables": len(columnas),
        "train_filas": len(train),
        "test_filas": len(test),
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
        "correlacion": correlacion,
    }


# ============================================================
# EJECUTAR
# ============================================================

print("\n[4/8] Ejecutando MODELO A...")

resultado_A = evaluar(
    "A - BASE",
    modelo_A
)


print("\n[5/8] Ejecutando MODELO B...")

resultado_B = evaluar(
    "B - BASE + CONTEXTO",
    modelo_B
)


print("\n[6/8] Ejecutando MODELO C...")

resultado_C = evaluar(
    "C - BASE + CONTEXTO + MATCHUP",
    modelo_C
)


# ============================================================
# TABLA FINAL
# ============================================================

print("\n[7/8] COMPARACIÓN FINAL")

resultados = pd.DataFrame(
    [
        resultado_A,
        resultado_B,
        resultado_C,
    ]
)


print(
    resultados.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ============================================================
# COMPARACIÓN CONTRA BASE
# ============================================================

print("\n" + "=" * 70)
print("CAMBIOS RESPECTO A BASE")
print("=" * 70)


base = resultado_A


for resultado in [
    resultado_B,
    resultado_C,
]:

    cambio_mae = (
        (
            resultado["MAE"]
            - base["MAE"]
        )
        / base["MAE"]
    ) * 100


    cambio_rmse = (
        (
            resultado["RMSE"]
            - base["RMSE"]
        )
        / base["RMSE"]
    ) * 100


    cambio_r2 = (
        resultado["R2"]
        - base["R2"]
    )


    cambio_corr = (
        resultado["correlacion"]
        - base["correlacion"]
    )


    print(
        f"\n{resultado['modelo']}"
    )

    print(
        f"  MAE:         {cambio_mae:+.2f}%"
    )

    print(
        f"  RMSE:        {cambio_rmse:+.2f}%"
    )

    print(
        f"  R²:          {cambio_r2:+.4f}"
    )

    print(
        f"  Correlación: {cambio_corr:+.4f}"
    )


# ============================================================
# GUARDAR
# ============================================================

print("\n[8/8] Guardando resultados...")

SALIDA = (
    "datos/"
    "backtest_resultados.csv"
)

resultados.to_csv(
    SALIDA,
    index=False
)


print(
    f"\nArchivo generado:"
)

print(
    SALIDA
)


print("\n" + "=" * 70)
print("BACKTEST TERMINADO")
print("=" * 70)