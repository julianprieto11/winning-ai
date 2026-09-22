import json
import glob
import os
import pandas as pd

LINEUPS_DIR = "datos/pitchapi/lineups"
MATCHES_DIR = "datos/pitchapi/matches"
SALIDA = "datos/historial_posiciones_pitchapi.csv"


# ============================================================
# FUNCION PARA CONVERTIR VALORES COMPLEJOS A TEXTO
# ============================================================

def limpiar_valor(valor):

    if isinstance(valor, dict):
        # Intentamos obtener un nombre si PitchAPI devuelve
        # un objeto en lugar de un texto.
        if "name" in valor:
            return str(valor["name"])

        return json.dumps(
            valor,
            ensure_ascii=False,
            sort_keys=True
        )

    if isinstance(valor, list):
        return json.dumps(
            valor,
            ensure_ascii=False
        )

    if pd.isna(valor):
        return ""

    return str(valor)


# ============================================================
# FECHAS DE LOS PARTIDOS
# ============================================================

fechas_partidos = {}

archivos_matches = glob.glob(
    os.path.join(MATCHES_DIR, "*.json")
)

for archivo in archivos_matches:

    try:

        with open(
            archivo,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        root = data.get("data", data)

        if not isinstance(root, dict):
            continue

        match_id = root.get("match_id")

        if not match_id:
            nombre = os.path.basename(archivo)
            match_id = os.path.splitext(nombre)[0]

        fecha = root.get("date")
        hora = root.get("time_utc")

        if fecha:

            fechas_partidos[str(match_id)] = {
                "date": limpiar_valor(fecha),
                "time_utc": limpiar_valor(hora)
            }

    except Exception:
        continue


# ============================================================
# LEER LINEUPS
# ============================================================

registros = []

archivos_lineups = glob.glob(
    os.path.join(
        LINEUPS_DIR,
        "*_lineups.json"
    )
)

print(f"Lineups encontrados: {len(archivos_lineups)}")


for archivo in archivos_lineups:

    try:

        with open(
            archivo,
            "r",
            encoding="utf-8"
        ) as f:
            raw = json.load(f)

    except Exception:
        continue

    data = raw.get("data", raw)

    if not isinstance(data, dict):
        continue

    match_id = data.get("match_id")

    if not match_id:

        nombre = os.path.basename(archivo)

        match_id = nombre.replace(
            "_lineups.json",
            ""
        )

    match_id = limpiar_valor(match_id)

    fecha_info = fechas_partidos.get(
        match_id,
        {}
    )

    fecha = fecha_info.get(
        "date",
        ""
    )

    time_utc = fecha_info.get(
        "time_utc",
        ""
    )


    # ========================================================
    # HOME / AWAY
    # ========================================================

    for lado in ["home", "away"]:

        equipo_data = data.get(
            lado,
            {}
        )

        if not isinstance(
            equipo_data,
            dict
        ):
            continue


        # ----------------------------------------------------
        # NOMBRE DEL EQUIPO
        # ----------------------------------------------------

        equipo = data.get(
            "home_team"
            if lado == "home"
            else "away_team",
            ""
        )

        equipo = limpiar_valor(
            equipo
        )


        # ====================================================
        # TITULARES
        # ====================================================

        starters = equipo_data.get(
            "starters",
            []
        )

        if isinstance(
            starters,
            list
        ):

            for jugador in starters:

                if not isinstance(
                    jugador,
                    dict
                ):
                    continue

                player_id = jugador.get(
                    "player_id"
                )

                if player_id is None:
                    continue

                registros.append({

                    "match_id": match_id,

                    "date": fecha,

                    "time_utc": time_utc,

                    "player_id": limpiar_valor(
                        player_id
                    ),

                    "player_name": limpiar_valor(
                        jugador.get(
                            "name",
                            ""
                        )
                    ),

                    "team": equipo,

                    "side": lado,

                    "starter": 1,

                    "position_id": limpiar_valor(
                        jugador.get(
                            "position_id"
                        )
                    )
                })


        # ====================================================
        # SUPLENTES
        # ====================================================

        subs = equipo_data.get(
            "subs",
            []
        )

        if isinstance(
            subs,
            list
        ):

            for jugador in subs:

                if not isinstance(
                    jugador,
                    dict
                ):
                    continue

                player_id = jugador.get(
                    "player_id"
                )

                if player_id is None:
                    continue

                registros.append({

                    "match_id": match_id,

                    "date": fecha,

                    "time_utc": time_utc,

                    "player_id": limpiar_valor(
                        player_id
                    ),

                    "player_name": limpiar_valor(
                        jugador.get(
                            "name",
                            ""
                        )
                    ),

                    "team": equipo,

                    "side": lado,

                    "starter": 0,

                    "position_id": limpiar_valor(
                        jugador.get(
                            "position_id"
                        )
                    )
                })


# ============================================================
# CREAR DATAFRAME
# ============================================================

df = pd.DataFrame(
    registros
)

if df.empty:

    print("")
    print("ERROR: No se encontraron registros.")
    raise SystemExit


# ============================================================
# ASEGURAR TIPOS SIMPLES
# ============================================================

columnas_texto = [
    "match_id",
    "date",
    "time_utc",
    "player_id",
    "player_name",
    "team",
    "side",
    "position_id"
]

for columna in columnas_texto:

    if columna in df.columns:

        df[columna] = df[columna].apply(
            limpiar_valor
        )


# ============================================================
# STARTER COMO NUMERO
# ============================================================

df["starter"] = pd.to_numeric(
    df["starter"],
    errors="coerce"
).fillna(0).astype(int)


# ============================================================
# ELIMINAR DUPLICADOS
# ============================================================

df = df.drop_duplicates(
    subset=[
        "match_id",
        "player_id"
    ],
    keep="first"
)


# ============================================================
# ORDENAR
# ============================================================

df = df.sort_values(
    by=[
        "date",
        "match_id",
        "player_name"
    ],
    ascending=[
        True,
        True,
        True
    ],
    kind="stable"
)


# ============================================================
# GUARDAR
# ============================================================

df.to_csv(
    SALIDA,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# RESUMEN
# ============================================================

print("")
print("========================================")
print("HISTORIAL DE POSICIONES GENERADO")
print("========================================")
print(
    f"Registros guardados: {len(df)}"
)
print(
    f"Jugadores únicos: {df['player_id'].nunique()}"
)
print(
    f"Partidos: {df['match_id'].nunique()}"
)
print(
    f"Titulares: {(df['starter'] == 1).sum()}"
)
print(
    f"Suplentes: {(df['starter'] == 0).sum()}"
)
print(
    f"Archivo: {SALIDA}"
)
print("========================================")