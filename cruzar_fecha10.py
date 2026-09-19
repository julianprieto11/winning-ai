import json
import glob


# ============================================================
# PARTIDOS DE LA FECHA 10
# ============================================================

PARTIDOS_FECHA10 = {
    "16667329": ("Central Córdoba", "Defensa y Justicia"),
    "16667338": ("Racing Club", "Sarmiento"),
    "16667328": ("Gimnasia LP", "Banfield"),
    "16667336": ("Gimnasia Mendoza", "Deportivo Riestra"),
    "16667325": ("Unión", "Independiente"),
    "16667327": ("River Plate", "Huracán"),
    "16667333": ("Instituto", "Talleres"),
    "16667340": ("San Lorenzo", "Boca Juniors"),
    "16667330": ("Platense", "Newell's Old Boys"),
    "16667332": ("Rosario Central", "Argentinos Juniors"),
    "16667326": ("Belgrano", "Estudiantes de Río Cuarto"),
    "16671623": ("Vélez Sarsfield", "Tigre"),
    "16667335": ("Aldosivi", "Atlético Tucumán"),
    "16667331": ("Barracas Central", "Independiente Rivadavia"),
    "16667337": ("Lanús", "Estudiantes"),
}


# ============================================================
# EQUIVALENCIAS DE NOMBRES
# ============================================================

EQUIVALENCIAS = {
    "Central Córdoba": [
        "Central Córdoba de Santiago",
    ],

    "Defensa y Justicia": [
        "Defensa y Justicia",
    ],

    "Racing Club": [
        "Racing Club",
    ],

    "Sarmiento": [
        "Sarmiento",
    ],

    "Gimnasia LP": [
        "Gimnasia LP",
    ],

    "Banfield": [
        "Banfield",
    ],

    "Gimnasia Mendoza": [
        "Gimnasia Mendoza",
    ],

    "Deportivo Riestra": [
        "Deportivo Riestra",
    ],

    "Unión": [
        "Unión",
        "Unión de Santa Fe",
    ],

    "Independiente": [
        "Independiente",
    ],

    "River Plate": [
        "River Plate",
    ],

    "Huracán": [
        "Huracán",
    ],

    "Instituto": [
        "Instituto",
    ],

    "Talleres": [
        "Talleres",
    ],

    "San Lorenzo": [
        "San Lorenzo",
    ],

    "Boca Juniors": [
        "Boca Juniors",
    ],

    "Platense": [
        "Club Atlético Platense",
    ],

    "Newell's Old Boys": [
        "Newell's Old Boys",
    ],

    "Rosario Central": [
        "Rosario Central",
    ],

    "Argentinos Juniors": [
        "Argentinos Juniors",
    ],

    "Belgrano": [
        "Belgrano",
    ],

    "Estudiantes de Río Cuarto": [
        "Estudiantes de Río Cuarto",
    ],

    "Vélez Sarsfield": [
        "Vélez Sarsfield",
    ],

    "Tigre": [
        "Tigre",
    ],

    "Aldosivi": [
        "Aldosivi",
    ],

    "Atlético Tucumán": [
        "Atlético Tucumán",
    ],

    "Barracas Central": [
        "Barracas Central",
    ],

    "Independiente Rivadavia": [
        "Independiente Rivadavia",
    ],

    "Lanús": [
        "Lanús",
    ],

    "Estudiantes": [
        "Estudiantes",
    ],
}


# ============================================================
# CARGAR PARTIDOS DE PITCHAPI
# ============================================================

pitchapi = []

archivos = glob.glob("datos/pitchapi/matches/*.json")

for archivo in archivos:

    with open(archivo, encoding="utf-8") as f:
        data = json.load(f)

    partido = data["data"]

    pitchapi.append({
        "pitch_id": partido["id"],
        "home": partido["home_team"]["name"],
        "away": partido["away_team"]["name"],
    })


# ============================================================
# FUNCIÓN PARA COMPARAR NOMBRES
# ============================================================

def coincide(nombre_pitchapi, nombre_buscado):

    if nombre_pitchapi == nombre_buscado:
        return True

    alternativas = EQUIVALENCIAS.get(nombre_buscado, [])

    return nombre_pitchapi in alternativas


# ============================================================
# CRUZAR LOS 15 PARTIDOS
# ============================================================

print()
print("CRUCE FECHA 10")
print("=" * 80)
print()

encontrados = 0


for sofa_id, (home_buscado, away_buscado) in PARTIDOS_FECHA10.items():

    partido_encontrado = None

    for partido in pitchapi:

        home_ok = coincide(
            partido["home"],
            home_buscado
        )

        away_ok = coincide(
            partido["away"],
            away_buscado
        )

        if home_ok and away_ok:

            partido_encontrado = partido
            break


    if partido_encontrado:

        encontrados += 1

        print(
            f"{sofa_id} -> "
            f"{partido_encontrado['pitch_id']} | "
            f"{home_buscado} vs {away_buscado}"
        )

    else:

        print(
            f"{sofa_id} -> NO ENCONTRADO | "
            f"{home_buscado} vs {away_buscado}"
        )


# ============================================================
# RESUMEN
# ============================================================

print()
print("=" * 80)
print(f"Partidos encontrados: {encontrados}/15")
print()

if encontrados == 15:

    print("OK: los 15 partidos de la Fecha 10 fueron vinculados correctamente.")

else:

    print("ATENCION: todavía hay partidos sin vincular.")

print()