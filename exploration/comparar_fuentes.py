from pathlib import Path

import pandas as pd

from consumir import obtener_orden_por_codigo


RUTA_PROYECTO = Path(__file__).resolve().parents[1]
RUTA_CSV = RUTA_PROYECTO / "data"/"2026-1.csv"

CANTIDAD_OC_PRUEBA = 10


def normalizar_id(valor):
    if pd.isna(valor):
        return None

    return str(valor).strip()


def comparar_oc(oc_csv, oc_api):
    primera_fila = oc_csv.iloc[0]

    comparaciones = {
        "Codigo OC": (
            normalizar_id(primera_fila["Codigo"]),
            normalizar_id(oc_api["Codigo"]),
        ),
        "Codigo licitacion": (
            normalizar_id(primera_fila["CodigoLicitacion"]),
            normalizar_id(oc_api["CodigoLicitacion"]),
        ),
        "Comprador": (
            normalizar_id(primera_fila["CodigoOrganismoPublico"]),
            normalizar_id(
                oc_api["Comprador"]["CodigoOrganismo"]
            ),
        ),
        "Proveedor": (
            normalizar_id(primera_fila["CodigoProveedor"]),
            normalizar_id(
                oc_api["Proveedor"]["Codigo"]
            ),
        ),
        "Cantidad items": (
            len(oc_csv),
            oc_api["Items"]["Cantidad"],
        ),
    }

    for campo, (valor_csv, valor_api) in comparaciones.items():
        coincide = valor_csv == valor_api

        print(
            f"{campo}: "
            f"CSV={valor_csv} | "
            f"API={valor_api} | "
            f"Coincide={coincide}"
        )

    # Campos que pueden cambiar con el tiempo.
    print(
        f"Estado: "
        f"CSV={primera_fila['Estado']} | "
        f"API={oc_api['Estado']}"
    )

    print(
        f"Total: "
        f"CSV={primera_fila['MontoTotalOC']} | "
        f"API={oc_api['Total']}"
    )


def main():
    df = pd.read_csv(
        RUTA_CSV,
        sep=";",
        encoding="latin1",
        decimal=",",
        low_memory=False,
    )

    codigos = (
        df["Codigo"]
        .dropna()
        .drop_duplicates()
        .head(CANTIDAD_OC_PRUEBA)
        .tolist()
    )

    for codigo in codigos:
        print("\n" + "=" * 70)
        print(f"COMPARANDO OC: {codigo}")
        print("=" * 70)

        oc_csv = df[df["Codigo"] == codigo]

        datos_api = obtener_orden_por_codigo(codigo)

        if datos_api is None:
            print("No fue posible consultar la API.")
            continue

        if datos_api["Cantidad"] == 0:
            print("La OC no existe actualmente en la API.")
            continue

        oc_api = datos_api["Listado"][0]

        comparar_oc(
            oc_csv,
            oc_api,
        )
    # ---------------------------------------------------------
    # Comparación específica de items
    # ---------------------------------------------------------

    codigo_items = "2404-54-SE26"

    print("\n" + "=" * 70)
    print(f"COMPARANDO ITEMS DE OC: {codigo_items}")
    print("=" * 70)

    oc_csv = df[df["Codigo"] == codigo_items]

    datos_api = obtener_orden_por_codigo(codigo_items)

    if datos_api is None or datos_api["Cantidad"] == 0:
        print("No fue posible obtener la OC desde la API.")
        return

    oc_api = datos_api["Listado"][0]
    items_api = oc_api["Items"]["Listado"]

    print("\n=== ITEMS CSV ===")

    columnas_csv = [
        "IDItem",
        "codigoProductoONU",
        "cantidad",
        "precioNeto",
    ]

    print(
        oc_csv[columnas_csv]
        .head(10)
        .to_string(index=False)
    )

    print("\n=== ITEMS API ===")

    for item in items_api[:10]:
        print(
            "Correlativo:", item["Correlativo"],
            "| CodigoProducto:", item["CodigoProducto"],
            "| Cantidad:", item["Cantidad"],
            "| PrecioNeto:", item["PrecioNeto"],
        )
if __name__ == "__main__":
    main()