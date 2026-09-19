import json
import glob

encontrados = 0

for archivo in glob.glob("datos/partidos/*.json"):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)

        texto = json.dumps(datos)

        if "passEndCoordinates" in texto:
            print("=" * 70)
            print("ARCHIVO:", archivo)

            def buscar(obj):
                global encontrados

                if isinstance(obj, dict):
                    for clave, valor in obj.items():
                        if clave == "passEndCoordinates":
                            print("EJEMPLO:")
                            print(valor)
                            encontrados += 1

                            if encontrados >= 10:
                                return True

                        if buscar(valor):
                            return True

                elif isinstance(obj, list):
                    for elemento in obj:
                        if buscar(elemento):
                            return True

                return False

            buscar(datos)

            if encontrados >= 10:
                break

    except Exception:
        pass

print()
print("Ejemplos encontrados:", encontrados)