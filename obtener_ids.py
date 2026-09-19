from curl_cffi import requests
import json

# ==========================================
# CONFIGURACIÓN
# ==========================================

TOURNAMENT_ID = 155
SEASON_ID = 87913

# ==========================================
# OBTENER TODOS LOS PARTIDOS
# ==========================================

print("================================")
print("BUSCANDO PARTIDOS DE LA TEMPORADA")
print("================================")

todos_los_partidos = []

page = 0

while True:

    print(f"Descargando página {page}...")

    url = (
        f"https://www.sofascore.com/api/v1/"
        f"unique-tournament/{TOURNAMENT_ID}/"
        f"season/{SEASON_ID}/events/last/{page}"
    )

    response = requests.get(
        url,
        impersonate="chrome"
    )

    if response.status_code != 200:
        print("ERROR HTTP:", response.status_code)
        break

    data = response.json()

    eventos = data.get("events", [])

    print("Partidos encontrados:", len(eventos))

    todos_los_partidos.extend(eventos)

    if not data.get("hasNextPage", False):
        break

    page += 1


# ==========================================
# FILTRAR PARTIDOS TERMINADOS
# ==========================================

partidos_terminados = []

for partido in todos_los_partidos:

    if partido.get("status", {}).get("type") == "finished":
        partidos_terminados.append(partido)


# ==========================================
# GUARDAR TODOS LOS DATOS
# ==========================================

with open(
    "partidos_temporada.json",
    "w",
    encoding="utf-8"
) as archivo:

    json.dump(
        todos_los_partidos,
        archivo,
        ensure_ascii=False,
        indent=2
    )


# ==========================================
# GUARDAR SOLO IDS TERMINADOS
# ==========================================

ids_terminados = [
    partido["id"]
    for partido in partidos_terminados
]


with open(
    "ids_partidos_terminados.json",
    "w",
    encoding="utf-8"
) as archivo:

    json.dump(
        ids_terminados,
        archivo,
        ensure_ascii=False,
        indent=2
    )


# ==========================================
# RESUMEN
# ==========================================

print()
print("================================")
print("PROCESO TERMINADO")
print("================================")

print("TOTAL PARTIDOS:", len(todos_los_partidos))
print("PARTIDOS TERMINADOS:", len(partidos_terminados))
print("PARTIDOS NO TERMINADOS:",
      len(todos_los_partidos) - len(partidos_terminados))

print()
print("ARCHIVOS CREADOS:")
print(" - partidos_temporada.json")
print(" - ids_partidos_terminados.json")

print("================================")