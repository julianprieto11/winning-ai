import sqlite3

# ==========================================
# CONFIGURACIÓN
# ==========================================

BASE_DATOS = "datos/winning_ai.db"

# ==========================================
# CONECTAR
# ==========================================

conexion = sqlite3.connect(BASE_DATOS)

cursor = conexion.cursor()

# ==========================================
# CONSULTAR TABLAS
# ==========================================

tablas = [
    "partidos",
    "jugadores",
    "jugador_partido",
    "estadisticas_jugador",
    "incidentes",
    "estadisticas_partido"
]

print("================================")
print("VERIFICACIÓN DE BASE DE DATOS")
print("================================")
print()

for tabla in tablas:

    cursor.execute(
        f"SELECT COUNT(*) FROM {tabla}"
    )

    cantidad = cursor.fetchone()[0]

    print(
        f"{tabla}: {cantidad}"
    )

# ==========================================
# PARTIDOS
# ==========================================

cursor.execute("""
SELECT
    COUNT(*),
    MIN(goles_local),
    MAX(goles_local),
    MIN(goles_visitante),
    MAX(goles_visitante)
FROM partidos
""")

resultado = cursor.fetchone()

print()
print("================================")
print("CONTROL DE PARTIDOS")
print("================================")

print("TOTAL:", resultado[0])
print("MÍNIMO GOLES LOCAL:", resultado[1])
print("MÁXIMO GOLES LOCAL:", resultado[2])
print("MÍNIMO GOLES VISITANTE:", resultado[3])
print("MÁXIMO GOLES VISITANTE:", resultado[4])

# ==========================================
# JUGADORES
# ==========================================

cursor.execute("""
SELECT
    COUNT(DISTINCT jugador_id)
FROM jugadores
""")

jugadores = cursor.fetchone()[0]

print()
print("================================")
print("CONTROL DE JUGADORES")
print("================================")

print("JUGADORES DISTINTOS:", jugadores)

# ==========================================
# ALGUNOS PARTIDOS
# ==========================================

cursor.execute("""
SELECT
    event_id,
    local_nombre,
    visitante_nombre,
    goles_local,
    goles_visitante
FROM partidos
ORDER BY fecha
LIMIT 5
""")

partidos = cursor.fetchall()

print()
print("================================")
print("PRIMEROS 5 PARTIDOS")
print("================================")

for partido in partidos:

    print(
        partido[0],
        "→",
        partido[1],
        partido[4] if False else "",
        partido[2],
        "|",
        partido[3],
        "-",
        partido[4]
    )

# ==========================================
# CERRAR
# ==========================================

conexion.close()

print()
print("================================")
print("VERIFICACIÓN TERMINADA")
print("================================")