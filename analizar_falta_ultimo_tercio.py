import json
import glob

archivos = glob.glob("datos/partidos/*.json")

total_jugadores = 0
con_campo = 0
con_valor = 0
total = 0

for archivo in archivos:
    with open(archivo, encoding="utf-8") as f:
        data = json.load(f)

    jugadores = (
        data["lineups"]["home"]["players"]
        + data["lineups"]["away"]["players"]
    )

    for jugador in jugadores:
        stats = jugador.get("statistics", {})

        if stats.get("minutesPlayed") is None:
            continue

        total_jugadores += 1

        if "fouledFinalThird" in stats:
            con_campo += 1

            valor = stats["fouledFinalThird"] or 0

            if valor > 0:
                con_valor += 1
                total += valor

print("Jugadores participantes:", total_jugadores)
print("Con campo fouledFinalThird:", con_campo)
print("Con valor > 0:", con_valor)
print("Total de faltas recibidas en último tercio:", total)

if total_jugadores:
    print(
        "Cobertura:",
        f"{con_campo / total_jugadores * 100:.1f}%"
    )