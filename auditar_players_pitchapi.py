import json
from pathlib import Path

BASE = Path("datos/pitchapi")

# Buscar solamente archivos *_players.json
# y excluir *_advanced_players.json
archivos = [
    archivo
    for archivo in BASE.glob("*_players.json")
    if not archivo.name.endswith("_advanced_players.json")
]

print("=" * 100)
print("AUDITORÍA PITCHAPI / PLAYERS")
print("=" * 100)
print(f"Archivos encontrados: {len(archivos)}")
print()

# ============================================================
# CAMPOS QUE QUEREMOS AUDITAR
# ============================================================

OBJETIVOS = {
    "Goles": ("top_stats", "Goals"),
    "Asistencias": ("top_stats", "Assists"),
    "Toques": ("attack", "Touches"),
    "Toques área rival": ("attack", "Touches in opposition box"),
    "Duelos ganados": ("duels", "Duels won"),
    "Duelos perdidos": ("duels", "Duels lost"),
}

# ============================================================
# CONTADORES
# ============================================================

registros = 0

resultados = {
    nombre: {
        "disponibles": 0,
        "missing": 0,
        "null": 0,
        "cero": 0,
    }
    for nombre in OBJETIVOS
}

ejemplos = {}

errores = 0

# ============================================================
# RECORRER ARCHIVOS
# ============================================================

for archivo in archivos:

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            data = json.load(f)

    except Exception as e:
        errores += 1
        print(f"ERROR leyendo {archivo.name}: {e}")
        continue

    # En nuestros JSON, "data" es una LISTA de jugadores
    jugadores = data.get("data", [])

    if not isinstance(jugadores, list):
        errores += 1
        print(
            f"FORMATO inesperado en {archivo.name}: "
            f"data es {type(jugadores).__name__}"
        )
        continue

    # ========================================================
    # RECORRER JUGADORES
    # ========================================================

    for jugador in jugadores:

        registros += 1

        stats = jugador.get("stats", [])

        if not isinstance(stats, list):
            continue

        # Convertimos los grupos de estadísticas
        # en un diccionario para buscarlos fácilmente.
        grupos = {}

        for grupo in stats:

            grupo_key = grupo.get("key")

            if grupo_key:
                grupos[grupo_key] = grupo.get("stats", {})

        # ====================================================
        # AUDITAR CADA CAMPO
        # ====================================================

        for nombre, (grupo, campo) in OBJETIVOS.items():

            grupo_stats = grupos.get(grupo)

            # El grupo directamente no existe
            if grupo_stats is None:
                resultados[nombre]["missing"] += 1
                continue

            dato = grupo_stats.get(campo)

            # El campo no existe
            if dato is None:
                resultados[nombre]["missing"] += 1
                continue

            stat = dato.get("stat", {})

            valor = stat.get("value")

            # El campo existe pero el valor es null
            if valor is None:
                resultados[nombre]["null"] += 1
                continue

            # =================================================
            # DATO DISPONIBLE
            # =================================================

            resultados[nombre]["disponibles"] += 1

            # IMPORTANTE:
            # 0 ES UN DATO DISPONIBLE.
            # NO se considera missing.
            if valor == 0:
                resultados[nombre]["cero"] += 1

            # Guardar un ejemplo
            if nombre not in ejemplos:

                jugador_info = jugador.get("player", {})

                ejemplos[nombre] = {
                    "archivo": archivo.name,
                    "jugador": jugador_info.get("name"),
                    "valor": valor,
                }


# ============================================================
# RESULTADOS
# ============================================================

print("=" * 100)
print("RESULTADOS")
print("=" * 100)
print()

print(f"Archivos procesados correctamente: {len(archivos) - errores}")
print(f"Errores de lectura/formato:        {errores}")
print(f"Registros de jugadores:             {registros}")
print()

for nombre, datos in resultados.items():

    cobertura = (
        datos["disponibles"] / registros * 100
        if registros
        else 0
    )

    print(nombre)
    print("-" * 100)

    print(f"Disponibles: {datos['disponibles']}")
    print(f"Missing:     {datos['missing']}")
    print(f"Null:        {datos['null']}")
    print(f"Ceros:       {datos['cero']}")
    print(f"Cobertura:   {cobertura:.2f}%")

    if nombre in ejemplos:

        ejemplo = ejemplos[nombre]

        print(
            f"Ejemplo:     {ejemplo['jugador']} | "
            f"{ejemplo['valor']} | "
            f"{ejemplo['archivo']}"
        )

    print()


# ============================================================
# RESUMEN 45%
# ============================================================

print("=" * 100)
print("RESUMEN PARA REGLA DEL 45%")
print("=" * 100)
print()

for nombre, datos in resultados.items():

    cobertura = (
        datos["disponibles"] / registros * 100
        if registros
        else 0
    )

    if cobertura >= 45:
        estado = "UTILIZABLE"
    else:
        estado = "PENDIENTE"

    print(
        f"{nombre:<25} "
        f"{cobertura:>7.2f}%   "
        f"{estado}"
    )


# ============================================================
# ACLARACIÓN DE LA REGLA
# ============================================================

print()
print("=" * 100)
print("IMPORTANTE")
print("=" * 100)
print()

print("45% = COBERTURA DEL DATO.")
print("45% != FRECUENCIA DE OCURRENCIA.")
print()

print("Un valor 0 cuenta como DATO DISPONIBLE.")
print("Solo missing/null/ausencia del campo cuenta como falta de dato.")
print()

print("=" * 100)
print("FIN DE AUDITORÍA")
print("=" * 100)