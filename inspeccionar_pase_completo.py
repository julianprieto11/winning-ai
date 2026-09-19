import json
import glob
from pprint import pprint

for archivo in glob.glob("datos/partidos/*.json"):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)

        encontrado = False

        def buscar(obj):
            global encontrado

            if isinstance(obj, dict):
                if "passEndCoordinates" in obj:
                    print("=" * 80)
                    print("ARCHIVO:", archivo)
                    print("OBJETO QUE CONTIENE passEndCoordinates:")
                    pprint(obj, sort_dicts=False, width=140)
                    return True

                for valor in obj.values():
                    if buscar(valor):
                        return True

            elif isinstance(obj, list):
                for elemento in obj:
                    if buscar(elemento):
                        return True

            return False

        if buscar(datos):
            break

    except Exception:
        pass