from curl_cffi import requests
import json
import os
import time

# ==========================================
# CONFIGURACIÓN
# ==========================================

ARCHIVO_IDS = "ids_partidos_terminados.json"
CARPETA_SALIDA = "datos/partidos"

# ==========================================
# PREPARAR CARPETA
# ==========================================

os.makedirs(CARPETA_SALIDA, exist_ok=True)

# ==========================================
# CARGAR IDS
# ==========================================

with open(
    ARCHIVO_IDS,
    "r",
    encoding="utf-8"
) as archivo:
    ids = json.load(archivo)

total = len(ids)

print("================================")
print("DESCARGADOR DE TEMPORADA")
print("================================")
print("PARTIDOS A PROCESAR:", total)
print()

# ==========================================
# CONTADORES
# ==========================================

descargados = 0
saltados = 0
errores = 0

# ==========================================
# PROCESAR PARTIDOS
# ==========================================

for numero, event_id in enumerate(ids, start=1):

    archivo_salida = os.path.join(
        CARPETA_SALIDA,
        f"{event_id}.json"
    )

    # --------------------------------------
    # SI YA EXISTE, LO SALTAMOS
    # --------------------------------------

    if os.path.exists(archivo_salida):

        print(
            f"[{numero}/{total}] "
            f"YA EXISTE → {event_id}"
        )

        saltados += 1
        continue

    print()
    print(
        f"[{numero}/{total}] "
        f"DESCARGANDO → {event_id}"
    )

    try:

        base_url = (
            f"https://www.sofascore.com/api/v1/event/{event_id}"
        )

        # ----------------------------------
        # EVENT
        # ----------------------------------

        event_response = requests.get(
            base_url,
            impersonate="chrome"
        )

        event_response.raise_for_status()

        event_data = event_response.json()

        # ----------------------------------
        # LINEUPS
        # ----------------------------------

        lineups_response = requests.get(
            f"{base_url}/lineups",
            impersonate="chrome"
        )

        lineups_response.raise_for_status()

        lineups_data = lineups_response.json()

        # ----------------------------------
        # INCIDENTS
        # ----------------------------------

        incidents_response = requests.get(
            f"{base_url}/incidents",
            impersonate="chrome"
        )

        incidents_response.raise_for_status()

        incidents_data = incidents_response.json()

        # ----------------------------------
        # STATISTICS
        # ----------------------------------

        statistics_response = requests.get(
            f"{base_url}/statistics",
            impersonate="chrome"
        )

        statistics_response.raise_for_status()

        statistics_data = statistics_response.json()

        # ----------------------------------
        # UNIFICAR
        # ----------------------------------

        partido_completo = {
            "event": event_data,
            "lineups": lineups_data,
            "incidents": incidents_data,
            "statistics": statistics_data
        }

        # ----------------------------------
        # GUARDAR
        # ----------------------------------

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

        # ----------------------------------
        # MOSTRAR INFORMACIÓN
        # ----------------------------------

        home = event_data["event"]["homeTeam"]["name"]
        away = event_data["event"]["awayTeam"]["name"]

        print(
            f"    OK → {home} vs {away}"
        )

        descargados += 1

        # Pequeña pausa para no bombardear el servidor
        time.sleep(0.5)

    except Exception as error:

        print(
            f"    ERROR → {event_id}"
        )

        print(
            f"    {error}"
        )

        errores += 1

        # Continuamos con el siguiente partido
        continue


# ==========================================
# RESUMEN FINAL
# ==========================================

print()
print("================================")
print("DESCARGA TERMINADA")
print("================================")
print("TOTAL:", total)
print("DESCARGADOS:", descargados)
print("YA EXISTÍAN:", saltados)
print("ERRORES:", errores)
print("================================")