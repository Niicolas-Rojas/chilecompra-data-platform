from collections import Counter

from consumir import (
    obtener_ordenes_por_fecha,
    obtener_orden_por_codigo,
    obtener_licitacion_por_codigo,
)


FECHA_PRUEBA = "20082026"


def buscar_primer_codigo_por_estado(
    listado,
    estados_buscados
):
    encontrados = {}

    for orden in listado:
        codigo_estado = orden["CodigoEstado"]

        if (
            codigo_estado in estados_buscados
            and codigo_estado not in encontrados
        ):
            encontrados[codigo_estado] = orden["Codigo"]

        if len(encontrados) == len(estados_buscados):
            break

    return encontrados


def main():
    # --------------------------------------------------
    # Consulta diaria
    # --------------------------------------------------

    datos = obtener_ordenes_por_fecha(FECHA_PRUEBA)

    if datos is None:
        return

    print("Cantidad OC:", datos["Cantidad"])

    # --------------------------------------------------
    # Distribución por estado
    # --------------------------------------------------

    conteo_estados = Counter(
        orden["CodigoEstado"]
        for orden in datos["Listado"]
    )

    print("\nCantidad por estado:")

    for estado, cantidad in sorted(conteo_estados.items()):
        print(f"{estado}: {cantidad}")

    # --------------------------------------------------
    # Obtener un ejemplo de cada estado
    # --------------------------------------------------

    estados_buscados = {4, 5, 6, 9, 12}

    codigos = buscar_primer_codigo_por_estado(
        datos["Listado"],
        estados_buscados
    )

    print("\nEstados encontrados:")

    for codigo_estado, codigo in sorted(codigos.items()):

        detalle = obtener_orden_por_codigo(codigo)

        if detalle is None or detalle["Cantidad"] == 0:
            continue

        orden = detalle["Listado"][0]

        print(
            f'{orden["CodigoEstado"]} -> '
            f'{orden["Estado"]} '
            f'({orden["Codigo"]})'
        )

    # --------------------------------------------------
    # Explorar una OC concreta
    # --------------------------------------------------

    print("\nDetalle de una OC:")

    datos_oc = obtener_orden_por_codigo(
        "1002-379-SE26"
    )

    if datos_oc is None:
        return

    orden = datos_oc["Listado"][0]

    print("Código:", orden["Codigo"])
    print("Estado:", orden["Estado"])
    print("Código licitación:", orden["CodigoLicitacion"])
    print("Total neto:", orden["TotalNeto"])
    print("Total:", orden["Total"])
    print(
        "Comprador:",
        orden["Comprador"]["NombreOrganismo"]
    )
    print(
        "Proveedor:",
        orden["Proveedor"]["Nombre"]
    )
    print(
        "Cantidad items:",
        orden["Items"]["Cantidad"]
    )

    # --------------------------------------------------
    # Validar relación OC -> Licitación
    # --------------------------------------------------

    codigo_licitacion = orden["CodigoLicitacion"]

    if codigo_licitacion:
        datos_licitacion = obtener_licitacion_por_codigo(
            codigo_licitacion
        )

        if (
            datos_licitacion is not None
            and datos_licitacion["Cantidad"] > 0
        ):
            licitacion = datos_licitacion["Listado"][0]

            print("\nLicitación relacionada:")
            print(
                "Código:",
                licitacion["CodigoExterno"]
            )
            print(
                "Nombre:",
                licitacion["Nombre"]
            )
            print(
                "Estado:",
                licitacion["Estado"]
            )


if __name__ == "__main__":
    main()