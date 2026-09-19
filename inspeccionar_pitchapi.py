import json

with open("pitchapi_partido.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def mostrar_estructura(obj, nivel=0, max_nivel=3):
    indent = "  " * nivel

    if nivel > max_nivel:
        return

    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, dict):
                print(f"{indent}{key}: {{...}}")
                mostrar_estructura(value, nivel + 1, max_nivel)
            elif isinstance(value, list):
                print(f"{indent}{key}: [lista - {len(value)} elementos]")
                if value:
                    print(f"{indent}  Primer elemento:")
                    mostrar_estructura(value[0], nivel + 2, max_nivel)
            else:
                print(f"{indent}{key}: {value}")

    elif isinstance(obj, list):
        print(f"{indent}LISTA - {len(obj)} elementos")


print("=" * 70)
print("ESTRUCTURA DEL JSON DE PITCHAPI")
print("=" * 70)
print()

mostrar_estructura(data)

print()
print("=" * 70)
print("FIN")
print("=" * 70)