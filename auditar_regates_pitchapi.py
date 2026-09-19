import json
from pathlib import Path

BASE = Path("datos/pitchapi")

archivos = list(BASE.glob("*_advanced_players.json"))

total_registros = 0

take_ons_disponibles = 0
take_ons_won_disponibles = 0

take_ons_none = 0
take_ons_won_none = 0

ejemplos = []

for archivo in archivos:

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        continue

    jugadores = data.get("data", {}).get("players", [])

    for jugador in jugadores:

        total_registros += 1

        carrying = jugador.get("carrying", {})

        take_ons = carrying.get("take_ons")
        take_ons_won = carrying.get("take_ons_won")

        if take_ons is not None:
            take_ons_disponibles += 1
        else:
            take_ons_none += 1

        if take_ons_won is not None:
            take_ons_won_disponibles += 1
        else:
            take_ons_won_none += 1

        if (
            len(ejemplos) < 10
            and take_ons is not None
            and take_ons_won is not None
        ):
            ejemplos.append({
                "jugador": jugador.get("player", {}).get("name"),
                "take_ons": take_ons,
                "take_ons_won": take_ons_won,
                "posibles_regates_fallidos": take_ons - take_ons_won,
                "archivo": archivo.name
            })


print("=" * 100)
print("AUDITORÍA DE REGATES / TAKE ONS")
print("=" * 100)

print(f"Archivos avanzados: {len(archivos)}")
print(f"Registros de jugadores: {total_registros}")
print()

print("TAKE ONS")
print(f"Disponibles: {take_ons_disponibles}")
print(f"Missing/None: {take_ons_none}")
print(
    f"Cobertura: "
    f"{(take_ons_disponibles / total_registros * 100):.2f}%"
)
print()

print("TAKE ONS WON")
print(f"Disponibles: {take_ons_won_disponibles}")
print(f"Missing/None: {take_ons_won_none}")
print(
    f"Cobertura: "
    f"{(take_ons_won_disponibles / total_registros * 100):.2f}%"
)
print()

print("=" * 100)
print("EJEMPLOS")
print("=" * 100)

for ejemplo in ejemplos:
    print()
    print(f"Jugador:                    {ejemplo['jugador']}")
    print(f"Take ons:                   {ejemplo['take_ons']}")
    print(f"Take ons won:               {ejemplo['take_ons_won']}")
    print(
        f"Posibles regates fallidos: "
        f"{ejemplo['posibles_regates_fallidos']}"
    )
    print(f"Archivo:                    {ejemplo['archivo']}")

print()
print("=" * 100)
print("FIN")
print("=" * 100)