import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

terminos = [
    "yellow",
    "red",
    "card",
    "booking",
    "caution",
    "disciplin",
    "dismiss",
    "sent_off",
    "sentoff",
    "second_yellow",
    "yellow_card",
    "red_card",
    "yellowcard",
    "redcard",
]

encontrados = {}


def recorrer(obj, ruta="root"):

    if isinstance(obj, dict):

        for clave, valor in obj.items():

            clave_texto = str(clave).lower()

            # SOLAMENTE analizamos el nombre del campo.
            # No analizamos nombres/valores de jugadores.
            if any(termino in clave_texto for termino in terminos):

                identificador = (
                    ruta,
                    str(clave)
                )

                if identificador not in encontrados:

                    encontrados[identificador] = {
                        "ruta": ruta,
                        "campo": clave,
                        "valor": valor
                    }

            recorrer(
                valor,
                f"{ruta}.{clave}"
            )

    elif isinstance(obj, list):

        for i, elemento in enumerate(obj):

            recorrer(
                elemento,
                f"{ruta}[{i}]"
            )


archivos = sorted(CARPETA.glob("*.json"))

print()
print("=" * 110)
print("BÚSQUEDA DE CAMPOS DE TARJETAS — PITCHAPI")
print("=" * 110)
print()

print(f"Archivos analizados: {len(archivos)}")
print()

for archivo in archivos:

    try:
        data = json.loads(
            archivo.read_text(encoding="utf-8")
        )

    except Exception:
        continue

    antes = len(encontrados)

    recorrer(data, "root")

    if len(encontrados) > antes:
        pass


for (ruta, campo), resultado in sorted(encontrados.items()):

    valor = resultado["valor"]

    # Evitamos imprimir objetos gigantes.
    if isinstance(valor, (dict, list)):
        valor_mostrar = (
            f"<{type(valor).__name__}, "
            f"{len(valor)} elementos>"
        )
    else:
        valor_mostrar = value = valor

    print(f"Campo : {campo}")
    print(f"Ruta  : {ruta}")
    print(f"Valor : {valor_mostrar}")
    print("-" * 110)


print()
print(f"Campos encontrados: {len(encontrados)}")