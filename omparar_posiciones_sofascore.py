import json
from pathlib import Path
from collections import Counter

CARPETA = Path("datos/partidos")

archivos = sorted(CARPETA.glob("*.json"))

print()
print("=" * 100)
print("COMPARACIÓN — POSICIÓN DEL JUGADOR VS POSICIÓN EN EL PARTIDO")
print("=" * 100)
print()

print(f"Archivos encontrados: {len(archivos)}")

comparaciones = Counter()
casos_diferentes = []
total = 0

for archivo in archivos:

    try:
        data = json.loads(
            archivo.read_text(encoding="utf-8")
        )
    except Exception:
        continue

    lineups = data.get("lineups", {})

    for lado in ["home", "away"]:

        equipo = lineups.get(lado, {})
        jugadores = equipo.get("players", [])

        if not isinstance(jugadores, list):
            continue

        for jugador in jugadores:

            player = jugador.get("player", {})

            posicion_jugador = player.get("position")
            posicion_partido = jugador.get("position")

            if posicion_jugador is None or posicion_partido is None:
                continue

            total += 1

            clave = (
                posicion_jugador,
                posicion_partido
            )

            comparaciones[clave] += 1

            if posicion_jugador != posicion_partido:

                if len(casos_diferentes) < 50:

                    casos_diferentes.append({
                        "archivo": archivo.name,
                        "jugador": player.get("name"),
                        "player_id": player.get("id"),
                        "player_position": posicion_jugador,
                        "match_position": posicion_partido,
                        "substitute": jugador.get("substitute"),
                        "minutes": (
                            jugador
                            .get("statistics", {})
                            .get("minutesPlayed")
                        )
                    })

# ============================================================
# TABLA DE COMBINACIONES
# ============================================================

print()
print("=" * 100)
print("COMBINACIONES ENCONTRADAS")
print("=" * 100)

print()
print(
    f"{'PERFIL':<12}"
    f"{'PARTIDO':<12}"
    f"{'CANTIDAD':>12}"
)

print("-" * 40)

for (perfil, partido), cantidad in comparaciones.most_common():

    print(
        f"{perfil:<12}"
        f"{partido:<12}"
        f"{cantidad:>12}"
    )

# ============================================================
# CAMBIOS
# ============================================================

print()
print("=" * 100)
print("CASOS DONDE CAMBIA LA POSICIÓN")
print("=" * 100)

cantidad_diferentes = sum(
    cantidad
    for (perfil, partido), cantidad in comparaciones.items()
    if perfil != partido
)

print()
print(f"Registros comparables: {total}")
print(f"Posiciones diferentes: {cantidad_diferentes}")

print()

for caso in casos_diferentes:

    print(
        f"{caso['jugador']:<30} "
        f"perfil={caso['player_position']} "
        f"partido={caso['match_position']} "
        f"min={caso['minutes']} "
        f"suplente={caso['substitute']}"
    )

print()
print("=" * 100)
print("FIN")
print("=" * 100)