import json
import glob

buscados = ["Belgrano", "Lanús", "Estudiantes", "Gimnasia Mendoza"]
resultados = {x: set() for x in buscados}

for f in glob.glob("datos/partidos/*.json"):
    try:
        with open(f, encoding="utf-8") as archivo:
            d = json.load(archivo)

        evento = d.get("event", {}).get("event", {})
        home = evento.get("homeTeam", {}).get("name", "")
        away = evento.get("awayTeam", {}).get("name", "")

        texto = (home + " " + away).lower()

        for equipo in buscados:
            if equipo.lower() in texto:
                resultados[equipo].update([home, away])

    except Exception:
        pass

for equipo in buscados:
    print(equipo, ":", sorted(resultados[equipo]))
