import pandas as pd

ARCHIVO = "datos/historial_posiciones_pitchapi.csv"

df = pd.read_csv(ARCHIVO)

df["date"] = pd.to_datetime(df["date"])

nombres = [
    "Leandro Paredes",
    "Marcelo Torres",
    "Rodrigo Auzmendi",
    "Rubén Botta",
    "Franco Nicola",
    "Nicolás Watson",
]

for nombre in nombres:
    print()
    print("=" * 60)
    print(nombre)
    print("=" * 60)

    jugador = df[
        df["player_name"].str.lower() == nombre.lower()
    ].sort_values("date")

    print(
        jugador.tail(10)[
            [
                "date",
                "player_name",
                "position_id",
                "starter",
            ]
        ].to_string(index=False)
    )