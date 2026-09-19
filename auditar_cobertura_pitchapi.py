import os
import json

CARPETA = "datos/pitchapi"

# ============================================================
# COBERTURAS QUE YA CONFIRMAMOS
# ============================================================

COBERTURA = {
    "minutes_played": 100.0,
    "passing.passes": 100.0,
    "passing.assists": 100.0,
    "carrying.progressive_carries": 100.0,
    "carrying.miscontrols": 100.0,
    "carrying.dispossessed": 100.0,
    "carrying.take_ons": 100.0,
    "carrying.take_ons_won": 100.0,
    "defending.duels_won": 100.0,
    "defending.tackles": 100.0,
    "defending.interceptions": 100.0,
    "passing.progressive_passes": 100.0,
    "passing.pass_accuracy": 99.2,
}

# ============================================================
# MAPA WINNING → PITCHAPI
#
# DIRECTA:
#   La estadística representa directamente la acción.
#
# DERIVABLE:
#   Podemos obtenerla mediante una fórmula a partir de
#   estadísticas disponibles.
#
# PARCIAL:
#   Hay información relacionada, pero no representa
#   exactamente la acción de Winning.
#
# NO DISPONIBLE:
#   No tenemos el dato necesario en PitchAPI advanced.
# ============================================================

MAPA = [

    {
        "winning": "Minutos jugados",
        "pitchapi": "minutes_played",
        "tipo": "DIRECTA",
        "cobertura": 100.0,
        "observacion": "Correspondencia directa."
    },

    {
        "winning": "Toque en área rival",
        "pitchapi": "—",
        "tipo": "NO DISPONIBLE",
        "cobertura": 0.0,
        "observacion": "carries_into_box mide conducciones que entran al área, no todos los toques."
    },

    {
        "winning": "Toque en último tercio",
        "pitchapi": "—",
        "tipo": "NO DISPONIBLE",
        "cobertura": 0.0,
        "observacion": "carries_into_final_third mide conducciones que entran al tercio, no todos los toques."
    },

    {
        "winning": "Conducción progresiva",
        "pitchapi": "carrying.progressive_carries",
        "tipo": "DIRECTA",
        "cobertura": 100.0,
        "observacion": "Correspondencia semántica directa."
    },

    {
        "winning": "Duelo ganado",
        "pitchapi": "defending.duels_won",
        "tipo": "DIRECTA",
        "cobertura": 100.0,
        "observacion": "Correspondencia directa según el campo disponible."
    },

    {
        "winning": "Duelo perdido",
        "pitchapi": "—",
        "tipo": "NO DISPONIBLE",
        "cobertura": 0.0,
        "observacion": "No tenemos actualmente un campo de duelos perdidos."
    },

    {
        "winning": "Mal control",
        "pitchapi": "carrying.miscontrols",
        "tipo": "DIRECTA",
        "cobertura": 100.0,
        "observacion": "Campo disponible para todos los registros."
    },

    {
        "winning": "Desposesión",
        "pitchapi": "carrying.dispossessed",
        "tipo": "DIRECTA",
        "cobertura": 100.0,
        "observacion": "Campo disponible para todos los registros."
    },

    {
        "winning": "Regate fallido",
        "pitchapi": "carrying.take_ons - carrying.take_ons_won",
        "tipo": "DERIVABLE",
        "cobertura": 100.0,
        "observacion": "Debe validarse contra la definición exacta de Winning antes de usarlo."
    },

    {
        "winning": "Pases",
        "pitchapi": "passing.passes",
        "tipo": "DIRECTA",
        "cobertura": 100.0,
        "observacion": "Dato disponible."
    },

    {
        "winning": "Pases progresivos",
        "pitchapi": "passing.progressive_passes",
        "tipo": "PARCIAL",
        "cobertura": 100.0,
        "observacion": "No forma parte directamente de las reglas de puntos que tenemos identificadas; puede servir como contexto."
    },

    {
        "winning": "Asistencia",
        "pitchapi": "passing.assists",
        "tipo": "DIRECTA",
        "cobertura": 100.0,
        "observacion": "Dato disponible."
    },

    {
        "winning": "Goles",
        "pitchapi": "—",
        "tipo": "NO DISPONIBLE",
        "cobertura": 0.0,
        "observacion": "No aparece como campo de advanced_players."
    },

    {
        "winning": "Resultado del equipo",
        "pitchapi": "event.score",
        "tipo": "DIRECTA",
        "cobertura": 100.0,
        "observacion": "Se puede obtener desde los datos del partido."
    },

    {
        "winning": "Arquero - valla invicta",
        "pitchapi": "event.score + minutes_played",
        "tipo": "DERIVABLE",
        "cobertura": 100.0,
        "observacion": "Se puede determinar a partir del resultado y los minutos, pero requiere identificar correctamente la posición del jugador."
    },

    {
        "winning": "Arquero - goles recibidos",
        "pitchapi": "event.score + team_id + posición",
        "tipo": "DERIVABLE",
        "cobertura": 100.0,
        "observacion": "Se puede obtener del resultado del partido y la pertenencia del jugador al equipo."
    },

    {
        "winning": "Defensor - valla invicta",
        "pitchapi": "event.score + minutes_played",
        "tipo": "DERIVABLE",
        "cobertura": 100.0,
        "observacion": "Se puede determinar a partir del resultado y los minutos."
    },

    {
        "winning": "Defensor - goles recibidos",
        "pitchapi": "event.score + team_id",
        "tipo": "DERIVABLE",
        "cobertura": 100.0,
        "observacion": "Se puede obtener del resultado del partido."
    },

    {
        "winning": "DT - victoria",
        "pitchapi": "event.score",
        "tipo": "DERIVABLE",
        "cobertura": 100.0,
        "observacion": "El resultado permite determinar victoria/empate/derrota."
    },

    {
        "winning": "DT - empate",
        "pitchapi": "event.score",
        "tipo": "DERIVABLE",
        "cobertura": 100.0,
        "observacion": "El resultado permite determinarlo."
    },

    {
        "winning": "DT - derrota",
        "pitchapi": "event.score",
        "tipo": "DERIVABLE",
        "cobertura": 100.0,
        "observacion": "El resultado permite determinarlo."
    },

    {
        "winning": "Capitán",
        "pitchapi": "—",
        "tipo": "NO DISPONIBLE",
        "cobertura": 0.0,
        "observacion": "La designación de capitán requiere otra fuente/dato."
    },
]


# ============================================================
# MOSTRAR MAPA
# ============================================================

print()
print("=" * 120)
print("MAPA WINNING → PITCHAPI")
print("=" * 120)
print()

print(
    f"{'REGLA WINNING':<32}"
    f"{'PITCHAPI':<42}"
    f"{'TIPO':<16}"
    f"{'COB.':>8}"
)

print("-" * 120)

for item in MAPA:

    print(
        f"{item['winning']:<32}"
        f"{item['pitchapi']:<42}"
        f"{item['tipo']:<16}"
        f"{item['cobertura']:>7.1f}%"
    )

print()

print("=" * 120)
print("DETALLE")
print("=" * 120)
print()

for item in MAPA:

    print(f"WINNING:       {item['winning']}")
    print(f"PITCHAPI:      {item['pitchapi']}")
    print(f"TIPO:          {item['tipo']}")
    print(f"COBERTURA:     {item['cobertura']:.1f}%")
    print(f"OBSERVACIÓN:   {item['observacion']}")
    print("-" * 120)

print()
print("=" * 120)
print("RESUMEN")
print("=" * 120)
print()

directas = sum(1 for x in MAPA if x["tipo"] == "DIRECTA")
derivables = sum(1 for x in MAPA if x["tipo"] == "DERIVABLE")
parciales = sum(1 for x in MAPA if x["tipo"] == "PARCIAL")
no_disponibles = sum(1 for x in MAPA if x["tipo"] == "NO DISPONIBLE")

print(f"Correspondencias DIRECTAS:      {directas}")
print(f"Correspondencias DERIVABLES:    {derivables}")
print(f"Correspondencias PARCIALES:     {parciales}")
print(f"NO DISPONIBLES:                 {no_disponibles}")

print()
print("=" * 120)
print("IMPORTANTE")
print("=" * 120)
print()
print("Este mapa NO calcula puntos Winning.")
print("Primero debemos validar las equivalencias semánticas.")
print("45% representa COBERTURA DEL DATO, no frecuencia de ocurrencia.")
print()
print("=" * 120)
print("FIN")
print("=" * 120)