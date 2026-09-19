import pandas as pd

df = pd.read_csv("datos/dataset_jugadores.csv")

# Solo jugadores que realmente participaron
df = df[df["minutesPlayed"].notna()].copy()

print("\n=== GOLES Y ASISTENCIAS POR POSICION ===\n")

for posicion in ["G", "D", "M", "F"]:

    datos = df[df["position"] == posicion]

    goles = datos["goals"].fillna(0)
    asistencias = datos["goalAssist"].fillna(0)

    print(f"--- POSICION {posicion} ---")
    print(f"Jugadores/actuaciones: {len(datos)}")

    print(f"Goles totales: {goles.sum():.0f}")
    print(f"Actuaciones con gol: {(goles > 0).sum()}")
    print(f"Promedio de goles (todos): {goles.mean():.3f}")
    print(f"Maximo de goles en un partido: {goles.max():.0f}")

    print(f"Asistencias totales: {asistencias.sum():.0f}")
    print(f"Actuaciones con asistencia: {(asistencias > 0).sum()}")
    print(f"Promedio de asistencias (todos): {asistencias.mean():.3f}")
    print(f"Maximo de asistencias en un partido: {asistencias.max():.0f}")

    print()

print("=== TOP ACTUACIONES POR GOLES ===\n")

top_goles = df[df["goals"].fillna(0) > 0].sort_values(
    "goals", ascending=False
).head(20)

print(
    top_goles[
        [
            "player_name",
            "team_name",
            "position",
            "minutesPlayed",
            "goals",
            "goalAssist"
        ]
    ].to_string(index=False)
)

print("\n=== TOP ACTUACIONES POR ASISTENCIAS ===\n")

top_asistencias = df[df["goalAssist"].fillna(0) > 0].sort_values(
    "goalAssist", ascending=False
).head(20)

print(
    top_asistencias[
        [
            "player_name",
            "team_name",
            "position",
            "minutesPlayed",
            "goals",
            "goalAssist"
        ]
    ].to_string(index=False)
)