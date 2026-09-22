from pathlib import Path
import math
import numpy as np
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATASET = BASE_DIR / "datos" / "dataset_winning_pitchapi.csv"
SALIDA_DIR = BASE_DIR / "datos"

FECHA_OBJETIVO = 10
FECHA_INICIO_FECHA10 = pd.Timestamp("2026-03-10")

MIN_PARTIDOS_PRINCIPALES = 8
MIN_TITULARIDADES_ULTIMOS_3 = 2

ULTIMOS_PARTIDOS = 3
PARTIDOS_FORMA = 5

SIMULACIONES = 10000

np.random.seed(42)


# ============================================================
# FUNCIONES
# ============================================================

def normalizar_texto(valor):
    if pd.isna(valor):
        return ""

    return (
        str(valor)
        .strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ü", "u")
    )


def safe_mean(values):
    valores = pd.to_numeric(
        values,
        errors="coerce"
    ).dropna()

    if len(valores) == 0:
        return 0.0

    return float(valores.mean())


def safe_std(values):
    valores = pd.to_numeric(
        values,
        errors="coerce"
    ).dropna()

    if len(valores) <= 1:
        return 0.0

    return float(
        valores.std(ddof=1)
    )


def calcular_promedio_ponderado(valores):
    valores = list(
        pd.to_numeric(
            valores,
            errors="coerce"
        ).dropna()
    )

    if not valores:
        return 0.0

    pesos = np.arange(
        1,
        len(valores) + 1
    )

    return float(
        np.average(
            valores,
            weights=pesos
        )
    )


def obtener_columna_titularidad(df):
    candidatos = [
        "titular",
        "starter",
        "starting",
        "es_titular",
        "titularidad",
        "fue_titular",
        "is_starter",
        "is_starting",
        "started",
    ]

    columnas_normalizadas = {
        normalizar_texto(col): col
        for col in df.columns
    }

    for candidato in candidatos:

        clave = normalizar_texto(
            candidato
        )

        if clave in columnas_normalizadas:
            return columnas_normalizadas[clave]

    return None


def interpretar_titular(valor):
    if pd.isna(valor):
        return False

    if isinstance(valor, bool):
        return valor

    texto = normalizar_texto(valor)

    verdaderos = {
        "1",
        "true",
        "si",
        "sí",
        "yes",
        "y",
        "titular",
        "starter",
        "starting",
        "started",
    }

    falsos = {
        "0",
        "false",
        "no",
        "n",
        "suplente",
        "substitute",
        "bench",
    }

    if texto in verdaderos:
        return True

    if texto in falsos:
        return False

    try:
        return float(texto) == 1
    except Exception:
        return False


def seleccionar_posicion(
    candidatos,
    posicion,
    cantidad,
    score_column,
    clubes_actuales
):
    resultado = []

    candidatos_pos = candidatos[
        candidatos["position"] == posicion
    ].sort_values(
        score_column,
        ascending=False
    )

    for _, jugador in candidatos_pos.iterrows():

        club = jugador["team_name"]

        if clubes_actuales.get(
            club,
            0
        ) >= 3:
            continue

        resultado.append(
            jugador.to_dict()
        )

        clubes_actuales[club] = (
            clubes_actuales.get(
                club,
                0
            ) + 1
        )

        if len(resultado) >= cantidad:
            break

    return resultado


def construir_equipo(
    candidatos,
    score_column
):
    clubes = {}

    equipo = []

    equipo.extend(
        seleccionar_posicion(
            candidatos,
            "ARQ",
            1,
            score_column,
            clubes
        )
    )

    equipo.extend(
        seleccionar_posicion(
            candidatos,
            "DEF",
            3,
            score_column,
            clubes
        )
    )

    equipo.extend(
        seleccionar_posicion(
            candidatos,
            "VOL",
            3,
            score_column,
            clubes
        )
    )

    equipo.extend(
        seleccionar_posicion(
            candidatos,
            "DEL",
            3,
            score_column,
            clubes
        )
    )

    return equipo, clubes


def construir_flex(
    candidatos,
    score_column,
    clubes_equipo
):
    flex = []

    for posicion in [
        "DEF",
        "VOL",
        "DEL"
    ]:

        candidatos_pos = candidatos[
            candidatos["position"] == posicion
        ].sort_values(
            score_column,
            ascending=False
        )

        for _, jugador in candidatos_pos.iterrows():

            club = jugador["team_name"]

            if clubes_equipo.get(
                club,
                0
            ) >= 3:
                continue

            flex.append(
                jugador.to_dict()
            )

            break

    return flex


def simular_equipo(equipo):

    resultados = []

    for _ in range(
        SIMULACIONES
    ):

        total = 0.0

        for jugador in equipo:

            media = float(
                jugador["promedio"]
            )

            desviacion = float(
                jugador["desviacion"]
            )

            if not np.isfinite(media):
                media = 0.0

            if (
                not np.isfinite(desviacion)
                or desviacion <= 0
            ):
                desviacion = 1.0

            desviacion = min(
                desviacion,
                max(
                    4.0,
                    abs(media) * 0.75
                )
            )

            valor = np.random.normal(
                media,
                desviacion
            )

            total += valor

        resultados.append(total)

    resultados = np.array(
        resultados
    )

    return {
        "promedio_simulado": float(
            np.mean(resultados)
        ),
        "mediana": float(
            np.median(resultados)
        ),
        "p10": float(
            np.percentile(
                resultados,
                10
            )
        ),
        "p25": float(
            np.percentile(
                resultados,
                25
            )
        ),
        "p75": float(
            np.percentile(
                resultados,
                75
            )
        ),
        "p90": float(
            np.percentile(
                resultados,
                90
            )
        ),
        "min": float(
            np.min(resultados)
        ),
        "max": float(
            np.max(resultados)
        ),
        "prob_mas_100": float(
            np.mean(
                resultados >= 100
            ) * 100
        ),
        "prob_mas_140": float(
            np.mean(
                resultados >= 140
            ) * 100
        ),
    }


# ============================================================
# CARGAR DATASET
# ============================================================

print("=" * 80)
print("BACKTEST WINNING AI - FECHA 10")
print("=" * 80)

print()
print("Cargando dataset...")

df = pd.read_csv(
    DATASET
)

print(
    f"Registros totales dataset: {len(df)}"
)


# ============================================================
# NORMALIZAR
# ============================================================

df["date"] = pd.to_datetime(
    df["date"],
    errors="coerce"
)

df["round_num"] = pd.to_numeric(
    df["round_name"],
    errors="coerce"
)

df["winning_total"] = pd.to_numeric(
    df["winning_total"],
    errors="coerce"
).fillna(0)

df["minutes_played"] = pd.to_numeric(
    df["minutes_played"],
    errors="coerce"
).fillna(0)

df["player_name"] = df[
    "player_name"
].fillna(
    "Jugador desconocido"
)

df["team_name"] = df[
    "team_name"
].fillna(
    "Equipo desconocido"
)

df["position"] = (
    df["position"]
    .fillna("")
    .astype(str)
    .str.upper()
    .str.strip()
)


# ============================================================
# FECHA 10
# ============================================================

fecha10 = df[
    df["round_num"] == FECHA_OBJETIVO
].copy()

if fecha10.empty:
    raise RuntimeError(
        "No se encontraron partidos de Fecha 10."
    )

fecha10 = fecha10.sort_values(
    [
        "date",
        "match_id"
    ]
)

print()
print("=" * 80)
print("FECHA 10")
print("=" * 80)

print(
    f"Primer partido: "
    f"{fecha10['date'].min().strftime('%Y-%m-%d')}"
)

print(
    f"Último partido: "
    f"{fecha10['date'].max().strftime('%Y-%m-%d')}"
)

print(
    f"Partidos encontrados: "
    f"{fecha10['match_id'].nunique()}"
)

print(
    f"Equipos involucrados: "
    f"{fecha10['team_name'].nunique()}"
)

print()
print("Partidos Fecha 10:")
print("-" * 80)

for match_id, grupo in fecha10.groupby(
    "match_id",
    sort=False
):

    fecha = grupo["date"].min()

    equipos = list(
        grupo["team_name"]
        .dropna()
        .unique()
    )

    print(
        f"{fecha.strftime('%d/%m')} | "
        f"{' vs '.join(equipos)} | "
        f"{match_id}"
    )


# ============================================================
# HISTORIAL ANTERIOR A FECHA 10
# ============================================================

historico = df[
    df["date"] < FECHA_INICIO_FECHA10
].copy()

print()
print("=" * 80)
print("HISTORIAL DISPONIBLE PARA EL MODELO")
print("=" * 80)

print(
    f"Registros: {len(historico)}"
)

print(
    f"Partidos: {historico['match_id'].nunique()}"
)

print(
    f"Jugadores: {historico['player_id'].nunique()}"
)

print(
    f"Última fecha permitida: "
    f"{historico['date'].max().strftime('%Y-%m-%d')}"
)


# ============================================================
# TITULARIDAD
# ============================================================

columna_titular = (
    obtener_columna_titularidad(
        historico
    )
)

if columna_titular:

    print()
    print(
        f"Columna de titularidad encontrada: "
        f"{columna_titular}"
    )

    historico["es_titular"] = (
        historico[
            columna_titular
        ].apply(
            interpretar_titular
        )
    )

else:

    print()
    print(
        "AVISO: no se encontró una columna "
        "explícita de titularidad."
    )

    print(
        "Se intentará reconstruir usando "
        "participación/minutos."
    )

    if "participacion" in historico.columns:

        participacion = pd.to_numeric(
            historico["participacion"],
            errors="coerce"
        ).fillna(0)

        historico["es_titular"] = (
            participacion >= 1
        )

    else:

        historico["es_titular"] = False


# ============================================================
# SOLO JUGADORES QUE APARECEN EN FECHA 10
# ============================================================

jugadores_fecha10 = set(
    fecha10["player_id"]
    .dropna()
    .unique()
)

historico = historico[
    historico["player_id"].isin(
        jugadores_fecha10
    )
].copy()


# ============================================================
# CONSTRUIR CANDIDATOS
# ============================================================

registros = []

for player_id, grupo in historico.groupby(
    "player_id"
):

    grupo = grupo.sort_values(
        "date"
    )

    fila_fecha10 = fecha10[
        fecha10["player_id"] == player_id
    ]

    if fila_fecha10.empty:
        continue

    club_fecha10 = (
        fila_fecha10
        .sort_values("date")
        .iloc[-1]["team_name"]
    )

    # --------------------------------------------------------
    # HISTORIAL DEL JUGADOR EN SU CLUB DE FECHA 10
    # --------------------------------------------------------

    grupo_club = grupo[
        grupo["team_name"] == club_fecha10
    ].copy()

    if grupo_club.empty:
        continue

    grupo_club = grupo_club.sort_values(
        "date"
    )

    # --------------------------------------------------------
    # PARTIDOS EN LOS QUE JUGÓ
    # --------------------------------------------------------

    grupo_jugado = grupo_club[
        grupo_club["minutes_played"] > 0
    ].copy()

    if grupo_jugado.empty:
        continue

    partidos = len(
        grupo_jugado
    )

    # --------------------------------------------------------
    # ÚLTIMOS 3
    # --------------------------------------------------------

    ultimos_3 = grupo_jugado.tail(
        ULTIMOS_PARTIDOS
    )

    titularidades_ultimos_3 = int(
        ultimos_3[
            "es_titular"
        ].sum()
    )

    cantidad_ultimos_3 = len(
        ultimos_3
    )

    # --------------------------------------------------------
    # FORMA
    # --------------------------------------------------------

    ultimos_5 = grupo_jugado.tail(
        PARTIDOS_FORMA
    )

    forma_reciente = safe_mean(
        ultimos_5[
            "winning_total"
        ]
    )

    ponderado_reciente = (
        calcular_promedio_ponderado(
            ultimos_5[
                "winning_total"
            ]
        )
    )

    # --------------------------------------------------------
    # HISTORIAL
    # --------------------------------------------------------

    promedio = safe_mean(
        grupo_jugado[
            "winning_total"
        ]
    )

    desviacion = safe_std(
        grupo_jugado[
            "winning_total"
        ]
    )

    minimo = float(
        grupo_jugado[
            "winning_total"
        ].min()
    )

    maximo = float(
        grupo_jugado[
            "winning_total"
        ].max()
    )

    # --------------------------------------------------------
    # PUNTOS POR 90
    # --------------------------------------------------------

    minutos_totales = float(
        grupo_jugado[
            "minutes_played"
        ].sum()
    )

    puntos_totales = float(
        grupo_jugado[
            "winning_total"
        ].sum()
    )

    if minutos_totales > 0:

        promedio_por90 = (
            puntos_totales
            / minutos_totales
            * 90
        )

    else:

        promedio_por90 = 0.0

    # --------------------------------------------------------
    # CONFIANZA POR CANTIDAD DE PARTIDOS
    # --------------------------------------------------------

    if partidos < 4:
        confianza = 0.0

    elif partidos < 6:
        confianza = 0.20

    elif partidos < 8:
        confianza = 0.45

    elif partidos < 12:
        confianza = 0.70

    elif partidos < 16:
        confianza = 0.85

    else:
        confianza = 1.00

    # --------------------------------------------------------
    # ESTABILIDAD
    # --------------------------------------------------------

    if promedio != 0:

        estabilidad = max(
            0.0,
            1.0 - (
                abs(desviacion)
                / max(
                    abs(promedio),
                    1.0
                )
            )
        )

    else:

        estabilidad = 0.0

    estabilidad = min(
        estabilidad,
        1.0
    )

    # --------------------------------------------------------
    # SCORES
    # --------------------------------------------------------

    score_seguro = (
        ponderado_reciente * 0.35
        + promedio * 0.25
        + forma_reciente * 0.15
        + minimo * 0.10
        + promedio_por90 * 0.05
        + estabilidad * 0.05
        + confianza * 0.05
    )

    score_intermedio = (
        ponderado_reciente * 0.35
        + promedio * 0.25
        + forma_reciente * 0.15
        + maximo * 0.10
        + minimo * 0.05
        + promedio_por90 * 0.05
        + confianza * 0.05
    )

    score_arriesgado = (
        maximo * 0.35
        + ponderado_reciente * 0.25
        + promedio_por90 * 0.15
        + promedio * 0.10
        + forma_reciente * 0.10
        + confianza * 0.05
    )

    # --------------------------------------------------------
    # POSICIÓN
    # --------------------------------------------------------

    posiciones = (
        grupo_club[
            "position"
        ]
        .dropna()
        .mode()
    )

    if len(posiciones):

        posicion = posiciones.iloc[0]

    else:

        posicion = ""

    registros.append({
        "player_id": player_id,
        "player_name": fila_fecha10.iloc[0]["player_name"],
        "team_name": club_fecha10,
        "position": posicion,
        "partidos_previos": partidos,
        "titularidades_ultimos_3": titularidades_ultimos_3,
        "partidos_ultimos_3": cantidad_ultimos_3,
        "forma_reciente": forma_reciente,
        "ponderado_reciente": ponderado_reciente,
        "promedio": promedio,
        "promedio_por90": promedio_por90,
        "desviacion": desviacion,
        "minimo": minimo,
        "maximo": maximo,
        "confianza_muestra": confianza,
        "estabilidad": estabilidad,
        "score_seguro": score_seguro,
        "score_intermedio": score_intermedio,
        "score_arriesgado": score_arriesgado,
    })


candidatos = pd.DataFrame(
    registros
)


# ============================================================
# FILTROS
# ============================================================

candidatos["cumple_titularidad"] = (
    (
        candidatos[
            "partidos_ultimos_3"
        ] >= 3
    )
    &
    (
        candidatos[
            "titularidades_ultimos_3"
        ] >= MIN_TITULARIDADES_ULTIMOS_3
    )
)

candidatos["cumple_muestra"] = (
    candidatos[
        "partidos_previos"
    ] >= MIN_PARTIDOS_PRINCIPALES
)

candidatos_principales = candidatos[
    candidatos["cumple_titularidad"]
    &
    candidatos["cumple_muestra"]
].copy()

candidatos_secundarios = candidatos[
    candidatos["cumple_titularidad"]
    &
    (
        candidatos[
            "partidos_previos"
        ] >= 6
    )
].copy()


print()
print("=" * 80)
print("FILTROS DE ELEGIBILIDAD")
print("=" * 80)

print(
    f"Candidatos totales: "
    f"{len(candidatos)}"
)

print(
    f"Cumplen titularidad reciente: "
    f"{int(candidatos['cumple_titularidad'].sum())}"
)

print(
    f"Cumplen mínimo "
    f"{MIN_PARTIDOS_PRINCIPALES} partidos: "
    f"{int(candidatos['cumple_muestra'].sum())}"
)

print(
    f"Candidatos principales: "
    f"{len(candidatos_principales)}"
)

print(
    f"Candidatos secundarios/FLEX: "
    f"{len(candidatos_secundarios)}"
)

print()
print("POSICIONES CANDIDATOS PRINCIPALES:")
print(
    candidatos_principales[
        "position"
    ].value_counts().to_string()
)


# ============================================================
# GENERAR EQUIPOS
# ============================================================

perfiles = {
    "SEGURO": "score_seguro",
    "INTERMEDIO": "score_intermedio",
    "ARRIESGADO": "score_arriesgado",
}

resultados_equipos = []
resultados_simulaciones = []
resultados_reales = []


for nombre_perfil, score_column in perfiles.items():

    print()
    print("=" * 80)
    print(
        f"PERFIL: {nombre_perfil}"
    )
    print("=" * 80)

    equipo, clubes = construir_equipo(
        candidatos_principales,
        score_column
    )

    print()
    print(
        f"Jugadores fijos: "
        f"{len(equipo)}"
    )

    # --------------------------------------------------------
    # MOSTRAR EQUIPO
    # --------------------------------------------------------

    for jugador in equipo:

        print(
            f"{jugador['position']:3} | "
            f"{jugador['player_name']:<28} | "
            f"{jugador['team_name']:<28} | "
            f"Hist {jugador['partidos_previos']:>2} | "
            f"Tit3 "
            f"{jugador['titularidades_ultimos_3']}/"
            f"{jugador['partidos_ultimos_3']} | "
            f"Prom "
            f"{jugador['promedio']:.2f} | "
            f"90 "
            f"{jugador['promedio_por90']:.2f}"
        )

    # --------------------------------------------------------
    # FLEX
    # --------------------------------------------------------

    flex = construir_flex(
        candidatos_secundarios,
        score_column,
        clubes
    )

    print()
    print("FLEX:")

    for jugador in flex:

        print(
            f"{jugador['position']:3} | "
            f"{jugador['player_name']:<28} | "
            f"{jugador['team_name']:<28} | "
            f"Hist "
            f"{jugador['partidos_previos']:>2} | "
            f"Tit3 "
            f"{jugador['titularidades_ultimos_3']}/"
            f"{jugador['partidos_ultimos_3']} | "
            f"Prom "
            f"{jugador['promedio']:.2f}"
        )

    # --------------------------------------------------------
    # SIMULACIÓN
    # --------------------------------------------------------

    simulacion = simular_equipo(
        equipo
    )

    print()
    print("SIMULACIÓN 10.000 ITERACIONES")
    print("-" * 80)

    print(
        f"Promedio: "
        f"{simulacion['promedio_simulado']:.2f}"
    )

    print(
        f"Mediana: "
        f"{simulacion['mediana']:.2f}"
    )

    print(
        f"P10: "
        f"{simulacion['p10']:.2f}"
    )

    print(
        f"P25: "
        f"{simulacion['p25']:.2f}"
    )

    print(
        f"P75: "
        f"{simulacion['p75']:.2f}"
    )

    print(
        f"P90: "
        f"{simulacion['p90']:.2f}"
    )

    print(
        f"Mínimo: "
        f"{simulacion['min']:.2f}"
    )

    print(
        f"Máximo: "
        f"{simulacion['max']:.2f}"
    )

    print(
        f"Probabilidad simulada >=100: "
        f"{simulacion['prob_mas_100']:.2f}%"
    )

    print(
        f"Probabilidad simulada >=140: "
        f"{simulacion['prob_mas_140']:.2f}%"
    )

    # --------------------------------------------------------
    # RESULTADO REAL
    # --------------------------------------------------------

    ids_equipo = {
        jugador["player_id"]
        for jugador in equipo
    }

    reales = fecha10[
        fecha10["player_id"].isin(
            ids_equipo
        )
    ]

    puntos_reales = float(
        reales[
            "winning_total"
        ].sum()
    )

    print()
    print(
        f"PUNTOS REALES FECHA 10: "
        f"{puntos_reales:.2f}"
    )

    # --------------------------------------------------------
    # GUARDAR
    # --------------------------------------------------------

    for jugador in equipo:

        resultados_equipos.append({
            "perfil": nombre_perfil,
            "tipo": "FIJO",
            **jugador
        })

    for jugador in flex:

        resultados_equipos.append({
            "perfil": nombre_perfil,
            "tipo": "FLEX",
            **jugador
        })

    resultados_simulaciones.append({
        "perfil": nombre_perfil,
        **simulacion
    })

    resultados_reales.append({
        "perfil": nombre_perfil,
        "puntos_reales_fecha10": puntos_reales
    })


# ============================================================
# GUARDAR ARCHIVOS
# ============================================================

SALIDA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

archivo_equipos = (
    SALIDA_DIR
    / "backtest_fecha10_equipos.csv"
)

archivo_simulaciones = (
    SALIDA_DIR
    / "backtest_fecha10_simulaciones.csv"
)

archivo_reales = (
    SALIDA_DIR
    / "backtest_fecha10_resultados_reales.csv"
)


pd.DataFrame(
    resultados_equipos
).to_csv(
    archivo_equipos,
    index=False,
    encoding="utf-8-sig"
)

pd.DataFrame(
    resultados_simulaciones
).to_csv(
    archivo_simulaciones,
    index=False,
    encoding="utf-8-sig"
)

pd.DataFrame(
    resultados_reales
).to_csv(
    archivo_reales,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# RESUMEN
# ============================================================

print()
print("=" * 80)
print("RESUMEN FINAL")
print("=" * 80)

print()

print(
    pd.DataFrame(
        resultados_simulaciones
    ).to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}"
    )
)

print()
print("PUNTOS REALES FECHA 10")
print("-" * 80)

print(
    pd.DataFrame(
        resultados_reales
    ).to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}"
    )
)

print()
print("Archivos generados:")
print(archivo_equipos)
print(archivo_simulaciones)
print(archivo_reales)

print()
print("=" * 80)
print("BACKTEST FINALIZADO")
print("=" * 80)