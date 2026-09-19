import json


ARCHIVO = "datos/partidos/16131124.json"


def reconstruir_goles_mientras_jugaba(archivo):
    with open(archivo, "r", encoding="utf-8") as f:
        datos = json.load(f)

    incidentes = datos["incidents"]["incidents"]
    lineups = datos["lineups"]

    # Buscar la duración real del partido.
    max_minuto = 90

    for incidente in incidentes:
        minuto = incidente.get("time")

        if minuto is not None and minuto > max_minuto:
            max_minuto = minuto

    # ---------------------------------------------------------
    # 1. CARGAMOS TODOS LOS TITULARES
    # ---------------------------------------------------------

    participacion = {}

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

        # El jugador que sale deja de estar en cancha.
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

        # El jugador que entra empieza a jugar.
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
    # 3. BUSCAMOS LOS GOLES RECIBIDOS MIENTRAS JUGABA CADA UNO
    # ---------------------------------------------------------

    resultados = []

    for indice, incidente in enumerate(incidentes):

        if incidente.get("incidentType") != "goal":
            continue

        es_local = incidente.get("isHome")
        minuto = incidente.get("time")

        # El gol afecta al equipo contrario.
        equipo_que_recibe = not es_local

        for player_id, jugador in participacion.items():

            if jugador["es_local"] != equipo_que_recibe:
                continue

            entrada = jugador["entrada"]
            salida = jugador["salida"]

            estaba_jugando = True

            # Todavía no había entrado.
            if minuto < entrada:
                estaba_jugando = False

            # Ya había salido.
            if salida is not None:

                if minuto > salida:
                    estaba_jugando = False

                elif minuto == salida:

                    # Si la sustitución aparece antes que el gol,
                    # el jugador ya había salido.
                    if indice > jugador["salida_indice"]:
                        estaba_jugando = False

            if estaba_jugando:
                resultados.append(
                    {
                        "player_id": player_id,
                        "player_name": jugador["nombre"],
                        "gol_minuto": minuto,
                        "gol_indice": indice,
                    }
                )

    return resultados


resultados = reconstruir_goles_mientras_jugaba(ARCHIVO)

print("GOLES RECIBIDOS MIENTRAS EL JUGADOR ESTABA EN CANCHA")
print()

for resultado in resultados:
    print(
        resultado["player_name"],
        "| gol recibido:",
        resultado["gol_minuto"],
        "| indice:",
        resultado["gol_indice"],
    )

print()
print("Total de registros:", len(resultados))