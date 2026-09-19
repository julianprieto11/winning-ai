import pandas as pd


# ============================================================
# ARCHIVOS
# ============================================================

CANDIDATOS = "datos/auditoria_historial_fecha10.csv"
HISTORIAL = "datos/dataset_winning_v2.csv"

SALIDA = "datos/prediccion_fecha10_v2.csv"


# ============================================================
# CARGAR DATOS
# ============================================================

cand = pd.read_csv(CANDIDATOS)
hist = pd.read_csv(HISTORIAL)


# ============================================================
# NORMALIZAR IDs
# ============================================================

cand["player_id"] = cand["player_id"].astype(str)
hist["player_id"] = hist["player_id"].astype(str)


# ============================================================
# HISTORIAL
# ============================================================

hist = hist[
    hist["minutesPlayed"].notna()
    & (hist["minutesPlayed"] > 0)
].copy()


historico = (
    hist
    .groupby("player_id")
    .agg(
        partidos=("match_id", "count"),
        minutos=("minutesPlayed", "sum"),
        winning_promedio=("winning_v2", "mean"),
        winning_por90=("winning_por90_v2", "mean"),
    )
    .reset_index()
)


# ============================================================
# UNIR CANDIDATOS CON HISTORIAL
# ============================================================

df = cand.merge(
    historico,
    on="player_id",
    how="left"
)


# ============================================================
# PROYECCIÓN
# ============================================================

df["proyeccion"] = df["winning_por90"]


# ============================================================
# TODOS LOS JUGADORES DE FECHA 10 SON CANDIDATOS
# ============================================================

df = df.copy()


# ============================================================
# NORMALIZAR POSICIONES
# ============================================================

df["position"] = (
    df["position"]
    .fillna("")
    .astype(str)
    .str.upper()
)


# ============================================================
# AUDITORÍA RÁPIDA
# ============================================================

print()
print("=" * 90)
print("DATOS DE CANDIDATOS")
print("=" * 90)
print()

print(f"Candidatos: {len(df)}")
print(
    f"Con proyección histórica: "
    f"{df['proyeccion'].notna().sum()}"
)
print(
    f"Sin proyección histórica: "
    f"{df['proyeccion'].isna().sum()}"
)

print()
print("Candidatos por posición:")

print(
    df["position"].value_counts(dropna=False)
)

print()


# ============================================================
# ELIMINAR SOLAMENTE LOS QUE NO TENGAN PROYECCIÓN
# ============================================================

df = df[
    df["proyeccion"].notna()
].copy()


# ============================================================
# ORDENAR
# ============================================================

df = df.sort_values(
    "proyeccion",
    ascending=False
).reset_index(drop=True)


# ============================================================
# FUNCIÓN: COMPROBAR LÍMITE DE CLUB
# ============================================================

def puede_agregar(equipo, seleccionados):

    cantidad = sum(
        1
        for jugador in seleccionados
        if jugador["equipo"] == equipo
    )

    return cantidad < 3


# ============================================================
# FUNCIÓN: SELECCIONAR POR POSICIÓN
# ============================================================

def seleccionar_posicion(
    df_pos,
    cantidad,
    seleccionados
):

    resultado = []

    for _, fila in df_pos.iterrows():

        if len(resultado) >= cantidad:
            break

        equipo = fila["equipo"]

        if not puede_agregar(
            equipo,
            seleccionados
        ):
            continue

        jugador = {
            "player_id": fila["player_id"],
            "jugador": fila["jugador"],
            "equipo": equipo,
            "position": fila["position"],
            "proyeccion": fila["proyeccion"],
            "partidos_hist": fila["partidos"],
            "minutos_hist": fila["minutos"],
        }

        resultado.append(jugador)
        seleccionados.append(jugador)

    return resultado


# ============================================================
# ARMAR 11 TITULAR
# ============================================================

seleccionados = []


# ------------------------------------------------------------
# ARQUERO
# ------------------------------------------------------------

arquero = seleccionar_posicion(
    df[df["position"] == "G"],
    1,
    seleccionados
)


# ------------------------------------------------------------
# DEFENSORES
# ------------------------------------------------------------

defensores = seleccionar_posicion(
    df[df["position"] == "D"],
    3,
    seleccionados
)


# ------------------------------------------------------------
# VOLANTES
# ------------------------------------------------------------

volantes = seleccionar_posicion(
    df[df["position"] == "M"],
    3,
    seleccionados
)


# ------------------------------------------------------------
# DELANTEROS
# ------------------------------------------------------------

delanteros = seleccionar_posicion(
    df[df["position"] == "F"],
    3,
    seleccionados
)


# ============================================================
# FLEX
#
# IMPORTANTE:
# Los FLEX NO forman parte de los 11 titulares.
#
# Se buscan después de armar el equipo y se mantienen
# como alternativas independientes.
# ============================================================

ids_titulares = {
    jugador["player_id"]
    for jugador in seleccionados
}


def mejor_flex(posicion):

    disponibles = df[
        (df["position"] == posicion)
        & (
            ~df["player_id"].isin(
                ids_titulares
            )
        )
    ].copy()

    return disponibles.head(1)


flex_def = mejor_flex("D")
flex_vol = mejor_flex("M")
flex_del = mejor_flex("F")


# ============================================================
# MOSTRAR RESULTADO
# ============================================================

print()
print("=" * 90)
print("PREDICCIÓN FECHA 10 - WINNING AI V2")
print("=" * 90)


def mostrar_titulo(titulo):

    print()
    print(titulo)
    print("-" * 90)


def mostrar_jugadores(lista):

    for i, jugador in enumerate(
        lista,
        1
    ):

        print(
            f"{i}. "
            f"{jugador['jugador']:<30} "
            f"{jugador['equipo']:<30} "
            f"Proyección: "
            f"{jugador['proyeccion']:.2f} "
            f"| Hist: "
            f"{jugador['partidos_hist']} partidos"
        )


# ============================================================
# ARQUERO
# ============================================================

mostrar_titulo("🧤 ARQUERO")

mostrar_jugadores(
    arquero
)


# ============================================================
# DEFENSORES
# ============================================================

mostrar_titulo("🛡️ DEFENSORES")

mostrar_jugadores(
    defensores
)


# ============================================================
# VOLANTES
# ============================================================

mostrar_titulo("⚙️ VOLANTES")

mostrar_jugadores(
    volantes
)


# ============================================================
# DELANTEROS
# ============================================================

mostrar_titulo("⚡ DELANTEROS")

mostrar_jugadores(
    delanteros
)


# ============================================================
# FLEX
# ============================================================

print()
print("=" * 90)
print("🔄 FLEX")
print("=" * 90)


if len(flex_def) > 0:

    f = flex_def.iloc[0]

    print(
        f"DEF | "
        f"{f['jugador']:<30} "
        f"{f['equipo']:<30} "
        f"Proyección: {f['proyeccion']:.2f}"
    )

else:

    print("DEF | No disponible")


if len(flex_vol) > 0:

    f = flex_vol.iloc[0]

    print(
        f"VOL | "
        f"{f['jugador']:<30} "
        f"{f['equipo']:<30} "
        f"Proyección: {f['proyeccion']:.2f}"
    )

else:

    print("VOL | No disponible")


if len(flex_del) > 0:

    f = flex_del.iloc[0]

    print(
        f"DEL | "
        f"{f['jugador']:<30} "
        f"{f['equipo']:<30} "
        f"Proyección: {f['proyeccion']:.2f}"
    )

else:

    print("DEL | No disponible")


# ============================================================
# VALIDACIÓN
# ============================================================

print()
print("=" * 90)
print("VALIDACIÓN")
print("=" * 90)

print()

print(
    f"Titulares: {len(seleccionados)}"
)

print(
    f"ARQ: {len(arquero)}"
)

print(
    f"DEF: {len(defensores)}"
)

print(
    f"VOL: {len(volantes)}"
)

print(
    f"DEL: {len(delanteros)}"
)


# ============================================================
# CLUBES
# ============================================================

print()
print("Jugadores por club:")
print("-" * 90)


conteo_clubes = {}


for jugador in seleccionados:

    equipo = jugador["equipo"]

    conteo_clubes[equipo] = (
        conteo_clubes.get(
            equipo,
            0
        ) + 1
    )


for equipo, cantidad in sorted(
    conteo_clubes.items(),
    key=lambda x: (-x[1], x[0])
):

    estado = (
        "OK"
        if cantidad <= 3
        else "ERROR"
    )

    print(
        f"{equipo:<40} "
        f"{cantidad} "
        f"{estado}"
    )


# ============================================================
# VALIDACIÓN FINAL DEL 11
# ============================================================

print()

if (
    len(arquero) == 1
    and len(defensores) == 3
    and len(volantes) == 3
    and len(delanteros) == 3
    and len(seleccionados) == 10
):

    print(
        "ATENCIÓN: el esquema actual tiene "
        "10 jugadores. Para Winning necesitamos "
        "verificar la estructura del puesto FLEX."
    )

else:

    print(
        "La estructura todavía necesita revisión."
    )


# ============================================================
# GUARDAR RESULTADO
# ============================================================

filas = []


# ------------------------------------------------------------
# TITULARES
# ------------------------------------------------------------

for jugador in seleccionados:

    filas.append({
        "tipo": "TITULAR",
        "posicion": jugador["position"],
        "jugador": jugador["jugador"],
        "player_id": jugador["player_id"],
        "equipo": jugador["equipo"],
        "proyeccion": jugador["proyeccion"],
        "partidos_hist": jugador["partidos_hist"],
        "minutos_hist": jugador["minutos_hist"],
    })


# ------------------------------------------------------------
# FLEX
# ------------------------------------------------------------

for posicion_flex, flex in [
    ("D", flex_def),
    ("M", flex_vol),
    ("F", flex_del),
]:

    if len(flex) == 0:
        continue

    f = flex.iloc[0]

    filas.append({
        "tipo": "FLEX",
        "posicion": posicion_flex,
        "jugador": f["jugador"],
        "player_id": f["player_id"],
        "equipo": f["equipo"],
        "proyeccion": f["proyeccion"],
        "partidos_hist": f["partidos"],
        "minutos_hist": f["minutos"],
    })


resultado = pd.DataFrame(
    filas
)


resultado.to_csv(
    SALIDA,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# FIN
# ============================================================

print()
print(
    f"Archivo generado: {SALIDA}"
)
print()