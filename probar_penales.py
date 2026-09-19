import json
import glob


ARCHIVOS = glob.glob("datos/partidos/*.json")

por_incident_class = []
por_from = []
por_goal_type = []
por_situation = []

vistos = set()


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

        jugador = incidente.get("player") or {}

        player_id = jugador.get("id")
        player_name = jugador.get("name")
        minuto = incidente.get("time")

        acciones = incidente.get(
            "footballPassingNetworkAction",
            []
        )

        if isinstance(acciones, dict):
            acciones = [acciones]

        goal_type = None
        situation = None

        for accion in acciones:

            if accion.get("eventType") == "goal":

                goal_type = accion.get("goalType")
                situation = accion.get("situation")

                break

        clave = (
            archivo,
            player_id,
            minuto
        )

        # -----------------------------------------------------
        # incidentClass
        # -----------------------------------------------------

        if incidente.get("incidentClass") == "penalty":
            por_incident_class.append(clave)

        # -----------------------------------------------------
        # from
        # -----------------------------------------------------

        if incidente.get("from") == "penalty":
            por_from.append(clave)

        # -----------------------------------------------------
        # goalType
        # -----------------------------------------------------

        if goal_type == "penalty":
            por_goal_type.append(clave)

        # -----------------------------------------------------
        # situation
        # -----------------------------------------------------

        if situation == "penalty":
            por_situation.append(clave)

        # -----------------------------------------------------
        # Mostrar cualquier combinación rara
        # -----------------------------------------------------

        es_penal = (
            incidente.get("incidentClass") == "penalty"
            or incidente.get("from") == "penalty"
            or goal_type == "penalty"
            or situation == "penalty"
        )

        if es_penal:

            if clave in vistos:
                continue

            vistos.add(clave)

            if not (
                incidente.get("incidentClass") == "penalty"
                and incidente.get("from") == "penalty"
                and goal_type == "penalty"
                and situation == "penalty"
            ):
                print()
                print("=" * 100)
                print("PENAL CON ESTRUCTURA DIFERENTE")
                print("=" * 100)
                print("Archivo:", archivo)
                print("Jugador:", player_name)
                print("ID:", player_id)
                print("Minuto:", minuto)
                print(
                    "incidentClass:",
                    incidente.get("incidentClass")
                )
                print(
                    "from:",
                    incidente.get("from")
                )
                print(
                    "goalType:",
                    goal_type
                )
                print(
                    "situation:",
                    situation
                )


print()
print("=" * 100)
print("RESUMEN")
print("=" * 100)

print(
    "incidentClass == penalty:",
    len(por_incident_class)
)

print(
    "from == penalty:",
    len(por_from)
)

print(
    "goalType == penalty:",
    len(por_goal_type)
)

print(
    "situation == penalty:",
    len(por_situation)
)

print(
    "Penales unicos detectados:",
    len(vistos)
)