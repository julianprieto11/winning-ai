import json
import glob


ARCHIVOS = glob.glob("datos/partidos/*.json")


def reconstruir_partido(archivo):

    with open(archivo, "r", encoding="utf-8") as f:
        datos = json.load(f)

    incidentes = datos.get("incidents", {}).get("incidents", [])
    lineups = datos.get("lineups", {})

    participacion = {}

    # ---------------------------------------------------------
    # 1. CARGAMOS TODOS LOS TITULARES
    # ---------------------------------------------------------

    for lado in ["home", "away"]:

        es_local = lado == "home"

        jugadores = lineups.get(lado, {}).get("players", [])

        for registro in jugadores:

            if registro.get("substitute"):
                continue

            jugador = registro.get("player") or {}
            player_id = jugador.get("id")

            if not player_id:
                continue

            participacion[player_id] = {
                "nombre": jugador.get("name"),
                "es_local": es_local,
                "entrada": 0,
                "entrada_indice": -1,
                "salida": None,
                "salida_indice": None,
            }

    # ---------------------------------------------------------
    # 2. APLICAMOS LAS SUSTITUCIONES
    # ---------------------------------------------------------

    for indice, incidente in enumerate(incidentes):

        if incidente.get("incidentType") != "substitution":
            continue

        player_in = incidente.get("playerIn") or {}
        player_out = incidente.get("playerOut") or {}

        id_in = player_in.get("id")
        id_out = player_out.get("id")

        minuto = incidente.get("time")
        es_local = incidente.get("isHome")

        # Jugador que sale
        if id_out:

            if id_out not in participacion:
                participacion[id_out] = {
                    "nombre": player_out.get("name"),
                    "es_local": es_local,
                    "entrada": 0,
                    "entrada_indice": -1,
                    "salida": minuto,
                    "salida_indice": indice,
                }
            else:
                participacion[id_out]["salida"] = minuto
                participacion[id_out]["salida_indice"] = indice

        # Jugador que entra
        if id_in:

            participacion[id_in] = {
                "nombre": player_in.get("name"),
                "es_local": es_local,
                "entrada": minuto,
                "entrada_indice": indice,
                "salida": None,
                "salida_indice": None,
            }

    # ---------------------------------------------------------
    # 3. CONTAMOS GOLES RECIBIDOS MIENTRAS CADA JUGADOR JUGABA
    # ---------------------------------------------------------

    goles_por_jugador = {}

    for player_id in participacion:
        goles_por_jugador[player_id] = 0

    for indice, incidente in enumerate(incidentes):

        if incidente.get("incidentType") != "goal":
            continue

        es_local = incidente.get("isHome")
        minuto = incidente.get("time")

        # El gol lo recibe el equipo contrario
        equipo_que_recibe = not es_local

        for player_id, jugador in participacion.items():

            if jugador["es_local"] != equipo_que_recibe:
                continue

            entrada = jugador["entrada"]
            salida = jugador["salida"]

            estaba_jugando = True

            # Todavía no había entrado
            if minuto < entrada:
                estaba_jugando = False

            # Ya había salido
            if salida is not None:

                if minuto > salida:
                    estaba_jugando = False

                elif minuto == salida:

                    # Si la sustitución aparece antes que el gol,
                    # el jugador ya estaba fuera.
                    if indice > jugador["salida_indice"]:
                        estaba_jugando = False

            if estaba_jugando:
                goles_por_jugador[player_id] += 1

    return participacion, goles_por_jugador


# =============================================================
# PROCESAMOS TODOS LOS PARTIDOS
# =============================================================

total_partidos = 0
total_jugadores = 0
total_goles_recibidos = 0

casos_sospechosos = []

for archivo in ARCHIVOS:

    try:

        participacion, goles = reconstruir_partido(archivo)

        total_partidos += 1

        for player_id, cantidad in goles.items():

            total_jugadores += 1
            total_goles_recibidos += cantidad

            # Guardamos algunos casos para revisar después
            if cantidad > 5:
                casos_sospechosos.append(
                    (
                        archivo,
                        participacion[player_id]["nombre"],
                        cantidad
                    )
                )

    except Exception as e:

        print()
        print("ERROR EN:", archivo)
        print(e)


# =============================================================
# RESULTADO
# =============================================================

print()
print("==========================================")
print("PRUEBA DE GOLES RECIBIDOS")
print("==========================================")
print()

print("Archivos encontrados:", len(ARCHIVOS))
print("Partidos procesados:", total_partidos)
print("Registros de jugadores:", total_jugadores)
print("Goles recibidos contabilizados:", total_goles_recibidos)

print()

print("Casos con más de 5 goles recibidos por jugador:")

if casos_sospechosos:

    for caso in casos_sospechosos[:30]:
        print(caso)

else:

    print("Ninguno")

print()
print("==========================================")