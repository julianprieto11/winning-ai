import json
import os
import time
from pathlib import Path

import requests


# ============================================================
# CONFIGURACIÓN
# ============================================================

CARPETA_BASE = Path("datos/pitchapi")
CARPETA_SALIDA = CARPETA_BASE / "matches"

API_URL = "https://api.pitchapi.dev/v1/matches"

# Pegá acá tu API key local, la misma que usás en tu otro script.
API_KEY = "pk_test_QWMXbKvU6nK1x81cECn-kK4ePC781lEMFjyftvALsdI"


# ============================================================
# PREPARACIÓN
# ============================================================

CARPETA_SALIDA.mkdir(
    parents=True,
    exist_ok=True
)

# IMPORTANTE:
# Solo toma archivos normales *_players.json.
# Excluye *_advanced_players.json.
archivos_players = sorted(
    archivo
    for archivo in CARPETA_BASE.glob("*_players.json")
    if not archivo.name.endswith("_advanced_players.json")
)

match_ids = sorted({
    archivo.stem.replace("_players", "")
    for archivo in archivos_players
})


print()
print("=" * 100)
print("DESCARGA DE DETALLES DE PARTIDOS — PITCHAPI")
print("=" * 100)
print()

print(f"Archivos de jugadores: {len(archivos_players)}")
print(f"Match IDs únicos:      {len(match_ids)}")
print(f"Carpeta de salida:     {CARPETA_SALIDA}")
print()


# ============================================================
# SESIÓN HTTP
# ============================================================

session = requests.Session()

session.headers.update({
    "X-API-KEY": API_KEY,
    "Accept": "application/json"
})


# ============================================================
# DESCARGA
# ============================================================

descargados = 0
existentes = 0
errores = 0

total = len(match_ids)

for indice, match_id in enumerate(match_ids, start=1):

    archivo_salida = CARPETA_SALIDA / f"{match_id}.json"

    print(f"[{indice}/{total}] {match_id}")

    # No repetir descargas
    if archivo_salida.exists():

        print("  Ya existe. Se omite.")
        existentes += 1
        continue

    url = f"{API_URL}/{match_id}"

    try:

        respuesta = session.get(
            url,
            timeout=30
        )

        if respuesta.status_code != 200:

            print(
                f"  ERROR HTTP {respuesta.status_code}"
            )

            errores += 1
            continue

        contenido = respuesta.json()

        archivo_salida.write_text(
            json.dumps(
                contenido,
                indent=2,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        print("  Guardado correctamente.")

        descargados += 1

        # Pausa pequeña entre consultas
        time.sleep(0.15)

    except requests.RequestException as error:

        print(f"  ERROR DE CONEXIÓN: {error}")
        errores += 1

    except ValueError as error:

        print(f"  ERROR JSON: {error}")
        errores += 1


# ============================================================
# RESUMEN
# ============================================================

print()
print("=" * 100)
print("RESUMEN")
print("=" * 100)
print()

print(f"Descargados:       {descargados}")
print(f"Ya existentes:     {existentes}")
print(f"Errores:           {errores}")
print(f"Total de IDs:      {total}")
print()

print("Proceso terminado.")