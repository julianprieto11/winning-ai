import json
import glob
from collections import defaultdict

ARCHIVOS = glob.glob("datos/partidos/*.json")

tarjetas = defaultdict(lambda: {
    "yellow": 0,
    "red": 0,
    "yellowRed": 0
})

for archivo in ARCHIVOS:
    with open(archivo, encoding="utf-8") as f:
        datos = json.load(f)

    evento = datos["event"]["event"]
    event_id = evento.get("id")

    for incidente in datos["incidents"]["incidents"]:

        if incidente.get("incidentType") != "card":
            continue

        if incidente.get("rescinded") is True:
            continue

        jugador = incidente.get("player")

        if not jugador:
            continue

        clase = incidente.get("incidentClass")

        if clase not in ["yellow", "red", "yellowRed"]:
            continue

        player_id = jugador.get("id")

        clave = (event_id, player_id)

        tarjetas[clave][clase] += 1


# Mostrar casos de segunda amarilla
mostrados = 0

for (event_id, player_id), datos_tarjeta in tarjetas.items():

    if datos_tarjeta["yellowRed"] <= 0:
        continue

    print("-" * 60)
    print("Partido:", event_id)
    print("Player ID:", player_id)
    print("Amarillas registradas:", datos_tarjeta["yellow"])
    print("Rojas directas:", datos_tarjeta["red"])
    print("Segundas amarillas:", datos_tarjeta["yellowRed"])

    # REGLAS WINNING
    #
    # Segunda amarilla = -3 puntos TOTAL
    # No se suma aparte la primera amarilla.
    #
    # Roja directa = -3 puntos.
    #
    # Amarilla normal, sin expulsión = -1 punto.

    if datos_tarjeta["yellowRed"] > 0:
        puntos = datos_tarjeta["yellowRed"] * -3
        puntos += datos_tarjeta["red"] * -3
    else:
        puntos = datos_tarjeta["yellow"] * -1
        puntos += datos_tarjeta["red"] * -3

    print("Puntos Winning:", puntos)

    mostrados += 1

    if mostrados >= 10:
        break


print("-" * 60)
print("Casos mostrados:", mostrados)