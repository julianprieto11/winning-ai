import json
import glob
from collections import Counter


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVOS = glob.glob("datos/partidos/*.json")


# ============================================================
# CONTADORES
# ============================================================

tipos = Counter()

ejemplos = {
    "normal": [],
    "penal": [],
    "autogol": [],
    "otro": []
}


# ============================================================
# PROCESAR PARTIDOS
# ============================================================

for archivo in ARCHIVOS:

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except Exception:
        continue

    incidentes_data = datos.get("incidents", {})
    incidentes = incidentes_data.get("incidents", [])

    for incidente in incidentes:

        # Solo nos interesan goles
        if incidente.get("incidentType") != "goal":
            continue

        # ----------------------------------------------------
        # Datos básicos
        # ----------------------------------------------------

        minuto = incidente.get("time")

        is_own_goal = incidente.get("incidentClass") == "ownGoal"

        # ----------------------------------------------------
        # Intentamos detectar penal
        # ----------------------------------------------------

        is_penalty = (
            incidente.get("incidentClass") == "penalty"
            or incidente.get("incidentClass") == "penaltyGoal"
            or incidente.get("isPenalty") is True
        )

        # Algunas respuestas de SofaScore pueden utilizar
        # diferentes campos. Revisamos también el texto.
        texto = str(incidente).lower()

        if "penalty" in texto or "penal" in texto:
            if not is_own_goal:
                is_penalty = True

        # ----------------------------------------------------
        # Clasificar
        # ----------------------------------------------------

        if is_own_goal:

            tipo = "autogol"

        elif is_penalty:

            tipo = "penal"

        else:

            tipo = "normal"

        tipos[tipo] += 1


        # ----------------------------------------------------
        # Guardar algunos ejemplos
        # ----------------------------------------------------

        if len(ejemplos[tipo]) < 10:

            ejemplos[tipo].append({
                "archivo": archivo,
                "minuto": minuto,
                "jugador": incidente.get("player", {}).get("name"),
                "incidente": incidente
            })


# ============================================================
# RESULTADOS
# ============================================================

print()
print("=" * 100)
print("TIPOS DE GOL DETECTADOS EN SOFASCORE")
print("=" * 100)

print()

for tipo in ["normal", "penal", "autogol"]:

    print(
        f"{tipo.upper():10} : {tipos[tipo]}"
    )

print()

print(
    "TOTAL      :",
    sum(tipos.values())
)


import json
import glob


ARCHIVOS = glob.glob("datos/partidos/*.json")

encontrados = 0

for archivo in ARCHIVOS:

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except Exception:
        continue

    incidentes = datos.get("incidents", {}).get("incidents", [])

    for incidente in incidentes:

        if incidente.get("incidentType") != "goal":
            continue

        texto = str(incidente).lower()

        # Buscamos posibles penales
        if (
            "penalty" in texto
            or "penal" in texto
        ):

            print()
            print("=" * 100)
            print("POSIBLE PENAL")
            print("=" * 100)
            print("Archivo:", archivo)
            print("Jugador:", incidente.get("player", {}).get("name"))
            print("Minuto:", incidente.get("time"))
            print("incidentClass:", incidente.get("incidentClass"))
            print("from:", incidente.get("from"))

            # Mostrar únicamente los datos importantes
            acciones = incidente.get(
                "footballPassingNetworkAction",
                []
            )

            for accion in acciones:

                if accion.get("eventType") == "goal":

                    print(
                        "goalType:",
                        accion.get("goalType")
                    )

                    print(
                        "situation:",
                        accion.get("situation")
                    )

                    print(
                        "bodyPart:",
                        accion.get("bodyPart")
                    )

            encontrados += 1

            if encontrados >= 10:
                break

    if encontrados >= 10:
        break


print()
print("=" * 100)
print("PENALES MOSTRADOS:", encontrados)
print("=" * 100)