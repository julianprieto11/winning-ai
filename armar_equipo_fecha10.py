import pandas as pd

df = pd.read_csv("datos/proyeccion_fecha10.csv")

# Ordenar por proyección
df = df.sort_values("proyeccion", ascending=False).copy()

# Normalizamos posiciones
df["posicion"] = df["posicion"].str.upper()

# ============================================================
# ARMAR XI
# ============================================================

limite_club = 3
equipo = []
clubes = {}

def agregar(jugador):
    club = jugador["equipo"]

    if clubes.get(club, 0) >= limite_club:
        return False

    equipo.append(jugador)
    clubes[club] = clubes.get(club, 0) + 1
    return True


# 1 ARQUERO
for _, jugador in df[df["posicion"] == "G"].iterrows():
    if agregar(jugador):
        break


# 4 DEFENSORES
for _, jugador in df[df["posicion"] == "D"].iterrows():
    if len([x for x in equipo if x["posicion"] == "D"]) >= 4:
        break
    agregar(jugador)


# 3 VOLANTES
for _, jugador in df[df["posicion"] == "M"].iterrows():
    if len([x for x in equipo if x["posicion"] == "M"]) >= 3:
        break
    agregar(jugador)


# 3 DELANTEROS
for _, jugador in df[df["posicion"] == "F"].iterrows():
    if len([x for x in equipo if x["posicion"] == "F"]) >= 3:
        break
    agregar(jugador)


# ============================================================
# MOSTRAR XI
# ============================================================

print()
print("=" * 70)
print("WINNING AI - EQUIPO FECHA 10")
print("=" * 70)

total = 0

for posicion in ["G", "D", "M", "F"]:

    jugadores = [x for x in equipo if x["posicion"] == posicion]

    for jugador in jugadores:

        puntos = jugador["proyeccion"]
        total += puntos

        print(
            f"{posicion} | "
            f"{jugador['jugador']} | "
            f"{jugador['equipo']} | "
            f"{puntos:.2f} pts/90"
        )

print()
print(f"PROYECCION TOTAL: {total:.2f}")

print()
print("JUGADORES POR CLUB")

for club, cantidad in clubes.items():
    print(f"{club}: {cantidad}")


# ============================================================
# FLEX
# ============================================================

print()
print("=" * 70)
print("FLEX - 3 OPCIONES")
print("=" * 70)

usados = {x["jugador"] for x in equipo}

for posicion, nombre in [
    ("D", "DEF"),
    ("M", "VOL"),
    ("F", "DEL")
]:

    candidatos = df[
        (df["posicion"] == posicion)
        & (~df["jugador"].isin(usados))
    ]

    opcion = None

    for _, jugador in candidatos.iterrows():

        if clubes.get(jugador["equipo"], 0) < 3:
            opcion = jugador
            break

    if opcion is not None:

        print(
            f"FLEX {nombre} | "
            f"{opcion['jugador']} | "
            f"{opcion['equipo']} | "
            f"{opcion['proyeccion']:.2f} pts/90"
        )