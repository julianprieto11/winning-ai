import json

match_id = "15269907"

with open(f"datos/partidos/{match_id}.json", "r", encoding="utf-8") as f:
    datos = json.load(f)

incidentes = datos["incidents"]["incidents"]

print()
print("=" * 100)
print(f"PARTICIPACIÓN TEMPORAL - PARTIDO {match_id}")
print("=" * 100)

for incidente in incidentes:

    if incidente.get("incidentType") not in [
        "substitution",
        "goal"
    ]:
        continue

    print()
    print(
        "TIPO:",
        incidente.get("incidentType"),
        "| MINUTO:",
        incidente.get("time"),
        "| ID:",
        incidente.get("id")
    )

    if incidente.get("incidentType") == "substitution":

        jugador_in = incidente.get("playerIn", {})
        jugador_out = incidente.get("playerOut", {})

        print(
            "ENTRA:",
            jugador_in.get("name"),
            "| ID:",
            jugador_in.get("id")
        )

        print(
            "SALE:",
            jugador_out.get("name"),
            "| ID:",
            jugador_out.get("id")
        )

        print(
            "reversedPeriodTime:",
            incidente.get("reversedPeriodTime")
        )

    elif incidente.get("incidentType") == "goal":

        jugador = incidente.get("player", {})

        print(
            "GOLEADOR:",
            jugador.get("name"),
            "| ID:",
            jugador.get("id")
        )

print()
print("=" * 100)