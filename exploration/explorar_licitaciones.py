from consumir import (
    obtener_licitaciones_por_fecha,
    obtener_licitacion_por_codigo,
)


FECHA_PRUEBA = "20082026"


def mostrar_tipos(diccionario):
    for clave, valor in diccionario.items():
        print(f"{clave}: {type(valor).__name__}")


def buscar_codigo_por_estado(listado, codigo_estado):
    for licitacion in listado:
        if licitacion["CodigoEstado"] == codigo_estado:
            return licitacion["CodigoExterno"]

    return None


def resumir_licitacion(datos):
    if datos is None or datos["Cantidad"] == 0:
        print("No se encontraron datos.")
        return

    licitacion = datos["Listado"][0]

    print("Código:", licitacion["CodigoExterno"])
    print("Código estado:", licitacion["CodigoEstado"])
    print("Estado:", licitacion["Estado"])

    adjudicacion = licitacion["Adjudicacion"]

    print(
        "Adjudicación general:",
        type(adjudicacion).__name__
    )

    items = licitacion["Items"]

    print("Cantidad items:", items["Cantidad"])

    if items["Cantidad"] > 0:
        primer_item = items["Listado"][0]

        print(
            "Adjudicación primer item:",
            type(primer_item["Adjudicacion"]).__name__
        )

    print("-" * 50)


def main():
    # --------------------------------------------------
    # Consulta resumida por fecha
    # --------------------------------------------------

    datos = obtener_licitaciones_por_fecha(FECHA_PRUEBA)

    if datos is None:
        return

    print("Cantidad licitaciones:", datos["Cantidad"])

    estados = {
        5: "Publicada",
        7: "Desierta",
        8: "Adjudicada",
    }

    codigos = {}

    for codigo_estado, nombre_estado in estados.items():
        codigo = buscar_codigo_por_estado(
            datos["Listado"],
            codigo_estado
        )

        codigos[codigo_estado] = codigo

        print(
            f"{nombre_estado} ({codigo_estado}): {codigo}"
        )

    print("\nComparación por estado\n")

    # --------------------------------------------------
    # Consulta detallada
    # --------------------------------------------------

    for codigo_estado, codigo in codigos.items():
        if codigo is None:
            continue

        detalle = obtener_licitacion_por_codigo(codigo)

        resumir_licitacion(detalle)


if __name__ == "__main__":
    main()