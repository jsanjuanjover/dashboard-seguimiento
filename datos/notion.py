import pandas as pd
from notion_client import Client
from notion_client.helpers import collect_paginated_api

COLUMNAS = ["id", "tarea", "estado", "fecha", "prioridad", "proyecto", "notas", "realizada", "editada"]


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
            "id": p["id"],
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


def _fuente(cliente, database_id):
    return cliente.databases.retrieve(database_id=database_id)["data_sources"][0]["id"]


def leer_tareas(token, database_id):
    cliente = Client(auth=token)
    return tipar_tareas(collect_paginated_api(cliente.data_sources.query, data_source_id=_fuente(cliente, database_id)))


def propiedades_estado(hecha, hoy):
    """Propiedades que se envían a Notion al marcar (Hecha, con fecha de hoy) o desmarcar una tarea."""
    if hecha:
        return {"Estado": {"status": {"name": "Hecha"}}, "Fecha realizada": {"date": {"start": f"{hoy:%Y-%m-%d}"}}}
    return {"Estado": {"status": {"name": "Pendiente"}}, "Fecha realizada": {"date": None}}


def cambiar_estado(token, page_id, hecha, hoy):
    Client(auth=token).pages.update(page_id=page_id, properties=propiedades_estado(hecha, hoy))


def propiedades_nueva_tarea(tarea, fecha, proyecto=None, prioridad=None):
    """Propiedades de una tarea nueva: Pendiente, con fecha límite y, si se dan, proyecto y prioridad."""
    props = {
        "Tarea": {"title": [{"text": {"content": tarea.strip()}}]},
        "Estado": {"status": {"name": "Pendiente"}},
        "Fecha límite": {"date": {"start": f"{fecha:%Y-%m-%d}"}},
    }
    if proyecto:
        props["Proyecto"] = {"select": {"name": proyecto}}
    if prioridad:
        props["Prioridad"] = {"select": {"name": prioridad}}
    return props


def crear_tarea(token, database_id, tarea, fecha, proyecto=None, prioridad=None):
    cliente = Client(auth=token)
    cliente.pages.create(parent={"data_source_id": _fuente(cliente, database_id)},
                         properties=propiedades_nueva_tarea(tarea, fecha, proyecto, prioridad))


def enviar_a_papelera(token, page_id):
    """Envía la tarea a la papelera de Notion (se puede recuperar desde allí)."""
    Client(auth=token).pages.update(page_id=page_id, in_trash=True)
