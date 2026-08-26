from pathlib import Path

import pandas as pd


RUTA_PROYECTO = Path(__file__).resolve().parents[1]

RUTA_CSV = RUTA_PROYECTO /"data"/ "2026-1.csv"


def main():
    df = pd.read_csv(
        RUTA_CSV,
        sep=";",
        encoding="latin1",
        decimal=",",
        low_memory=False
    )

    print("Filas CSV:", len(df))
    print("OC únicas:", df["Codigo"].nunique())
    print("Items únicos:", df["IDItem"].nunique())

    print("\nRango de fechas:")

    columnas_fecha = [
        "FechaCreacion",
        "FechaEnvio",
        "fechaUltimaModificacion",
        "FechaAceptacion",
    ]

    for columna in columnas_fecha:

        fechas = pd.to_datetime(
            df[columna],
            errors="coerce"
        )

        print(
            f"{columna}: "
            f"MIN={fechas.min()} "
            f"MAX={fechas.max()}"
        )

    print("\nOC con más items:")

    print(
        df.groupby("Codigo")
        .size()
        .sort_values(ascending=False)
        .head(10)
    )
    print("\nNulos en campos importantes:")

    columnas_importantes = [
        "Codigo",
        "IDItem",
        "CodigoLicitacion",
        "CodigoProveedor",
        "CodigoOrganismoPublico",
    ]

    total_filas = len(df)

    for columna in columnas_importantes:
        cantidad_nulos = df[columna].isna().sum()
        porcentaje = (cantidad_nulos / total_filas) * 100

        print(
            f"{columna}: "
            f"{cantidad_nulos} nulos "
            f"({porcentaje:.2f}%)"
        )

    print("\nDuplicados:")

    print(
        "Codigo duplicado:",
        df["Codigo"].duplicated().sum()
    )

    print(
        "IDItem duplicado:",
        df["IDItem"].duplicated().sum()
    )
    

if __name__ == "__main__":
    main()