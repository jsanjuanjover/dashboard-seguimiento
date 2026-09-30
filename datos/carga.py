import pandas as pd

FORMATO_FECHA = "%d/%m/%Y"


def _fechas(serie):
    return pd.to_datetime(serie, format=FORMATO_FECHA, errors="coerce")


def tipar_items(df):
    df = df.dropna(subset=["nombre"]).copy()
    for col in ["inicio", "fin", "ult_act"]:
        df[col] = _fechas(df[col])
    for col in ["actual", "total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def tipar_pasos(df):
    df = df.dropna(subset=["proyecto", "paso"]).copy()
    df["fecha_hecho"] = _fechas(df["fecha_hecho"])
    df["orden"] = pd.to_numeric(df["orden"], errors="coerce")
    return df


def leer_hojas(conn, ttl):
    items = tipar_items(conn.read(worksheet="Items", ttl=ttl))
    pasos = tipar_pasos(conn.read(worksheet="Pasos", ttl=ttl))
    return items, pasos
