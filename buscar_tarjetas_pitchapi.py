import json
from pathlib import Path

CARPETA = Path("datos/pitchapi")

terminos = [
    "yellow",
    "red card",
    "redcard",
    "yellow card",
    "yellowcard",
    "card",
    "booking",
    "bookings",
    "discipline",
    "disciplinary",
    "caution",
    "second yellow",
    "straight red",
    "dismissal",
    "sent off",
    "sent_off",
    "red_card",
    "yellow_card",
    "cards",
]

encontrados = {}

def recorrer(obj, ruta="root"):
    """
    Recorre recursivamente cualquier JSON y devuelve
    todos los campos cuyo nombre o contenido pueda estar
    relacionado con tarjetas.
    """

    if isinstance(obj, dict):

        for clave, valor in obj.items():

            texto_clave = str(clave).lower()

            if any(termino in texto_clave for termino in terminos):

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

            # También buscamos en valores de texto
            if isinstance(valor, str):

                texto = valor.lower()

                if any(termino in texto for termino in terminos):

                    identificador = (
                        ruta,
                        str(clave),
                        valor
                    )

                    if identificador not in encontrados:
                        encontrados[identificador] = {
                            "ruta": ruta,
                            "campo": clave,
                            "valor": valor
                        }

            recorrer(valor, f"{ruta}.{clave}")

    elif isinstance(obj, list):

        for i, elemento in enumerate(obj):
            recorrer(elemento, f"{ruta}[{i}]")


archivos = sorted(CARPETA.glob("*.json"))

print()
print("=" * 110)
print("BÚSQUEDA GLOBAL DE TARJETAS — PITCHAPI")
print("=" * 110)
print()

print(f"Archivos analizados: {len(archivos)}")
print()

archivos_con_resultados = set()

for archivo in archivos:

    try:
        data = json.loads(
            archivo.read_text(encoding="utf-8")
        )
    except Exception as e:
        continue

    encontrados_antes = len(encontrados)

    recorrer(data, "root")

    if len(encontrados) > encontrados_antes:
        archivos_con_resultados.add(archivo.name)


print(f"Archivos con posibles coincidencias: {len(archivos_con_resultados)}")
print()

for (ruta, campo, *resto), resultado in encontrados.items():

    valor = resultado["valor"]

    print(f"Campo : {campo}")
    print(f"Ruta  : {ruta}")
    print(f"Valor : {valor}")
    print("-" * 110)

print()
print(f"Coincidencias encontradas: {len(encontrados)}")