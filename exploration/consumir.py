import os

import requests
from dotenv import load_dotenv


load_dotenv()


URL_LICITACIONES = (
    "https://api.mercadopublico.cl/"
    "servicios/v1/publico/licitaciones.json"
)

URL_ORDENES = (
    "https://api.mercadopublico.cl/"
    "servicios/v1/publico/ordenesdecompra.json"
)


def obtener_ticket():
    ticket = os.getenv("MERCADO_PUBLICO_TICKET")

    if not ticket:
        raise ValueError(
            "No se encontró la variable MERCADO_PUBLICO_TICKET"
        )

    return ticket


def consumir_api(url, parametros):
    ticket = obtener_ticket()

    params = parametros.copy()
    params["ticket"] = ticket

    try:
        respuesta = requests.get(
            url,
            params=params,
            timeout=30
        )

        if respuesta.status_code == 200:
            return respuesta.json()

        print(
            f"Error HTTP {respuesta.status_code}: "
            f"{respuesta.text}"
        )

        return None

    except requests.exceptions.Timeout:
        print("La petición excedió el tiempo máximo de espera.")
        return None

    except requests.exceptions.RequestException as error:
        print(f"Error realizando la petición: {error}")
        return None


def obtener_licitaciones_por_fecha(fecha):
    return consumir_api(
        URL_LICITACIONES,
        {"fecha": fecha}
    )


def obtener_licitacion_por_codigo(codigo):
    return consumir_api(
        URL_LICITACIONES,
        {"codigo": codigo}
    )


def obtener_ordenes_por_fecha(fecha):
    return consumir_api(
        URL_ORDENES,
        {"fecha": fecha}
    )


def obtener_orden_por_codigo(codigo):
    return consumir_api(
        URL_ORDENES,
        {"codigo": codigo}
    )