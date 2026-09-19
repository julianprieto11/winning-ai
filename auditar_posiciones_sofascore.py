import json
from pathlib import Path
from collections import Counter

CARPETA = Path("datos/partidos")

archivos = sorted(CARPETA.glob("*.json"))

print()
print("=" * 100)
print("AUDITORÍA — POSICIONES SOFASCORE")
print("=" * 100)
print()

print(f"Archivos encontrados: {len(archivos)}")

campos = Counter()
valores_position = Counter()
ejemplos = []

def buscar_campos_position(obj, ruta=""):
    if isinstance(obj, dict):
        for key, value in obj.items():

            nueva_ruta = f"{ruta}.{key}" if ruta else key

            if "position" in key.lower():
                campos[nueva_ruta] += 1

            buscar_campos_position(value, nueva_ruta)

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            buscar_campos_position(item, f"{ruta}[{i}]")

# ============================================================
# AUDITORÍA
# ============================================================

for archivo in archivos:

    try:
        data = json.loads(
            archivo.read_text(encoding="utf-8")
        )
    except Exception:
        continue

    buscar_campos_position(data)

    lineups = data.get("lineups", {})

    for lado in ["home", "away"]:

        equipo = lineups.get(lado, {})

        jugadores = equipo.get("players", [])

        if not isinstance(jugadores, list):
            continue

        for jugador in jugadores:

            # Guardamos cualquier valor relacionado con posición
            for key, value in jugador.items():

                if "position" in key.lower():
                    valores_position[f"{key} = {value}"] += 1

            if len(ejemplos) < 10:
                ejemplos.append(jugador)

# ============================================================
# CAMPOS
# ============================================================

print()
print("=" * 100)
print("CAMPOS RELACIONADOS CON POSITION")
print("=" * 100)

if campos:

    for campo, cantidad in sorted(campos.items()):
        print(f"{campo:<70} {cantidad}")

else:
    print("No se encontraron campos relacionados con position.")

# ============================================================
# VALORES
# ============================================================

print()
print("=" * 100)
print("VALORES DE POSICIÓN EN PLAYERS")
print("=" * 100)

if valores_position:

    for valor, cantidad in valores_position.most_common(100):
        print(f"{valor:<50} {cantidad}")

else:
    print("No se encontraron valores.")

# ============================================================
# EJEMPLOS
# ============================================================

print()
print("=" * 100)
print("EJEMPLOS DE JUGADORES DE SOFASCORE")
print("=" * 100)

for i, jugador in enumerate(ejemplos[:5], start=1):

    print()
    print(f"JUGADOR #{i}")
    print("-" * 80)

    print(
        json.dumps(
            jugador,
            indent=2,
            ensure_ascii=False
        )
    )

print()
print("=" * 100)
print("FIN")
print("=" * 100)