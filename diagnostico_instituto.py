import glob
import json
import os

encontrados = []

for f in glob.glob("datos/partidos/*.json"):
    try:
        with open(f, encoding="utf-8") as archivo:
            d = json.load(archivo)

        e = d.get("event", {})

        nombres = [
            e.get("homeTeam", {}).get("name", ""),
            e.get("awayTeam", {}).get("name", "")
        ]

        if "Instituto" in " ".join(nombres):
            encontrados.append(
                (
                    os.path.basename(f),
                    e.get("id"),
                    nombres
                )
            )

    except Exception:
        pass

print("PARTIDOS ENCONTRADOS:", len(encontrados))

for x in encontrados[-20:]:
    print(x)
