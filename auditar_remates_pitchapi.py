import json
from pathlib import Path

BASE = Path("datos/pitchapi")

archivos = [
    archivo
    for archivo in BASE.glob("*_players.json")
    if not archivo.name.endswith("_advanced_players.json")
]

CAMPOS = {
    "Remates totales": ("total_shots",),
    "Remates al arco": ("ShotsOnTarget",),
    "Remates fuera": ("ShotsOffTarget",),
    "Remates bloqueados": ("blocked_shots",),
    "Remates al palo": ("shots_woodwork",),
}

contadores = {}

for nombre, keys in CAMPOS.items():
    contadores[nombre] = {
        "disponibles": 0,
        "missing": 0,
        "null": 0,
        "ceros": 0,
    }

total_registros = 0

for archivo in archivos:

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        continue

    jugadores = data.get("data", [])

    for jugador in jugadores:

        total_registros += 1

        encontrados = {}

        for grupo in jugador.get("stats", []):

            stats = grupo.get("stats", {})

            if not isinstance(stats, dict):
                continue

            for nombre_campo, dato in stats.items():

                key = dato.get("key", "")

                if key in [
                    "total_shots",
                    "ShotsOnTarget",
                    "ShotsOffTarget",
                    "blocked_shots",
                    "shots_woodwork",
                ]:

                    valor = dato.get("stat", {}).get("value")
                    encontrados[key] = valor

        for nombre, keys in CAMPOS.items():

            key = keys[0]

            if key not in encontrados:
                contadores[nombre]["missing"] += 1
                continue

            valor = encontrados[key]

            if valor is None:
                contadores[nombre]["null"] += 1
                continue

            contadores[nombre]["disponibles"] += 1

            if valor == 0:
                contadores[nombre]["ceros"] += 1


print("=" * 100)
print("AUDITORÍA DE REMATES - PITCHAPI")
print("=" * 100)

print(f"Archivos procesados: {len(archivos)}")
print(f"Registros de jugadores: {total_registros}")
print()

for nombre, datos in contadores.items():

    cobertura = (
        datos["disponibles"] / total_registros * 100
        if total_registros
        else 0
    )

    print(nombre)
    print(f"Disponibles: {datos['disponibles']}")
    print(f"Missing:     {datos['missing']}")
    print(f"Null:        {datos['null']}")
    print(f"Ceros:       {datos['ceros']}")
    print(f"Cobertura:   {cobertura:.2f}%")

    if cobertura >= 45:
        print("Estado:      UTILIZABLE")
    else:
        print("Estado:      NO UTILIZABLE")

    print("-" * 100)

print("=" * 100)
print("FIN")
print("=" * 100)