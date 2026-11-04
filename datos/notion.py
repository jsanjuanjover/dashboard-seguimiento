import pandas as pd
from notion_client import Client
from notion_client.helpers import collect_paginated_api

COLUMNAS = ["tarea", "estado", "fecha", "prioridad", "proyecto", "notas", "realizada", "editada"]


def _texto(prop):
    return "".join(t["plain_text"] for t in prop.get(prop["type"]) or []) or None


def _opcion(prop):
    valor = prop.get(prop["type"])
    return valor["name"] if valor else None


def _fecha(prop):
    valor = prop.get("date")
    return valor["start"][:10] if valor else None


def tipar_tareas(paginas):
    """Convierte las páginas de la API en filas; tolera propiedades vacías."""
    filas = []
    for p in paginas:
        props = p["properties"]
        filas.append({
            "tarea": _texto(props["Tarea"]),
            "estado": _opcion(props["Estado"]),
            "fecha": _fecha(props["Fecha límite"]),
            "prioridad": _opcion(props["Prioridad"]),
            "proyecto": _opcion(props["Proyecto"]),
            "notas": _texto(props["Notas"]),
            "realizada": _fecha(props["Fecha realizada"]),
            "editada": p["last_edited_time"][:10],
        })
    df = pd.DataFrame(filas, columns=COLUMNAS).dropna(subset=["tarea"])
    for col in ["fecha", "realizada", "editada"]:
        df[col] = pd.to_datetime(df[col], format="%Y-%m-%d", errors="coerce")
    return df


def leer_tareas(token, database_id):
    cliente = Client(auth=token)
    fuente = cliente.databases.retrieve(database_id=database_id)["data_sources"][0]["id"]
    return tipar_tareas(collect_paginated_api(cliente.data_sources.query, data_source_id=fuente))
