import json
from pathlib import Path
from collections import Counter

CARPETA = Path("datos/pitchapi/matches")

archivos = sorted(CARPETA.glob("*.json"))

print()
print("=" * 100)
print("AUDITORÍA COMPLETA DE RESULTADOS — PITCHAPI")
print("=" * 100)
print()

print(f"Archivos encontrados: {len(archivos)}")
print()

estados = Counter()

total = 0
completos = 0
sin_marcador = 0
sin_local = 0
sin_visitante = 0

ejemplos_sin_marcador = []

for archivo in archivos:

    try:
        contenido = json.loads(
            archivo.read_text(encoding="utf-8")
        )
    except Exception:
        continue

    partido = contenido.get("data", {})

    total += 1

    status = partido.get("status")

    estados[status] += 1

    home = partido.get("home_team")
    away = partido.get("away_team")

    score_home = partido.get("score_home")
    score_away = partido.get("score_away")

    if not home:
        sin_local += 1

    if not away:
        sin_visitante += 1

    if score_home is not None and score_away is not None:
        completos += 1
    else:
        sin_marcador += 1

        if len(ejemplos_sin_marcador) < 10:
            ejemplos_sin_marcador.append({
                "archivo": archivo.name,
                "status": status,
                "local": home.get("name") if home else None,
                "visitante": away.get("name") if away else None,
                "score_home": score_home,
                "score_away": score_away
            })

print("=" * 100)
print("ESTADOS")
print("=" * 100)

for estado, cantidad in estados.most_common():
    print(f"{str(estado):20} {cantidad}")

print()

print("=" * 100)
print("INTEGRIDAD")
print("=" * 100)

print(f"Total partidos:              {total}")
print(f"Con marcador:                {completos}")
print(f"Sin marcador:                {sin_marcador}")
print(f"Sin equipo local:            {sin_local}")
print(f"Sin equipo visitante:        {sin_visitante}")

print()

print("=" * 100)
print("EJEMPLOS SIN MARCADOR")
print("=" * 100)

for ejemplo in ejemplos_sin_marcador:

    print()
    print(f"Archivo:    {ejemplo['archivo']}")
    print(f"Estado:     {ejemplo['status']}")
    print(f"Local:      {ejemplo['local']}")
    print(f"Visitante:  {ejemplo['visitante']}")
    print(f"Score:      {ejemplo['score_home']} - {ejemplo['score_away']}")

print()
print("=" * 100)
print("FIN")
print("=" * 100)