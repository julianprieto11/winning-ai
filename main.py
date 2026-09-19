import pandas as pd

print("================================")
print("       WINNING AI")
print("================================")

archivo = "data/players.csv"

jugadores = pd.read_csv(archivo)

print("Base de jugadores cargada correctamente.")
print(f"Cantidad de jugadores: {len(jugadores)}")