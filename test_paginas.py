from curl_cffi import requests
import json

event_id = 16671607

# Datos generales del partido
event_response = requests.get(
    f"https://www.sofascore.com/api/v1/event/{event_id}",
    impersonate="chrome"
).json()

# Alineaciones + estadísticas individuales
lineups_response = requests.get(
    f"https://www.sofascore.com/api/v1/event/{event_id}/lineups",
    impersonate="chrome"
).json()

# Guardamos TODO sin modificarlo
partido_completo = {
    "event": event_response,
    "lineups": lineups_response
}

with open(
    "partido_16671607.json",
    "w",
    encoding="utf-8"
) as archivo:
    json.dump(
        partido_completo,
        archivo,
        ensure_ascii=False,
        indent=2
    )

print("================================")
print("ARCHIVO GUARDADO")
print("================================")
print("partido_16671607.json")
print("EVENT ID:", event_id)
print("LOCAL:", event_response["event"]["homeTeam"]["name"])
print("VISITANTE:", event_response["event"]["awayTeam"]["name"])
print("JUGADORES:", len(
    lineups_response["home"]["players"]
    + lineups_response["away"]["players"]
))