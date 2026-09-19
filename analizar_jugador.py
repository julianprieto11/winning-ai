import sqlite3
import json

# ==========================================
# CONFIGURACIÓN
# ==========================================

BASE_DATOS = "datos/winning_ai.db"

# Partido que vamos a analizar
EVENT_ID = 16671607

# ==========================================
# CONECTAR
# ==========================================

conexion = sqlite3.connect(BASE_DATOS)
cursor = conexion.cursor()

# ==========================================
# DATOS DEL PARTIDO
# ==========================================

cursor.execute("""
SELECT
    local_nombre,
    visitante_nombre,
    goles_local,
    goles_visitante
FROM partidos
WHERE event_id = ?
""", (EVENT_ID,))

partido = cursor.fetchone()

print("================================")
print("ANÁLISIS DE PARTIDO")
print("================================")

print(
    partido[0],
    partido[2],
    "-",
    partido[3],
    partido[1]
)

# ==========================================
# JUGADORES
# ==========================================

cursor.execute("""
SELECT
    jp.jugador_id,
    j.nombre,
    jp.equipo_nombre,
    jp.titular,
    jp.posicion,
    ej.estadisticas_json
FROM jugador_partido jp

JOIN jugadores j
    ON j.jugador_id = jp.jugador_id

JOIN estadisticas_jugador ej
    ON ej.event_id = jp.event_id
    AND ej.jugador_id = jp.jugador_id

WHERE jp.event_id = ?

ORDER BY jp.equipo_nombre, j.nombre
""", (EVENT_ID,))

jugadores = cursor.fetchall()

print()
print("================================")
print("JUGADORES DEL PARTIDO")
print("================================")

for numero, jugador in enumerate(jugadores, start=1):

    jugador_id = jugador[0]
    nombre = jugador[1]
    equipo = jugador[2]
    titular = jugador[3]
    posicion = jugador[4]

    print(
        f"{numero:2}. "
        f"{nombre} | "
        f"{equipo} | "
        f"{posicion} | "
        f"{'TITULAR' if titular else 'SUPLENTE'}"
    )

# ==========================================
# ELEGIR UN JUGADOR
# ==========================================

print()
print("================================")
print("SELECCIÓN")
print("================================")

numero = int(
    input("Elegí el número de jugador: ")
)

jugador = jugadores[numero - 1]

jugador_id = jugador[0]
nombre = jugador[1]
equipo = jugador[2]
titular = jugador[3]
posicion = jugador[4]
estadisticas = json.loads(jugador[5])

# ==========================================
# MOSTRAR ESTADÍSTICAS
# ==========================================

print()
print("================================")
print("JUGADOR SELECCIONADO")
print("================================")

print("NOMBRE:", nombre)
print("ID:", jugador_id)
print("EQUIPO:", equipo)
print("POSICIÓN:", posicion)
print(
    "TITULAR:",
    "SI" if titular else "NO"
)

print()
print("================================")
print("ESTADÍSTICAS SOFASCORE")
print("================================")

for campo, valor in sorted(
    estadisticas.items()
):

    print(
        f"{campo:45} → {valor}"
    )

# ==========================================
# INCIDENTES DEL JUGADOR
# ==========================================

cursor.execute("""
SELECT incidente_json
FROM incidentes
WHERE event_id = ?
""", (EVENT_ID,))

incidentes = cursor.fetchall()

print()
print("================================")
print("INCIDENTES DEL JUGADOR")
print("================================")

encontrados = 0

for registro in incidentes:

    incidente = json.loads(
        registro[0]
    )

    # Buscar cualquier aparición del ID
    texto = json.dumps(
        incidente,
        ensure_ascii=False
    )

    if str(jugador_id) in texto:

        print()
        print(
            json.dumps(
                incidente,
                ensure_ascii=False,
                indent=2
            )
        )

        encontrados += 1

if encontrados == 0:

    print(
        "No se encontraron incidentes "
        "individuales para este jugador."
    )

# ==========================================
# CERRAR
# ==========================================

conexion.close()

print()
print("================================")
print("ANÁLISIS TERMINADO")
print("================================")