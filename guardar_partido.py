from curl_cffi import requests
import json

# ==========================================
# CONFIGURACIÓN
# ==========================================

import sys

event_id = int(sys.argv[1])

base_url = f"https://www.sofascore.com/api/v1/event/{event_id}"

# ==========================================
# DESCARGAR DATOS
# ==========================================

print("================================")
print("DESCARGANDO PARTIDO")
print("================================")

print("Event...")
event_response = requests.get(
    base_url,
    impersonate="chrome"
).json()

print("Lineups + estadísticas de jugadores...")
lineups_response = requests.get(
    f"{base_url}/lineups",
    impersonate="chrome"
).json()

print("Incidentes...")
incidents_response = requests.get(
    f"{base_url}/incidents",
    impersonate="chrome"
).json()

print("Estadísticas generales...")
statistics_response = requests.get(
    f"{base_url}/statistics",
    impersonate="chrome"
).json()

# ==========================================
# UNIFICAR TODO
# ==========================================

partido_completo = {
    "event": event_response,
    "lineups": lineups_response,
    "incidents": incidents_response,
    "statistics": statistics_response
}

# ==========================================
# GUARDAR JSON
# ==========================================

archivo_salida = f"datos/partidos/{event_id}.json"

with open(
    archivo_salida,
    "w",
    encoding="utf-8"
) as archivo:
    json.dump(
        partido_completo,
        archivo,
        ensure_ascii=False,
        indent=2
    )

# ==========================================
# RESUMEN
# ==========================================

home = event_response["event"]["homeTeam"]["name"]
away = event_response["event"]["awayTeam"]["name"]

jugadores_local = len(
    lineups_response["home"]["players"]
)

jugadores_visitante = len(
    lineups_response["away"]["players"]
)

incidentes = len(
    incidents_response.get("incidents", [])
)

periodos = len(
    statistics_response.get("statistics", [])
)

print()
print("================================")
print("PARTIDO GUARDADO CORRECTAMENTE")
print("================================")
print("ARCHIVO:", archivo_salida)
print("EVENT ID:", event_id)
print("LOCAL:", home)
print("VISITANTE:", away)
print("JUGADORES LOCAL:", jugadores_local)
print("JUGADORES VISITANTE:", jugadores_visitante)
print("INCIDENTES:", incidentes)
print("PERIODOS ESTADÍSTICAS:", periodos)
print("================================")