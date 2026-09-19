import re
import requests
import json
import os

MATCH_ID = "m_0MqdAY"

# Leer API key desde el script existente
lines = open("probar_pitchapi.py", encoding="utf-8").read().splitlines()

key = [
    x.split("=", 1)[1].strip().strip('"')
    for x in lines
    if x.strip().startswith("API_KEY")
][0]

url = f"https://api.pitchapi.dev/v1/matches/{MATCH_ID}/lineups"

response = requests.get(
    url,
    headers={"X-API-KEY": key}
)

print("STATUS:", response.status_code)

if response.status_code != 200:
    print(response.text[:3000])
    raise SystemExit

data = response.json()

os.makedirs("datos/pitchapi/lineups", exist_ok=True)

archivo = f"datos/pitchapi/lineups/{MATCH_ID}_lineups.json"

with open(archivo, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("GUARDADO:", archivo)

lineups = data.get("data", {})

for lado in ("home", "away"):

    equipo = lineups.get(lado, {})

    print()
    print("=" * 50)
    print(lado.upper())
    print("FORMACIÓN:", equipo.get("formation"))
    print("=" * 50)

    print("\nTITULARES:")

    for jugador in equipo.get("starters", []):
        print(
            f"{jugador.get('name')} | "
            f"position_id={jugador.get('position_id')} | "
            f"capitan={jugador.get('is_captain')}"
        )

    print("\nSUPLENTES:")

    for jugador in equipo.get("subs", []):
        print(
            f"{jugador.get('name')} | "
            f"position_id={jugador.get('position_id')}"
        )