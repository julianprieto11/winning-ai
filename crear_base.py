import sqlite3
import os

# ==========================================
# CONFIGURACIÓN
# ==========================================

CARPETA_DATOS = "datos"

os.makedirs(CARPETA_DATOS, exist_ok=True)

BASE_DATOS = os.path.join(
    CARPETA_DATOS,
    "winning_ai.db"
)

# ==========================================
# CONECTAR CON SQLITE
# ==========================================

conexion = sqlite3.connect(BASE_DATOS)

cursor = conexion.cursor()

# ==========================================
# TABLA: PARTIDOS
# ==========================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS partidos (

    event_id INTEGER PRIMARY KEY,

    fecha INTEGER,

    temporada_id INTEGER,

    torneo_id INTEGER,

    ronda INTEGER,

    estado TEXT,

    local_id INTEGER,

    local_nombre TEXT,

    visitante_id INTEGER,

    visitante_nombre TEXT,

    goles_local INTEGER,

    goles_visitante INTEGER,

    arbitro_id INTEGER,

    arbitro_nombre TEXT
)
""")

# ==========================================
# TABLA: JUGADORES
# ==========================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS jugadores (

    jugador_id INTEGER PRIMARY KEY,

    nombre TEXT,

    nombre_corto TEXT,

    slug TEXT
)
""")

# ==========================================
# TABLA: PARTICIPACIÓN
# ==========================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS jugador_partido (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    event_id INTEGER,

    jugador_id INTEGER,

    equipo_id INTEGER,

    equipo_nombre TEXT,

    titular INTEGER,

    posicion TEXT,

    FOREIGN KEY (event_id)
        REFERENCES partidos(event_id),

    FOREIGN KEY (jugador_id)
        REFERENCES jugadores(jugador_id)
)
""")

# ==========================================
# TABLA: ESTADÍSTICAS
# ==========================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS estadisticas_jugador (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    event_id INTEGER,

    jugador_id INTEGER,

    estadisticas_json TEXT,

    FOREIGN KEY (event_id)
        REFERENCES partidos(event_id),

    FOREIGN KEY (jugador_id)
        REFERENCES jugadores(jugador_id)
)
""")

# ==========================================
# TABLA: INCIDENTES
# ==========================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS incidentes (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    event_id INTEGER,

    incidente_json TEXT,

    FOREIGN KEY (event_id)
        REFERENCES partidos(event_id)
)
""")

# ==========================================
# TABLA: ESTADÍSTICAS GENERALES
# ==========================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS estadisticas_partido (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    event_id INTEGER,

    periodo TEXT,

    estadisticas_json TEXT,

    FOREIGN KEY (event_id)
        REFERENCES partidos(event_id)
)
""")

# ==========================================
# ÍNDICES
# ==========================================

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_jugador_partido_jugador
ON jugador_partido(jugador_id)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_jugador_partido_evento
ON jugador_partido(event_id)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_estadisticas_jugador
ON estadisticas_jugador(jugador_id)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_incidentes_evento
ON incidentes(event_id)
""")

# ==========================================
# GUARDAR
# ==========================================

conexion.commit()

conexion.close()

# ==========================================
# RESULTADO
# ==========================================

print("================================")
print("BASE DE DATOS CREADA")
print("================================")
print("ARCHIVO:", BASE_DATOS)
print()
print("TABLAS CREADAS:")
print("- partidos")
print("- jugadores")
print("- jugador_partido")
print("- estadisticas_jugador")
print("- incidentes")
print("- estadisticas_partido")
print("================================")