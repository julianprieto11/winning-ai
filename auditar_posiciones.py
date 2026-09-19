import json
from pathlib import Path
from collections import Counter

CARPETA = Path("datos/pitchapi")

archivos = sorted(
    archivo
    for archivo in CARPETA.glob("*_players.json")
    if not archivo.name.endswith("_advanced_players.json")
)

print()
print("=" * 100)
print("AUDITORÍA — POSICIONES")
print("=" * 100)
print()

print(f"Partidos encontrados: {len(archivos)}")

# ============================================================
# BUSCAR TODOS LOS CAMPOS RELACIONADOS CON POSICIÓN
# ============================================================

campos = Counter()
valores_position_id = Counter()

ejemplos = []

for archivo in archivos:

    try:
        data = json.loads(
            archivo.read_text(encoding="utf-8")
        )
    except Exception:
        continue

    jugadores = data.get("data", [])

    if not isinstance(jugadores, list):
        continue

    for jugador in jugadores:

        player = jugador.get("player", {})

        # Campos directos del objeto player
        for key, value in player.items():

            if "position" in key.lower():
                campos[f"player.{key}"] += 1

                if key == "position_id":
                    valores_position_id[str(value)] += 1

        # Buscar recursivamente cualquier campo que contenga position
        def buscar_position(obj, ruta=""):

            if isinstance(obj, dict):

                for key, value in obj.items():

                    nueva_ruta = (
                        f"{ruta}.{key}"
                        if ruta
                        else key
                    )

                    if "position" in key.lower():
                        campos[nueva_ruta] += 1

                    buscar_position(value, nueva_ruta)

            elif isinstance(obj, list):

                for i, item in enumerate(obj):
                    buscar_position(item, f"{ruta}[{i}]")

        buscar_position(jugador)

        if len(ejemplos) < 10:
            ejemplos.append(jugador)

# ============================================================
# CAMPOS ENCONTRADOS
# ============================================================

print()
print("=" * 100)
print("CAMPOS RELACIONADOS CON POSICIÓN")
print("=" * 100)

if campos:

    for campo, cantidad in sorted(campos.items()):
        print(f"{campo:<50} apariciones={cantidad}")

else:
    print("No se encontraron campos relacionados con posición.")

# ============================================================
# POSITION_ID
# ============================================================

print()
print("=" * 100)
print("VALORES DE position_id")
print("=" * 100)

if valores_position_id:

    for valor, cantidad in valores_position_id.most_common():
        print(f"{valor:<20} {cantidad}")

else:

    print("No se encontraron valores de position_id.")

# ============================================================
# EJEMPLOS
# ============================================================

print()
print("=" * 100)
print("EJEMPLO DE OBJETOS PLAYER")
print("=" * 100)

for jugador in ejemplos[:3]:

    print()
    print(json.dumps(
        jugador.get("player", {}),
        indent=2,
        ensure_ascii=False
    ))

print()
print("=" * 100)
print("FIN")
print("=" * 100)