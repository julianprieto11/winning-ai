import requests
import json
import os
import time

BASE = "datos/pitchapi"

# Leer API key desde el script existente
lines = open("probar_pitchapi.py", encoding="utf-8").read().splitlines()

key = [
    x.split("=", 1)[1].strip().strip('"')
    for x in lines
    if x.strip().startswith("API_KEY")
][0]

headers = {
    "X-API-KEY": key
}

# Buscar todos los JSON de PitchAPI y obtener match_id
match_ids = set()

for root, dirs, files in os.walk(BASE):

    for filename in files:

        if not filename.endswith(".json"):
            continue

        path = os.path.join(root, filename)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        root_data = data.get("data", {})

        if not isinstance(root_data, dict):
            continue

        match_id = root_data.get("match_id")

        if match_id:
            match_ids.add(match_id)


print("=" * 70)
print("DESCARGA MASIVA DE LINEUPS - PITCHAPI")
print("=" * 70)

print("Partidos encontrados:", len(match_ids))

os.makedirs(f"{BASE}/lineups", exist_ok=True)

descargados = 0
existentes = 0
errores = 0

for i, match_id in enumerate(sorted(match_ids), 1):

    archivo = f"{BASE}/lineups/{match_id}_lineups.json"

    if os.path.exists(archivo):
        existentes += 1
        continue

    url = f"https://api.pitchapi.dev/v1/matches/{match_id}/lineups"

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:

            data = response.json()

            with open(archivo, "w", encoding="utf-8") as f:
                json.dump(
                    data,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            descargados += 1

        else:

            errores += 1

            print(
                f"[ERROR] {match_id} -> "
                f"HTTP {response.status_code}"
            )

    except Exception as e:

        errores += 1

        print(
            f"[ERROR] {match_id} -> {e}"
        )

    if i % 25 == 0:

        print(
            f"Progreso: {i}/{len(match_ids)} | "
            f"descargados={descargados} | "
            f"existentes={existentes} | "
            f"errores={errores}"
        )

    time.sleep(0.15)


print()
print("=" * 70)
print("RESUMEN")
print("=" * 70)

print("Partidos encontrados :", len(match_ids))
print("Ya existentes        :", existentes)
print("Descargados          :", descargados)
print("Errores              :", errores)

print()
print("Carpeta:", f"{BASE}/lineups")