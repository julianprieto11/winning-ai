import pandas as pd

df = pd.read_csv("datos/contexto_equipos.csv")
df["date"] = pd.to_datetime(df["date"])

df = df.sort_values(["team_id", "date", "match_id"]).copy()

rows = []


def calcular_forma(historial):
    ultimos_5 = historial[-5:]

    pj = len(ultimos_5)

    ganados = sum(x["resultado"] == "G" for x in ultimos_5)
    empatados = sum(x["resultado"] == "E" for x in ultimos_5)
    perdidos = sum(x["resultado"] == "P" for x in ultimos_5)

    gf = sum(x["gf"] for x in ultimos_5)
    gc = sum(x["gc"] for x in ultimos_5)
    pts = sum(x["pts"] for x in ultimos_5)

    return {
        "partidos": pj,
        "ganados": ganados,
        "empatados": empatados,
        "perdidos": perdidos,
        "goles_favor": gf,
        "goles_contra": gc,
        "diferencia_gol": gf - gc,
        "puntos": pts,
        "prom_goles_favor": gf / pj if pj else 0,
        "prom_goles_contra": gc / pj if pj else 0,
    }


for team_id, grupo in df.groupby("team_id", sort=False):

    historial_local = []
    historial_visitante = []

    for _, r in grupo.iterrows():

        forma_local = calcular_forma(historial_local)
        forma_visitante = calcular_forma(historial_visitante)

        fila = {
            "match_id": r["match_id"],
            "date": r["date"].date(),
            "team_id": r["team_id"],
            "team_name": r["team_name"],
        }

        for clave, valor in forma_local.items():
            fila[f"local_ultimos_5_{clave}"] = valor

        for clave, valor in forma_visitante.items():
            fila[f"visitante_ultimos_5_{clave}"] = valor

        rows.append(fila)

        if r["goles_favor"] > r["goles_contra"]:
            resultado = "G"
            pts = 3
        elif r["goles_favor"] == r["goles_contra"]:
            resultado = "E"
            pts = 1
        else:
            resultado = "P"
            pts = 0

        registro = {
            "resultado": resultado,
            "gf": r["goles_favor"],
            "gc": r["goles_contra"],
            "pts": pts,
        }

        if r["local_visitante"] == "LOCAL":
            historial_local.append(registro)
        else:
            historial_visitante.append(registro)


out = pd.DataFrame(rows)

out.to_csv(
    "datos/forma_local_visitante_equipos.csv",
    index=False,
    encoding="utf-8-sig"
)

print("CREADO:", len(out), "filas")
print("COLUMNAS:", len(out.columns))
print()
print(out.head(10).to_string(index=False))