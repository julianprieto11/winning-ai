import json
import time
from pathlib import Path
import requests

# ============================================================
# CONFIGURACIÓN
# ============================================================

CARPETA = Path("datos/pitchapi")
API_KEY = "pk_test_QWMXbKvU6nK1x81cECn-kK4ePC781lEMFjyftvALsdI"

BASE_URL = "https://api.pitchapi.dev/v1"

# ============================================================
# SESIÓN
# ============================================================

session = requests.Session()

session.headers.update({
    "X-API-KEY": API_KEY
})

# ============================================================
# BUSCAR LOS MATCH IDs
# ============================================================

match_ids = set()

for archivo in CARPETA.glob("*_players.json"):

    # No confundir con advanced_players
    if archivo.name.endswith("_advanced_players.json"):
        continue

    match_id = archivo.name.replace("_players.json", "")

    if match_id:
        match_ids.add(match_id)

match_ids = sorted(match_ids)

print()
print("=" * 90)
print("DESCARGA DE EVENTS — PITCHAPI")
print("=" * 90)
print()

print(f"Partidos encontrados: {len(match_ids)}")
print()

# ============================================================
# DESCARGAR EVENTS
# ============================================================

descargados = 0
ya_existian = 0
errores = 0

for i, match_id in enumerate(match_ids, start=1):

    archivo_salida = CARPETA / f"{match_id}_events.json"

    print(
        f"[{i}/{len(match_ids)}] {match_id}",
        end=" "
    )

    # Si ya existe, no lo volvemos a pedir
    if archivo_salida.exists():

        print("-> YA EXISTE")

        ya_existian += 1
        continue

    url = f"{BASE_URL}/matches/{match_id}/events"

    try:

        response = session.get(
            url,
            timeout=30
        )

        print(f"-> HTTP {response.status_code}")

        if response.status_code == 200:

            data = response.json()

            archivo_salida.write_text(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=2
                ),
                encoding="utf-8"
            )

            descargados += 1

        elif response.status_code == 429:

            print("   Rate limit. Esperando 5 segundos...")
            time.sleep(5)

            response = session.get(
                url,
                timeout=30
            )

            if response.status_code == 200:

                data = response.json()

                archivo_salida.write_text(
                    json.dumps(
                        data,
                        ensure_ascii=False,
                        indent=2
                    ),
                    encoding="utf-8"
                )

                descargados += 1

            else:

                errores += 1
                print(
                    f"   ERROR después del reintento: "
                    f"{response.status_code}"
                )

        else:

            errores += 1

            try:
                print(
                    "   ",
                    response.json()
                )
            except Exception:
                print(
                    "   ",
                    response.text[:300]
                )

    except Exception as e:

        errores += 1

        print(
            f"   ERROR: {e}"
        )

print()
print("=" * 90)
print("RESUMEN")
print("=" * 90)
print()
print(f"Descargados : {descargados}")
print(f"Ya existían : {ya_existian}")
print(f"Errores     : {errores}")
print()
print("Listo.")