import pandas as pd

# Cargar contexto de equipos
df = pd.read_csv("datos/contexto_equipos.csv")
df["date"] = pd.to_datetime(df["date"])

# Orden cronológico
df = df.sort_values(["team_id", "date", "match_id"]).copy()

rows = []

# Procesar cada equipo por separado
for team_id, grupo in df.groupby("team_id", sort=False):

    historial = []

    for _, r in grupo.iterrows():

        # SOLO partidos anteriores al partido actual
        ultimos_5 = historial[-5:]

        pj = len(ultimos_5)

        ganados = sum(x["resultado"] == "G" for x in ultimos_5)
        empatados = sum(x["resultado"] == "E" for x in ultimos_5)
        perdidos = sum(x["resultado"] == "P" for x in ultimos_5)

        goles_favor = sum(x["gf"] for x in ultimos_5)
        goles_contra = sum(x["gc"] for x in ultimos_5)

        puntos = sum(x["pts"] for x in ultimos_5)

        rows.append({
            "match_id": r["match_id"],
            "date": r["date"].date(),
            "team_id": r["team_id"],
            "team_name": r["team_name"],

            "forma_ultimos_5_partidos": pj,
            "forma_ultimos_5_ganados": ganados,
            "forma_ultimos_5_empatados": empatados,
            "forma_ultimos_5_perdidos": perdidos,

            "forma_ultimos_5_goles_favor": goles_favor,
            "forma_ultimos_5_goles_contra": goles_contra,
            "forma_ultimos_5_diferencia_gol": goles_favor - goles_contra,

            "forma_ultimos_5_puntos": puntos,

            "forma_ultimos_5_prom_goles_favor": (
                goles_favor / pj if pj else 0
            ),

            "forma_ultimos_5_prom_goles_contra": (
                goles_contra / pj if pj else 0
            ),
        })

        # Resultado del partido actual.
        # Se agrega DESPUÉS de calcular la forma,
        # para evitar utilizar información del futuro.
        if r["goles_favor"] > r["goles_contra"]:
            resultado = "G"
            pts = 3
        elif r["goles_favor"] == r["goles_contra"]:
            resultado = "E"
            pts = 1
        else:
            resultado = "P"
            pts = 0

        historial.append({
            "resultado": resultado,
            "gf": r["goles_favor"],
            "gc": r["goles_contra"],
            "pts": pts,
        })


# Crear DataFrame final
out = pd.DataFrame(rows)

# Guardar
out.to_csv(
    "datos/forma_reciente_equipos.csv",
    index=False,
    encoding="utf-8-sig"
)

print("CREADO:", len(out), "filas")
print("COLUMNAS:", len(out.columns))
print()
print(out.head(10).to_string(index=False))