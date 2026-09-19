import sqlite3
import json
from collections import defaultdict

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
# OBTENER ESTADÍSTICAS
# ==========================================

cursor.execute("""
SELECT estadisticas_json
FROM estadisticas_jugador
""")

registros = cursor.fetchall()

# ==========================================
# ANALIZAR CAMPOS
# ==========================================

campos = defaultdict(int)

for registro in registros:

    estadisticas = json.loads(
        registro[0]
    )

    for campo in estadisticas:

        campos[campo] += 1

# ==========================================
# RESULTADO
# ==========================================

print("================================")
print("ANÁLISIS DE CAMPOS SOFASCORE")
print("================================")

print(
    "REGISTROS ANALIZADOS:",
    len(registros)
)

print(
    "CAMPOS DISTINTOS:",
    len(campos)
)

print()

# ==========================================
# MOSTRAR CAMPOS
# ==========================================

for campo in sorted(campos):

    cantidad = campos[campo]

    porcentaje = (
        cantidad / len(registros)
    ) * 100

    print(
        f"{campo:45} "
        f"{cantidad:6} "
        f"{porcentaje:6.2f}%"
    )

# ==========================================
# CERRAR
# ==========================================

conexion.close()

print()
print("================================")
print("ANÁLISIS TERMINADO")
print("================================")