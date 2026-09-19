import pandas as pd


# ============================================================
# CARGAR DATOS
# ============================================================

candidatos = pd.read_csv(
    "datos/candidatos_fecha10.csv"
)

historial = pd.read_csv(
    "datos/dataset_jugadores.csv"
)


# ============================================================
# NORMALIZAR IDs
# ============================================================

candidatos["player_id"] = candidatos["player_id"].astype(str)
historial["player_id"] = historial["player_id"].astype(str)


# ============================================================
# JUGADORES CON HISTORIAL
# ============================================================

ids_historial = set(
    historial["player_id"].dropna().unique()
)

candidatos["tiene_historial"] = (
    candidatos["player_id"].isin(ids_historial)
)


# ============================================================
# RESUMEN
# ============================================================

con_historial = candidatos[
    candidatos["tiene_historial"]
]

sin_historial = candidatos[
    ~candidatos["tiene_historial"]
]


print()
print("=" * 80)
print("AUDITORÍA HISTORIAL - FECHA 10")
print("=" * 80)
print()

print(f"Candidatos totales:       {len(candidatos)}")
print(f"Con historial:            {len(con_historial)}")
print(f"Sin historial:            {len(sin_historial)}")

print()
print("SIN HISTORIAL:")
print("-" * 80)

if len(sin_historial) == 0:
    print("Ninguno.")
else:
    for _, fila in sin_historial.iterrows():
        print(
            f"{fila['jugador']:<30} "
            f"{fila['equipo']:<30} "
            f"{fila['position']}"
        )


print()
print("HISTORIAL POR POSICIÓN:")
print("-" * 80)

print(
    con_historial["position"]
    .value_counts()
)


# ============================================================
# GUARDAR
# ============================================================

salida = "datos/auditoria_historial_fecha10.csv"

candidatos.to_csv(
    salida,
    index=False,
    encoding="utf-8-sig"
)

print()
print(f"Archivo generado: {salida}")
print()