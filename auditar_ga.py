import csv

with open("datos/dataset_winning_pitchapi.csv", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

rows.sort(key=lambda x: float(x["goles_asistencias"] or 0), reverse=True)

print("Jugador | Partido | Goles | Asistencias | G/A puntos")
print("-" * 90)

for x in rows[:30]:
    print(
        f"{x['player_name']} | "
        f"{x['match_id']} | "
        f"goles={x['goals']} | "
        f"asist={x['assists']} | "
        f"GA={x['goles_asistencias']}"
    )
