import json
import glob
import collections

FILES = glob.glob("datos/pitchapi/lineups/*_lineups.json")

position_data = collections.defaultdict(list)

for file in FILES:
    try:
        with open(file, "r", encoding="utf-8") as f:
            raw = json.load(f)

        data = raw.get("data", raw)

        for side in ("home", "away"):
            team = data.get(side, {})
            starters = team.get("starters") or []

            for player in starters:
                position_id = player.get("position_id")

                if position_id is None:
                    continue

                position_data[position_id].append({
                    "pitch_x": player.get("pitch_x"),
                    "pitch_y": player.get("pitch_y"),
                    "name": player.get("name"),
                })

    except Exception as e:
        print(f"ERROR en {file}: {e}")


print("ARCHIVOS:", len(FILES))
print()
print("POSITION_ID | CANTIDAD | EJEMPLOS")
print("-" * 80)

for position_id in sorted(position_data):
    examples = position_data[position_id][:8]

    print(
        f"{position_id:>10} | "
        f"{len(position_data[position_id]):>8} | "
        f"{examples}"
    )