import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

from datos import calculos
from datos.carga import leer_hojas
from datos.notion import cambiar_estado, leer_tareas
from vistas import bloques

st.set_page_config(page_title="Seguimiento", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)


INTERVALO = "1h"


def ahora():
    return pd.Timestamp.now(tz="Europe/Madrid").tz_localize(None)


@st.cache_data(ttl=INTERVALO)
def cargar():
    items, pasos = leer_hojas(conn, ttl=0)
    return items, pasos, ahora()


@st.cache_data(ttl=INTERVALO)
def cargar_tareas():
    return leer_tareas(st.secrets["notion"]["token"], st.secrets["notion"]["database_id"])


def marcar_tarea(page_id, hecha, clave):
    """Escribe en Notion el cambio de una casilla; si falla, la casilla vuelve a como estaba."""
    try:
        cambiar_estado(st.secrets["notion"]["token"], page_id, hecha, ahora().normalize())
        cargar_tareas.clear()
    except Exception as e:
        del st.session_state[clave]
        st.session_state["error_marcar"] = f"No se pudo guardar el cambio en Notion: {type(e).__name__}: {e}"


def proyectos(df, pasos, hoy):
    bloques.fila_metricas(calculos.metricas(df, hoy))
    tipos, areas = bloques.filtros(df)
    vista = calculos.filtrar(df, tipos, areas)

    izquierda, derecha = st.columns([3, 2])
    with izquierda:
        en_curso = calculos.en_curso(vista)
        detalles = {r.nombre: calculos.detalle(pasos, r.nombre, hoy) for r in calculos.en_progreso(en_curso).itertuples()}
        bloques.en_curso(en_curso, detalles)
        bloques.no_empezados(calculos.no_empezados(vista))
    with derecha:
        bloques.pausados(calculos.pausados(vista))
        bloques.finalizados(calculos.finalizados_por_tipo(vista))
        bloques.desglose(calculos.desglose(vista, "tipo"), calculos.desglose(vista, "area"))


@st.fragment(run_every=INTERVALO)
def dashboard():
    hoy = ahora().normalize()
    with st.container(horizontal=True, vertical_alignment="center"):
        if st.button("Actualizar", icon=":material/refresh:"):
            cargar.clear()
            cargar_tareas.clear()
        hueco_hora = st.empty()
    try:
        items, pasos, leido = cargar()
        hueco_hora.caption(f"Actualizado a las {leido:%H:%M}")
    except Exception as e:
        st.error(
            f"No se pudo leer la hoja: {type(e).__name__}: {e}. "
            "Si es 'permission denied' o 'not found', comprueba que está compartida con la cuenta de servicio."
        )
        return
    df = calculos.enriquecer(items, pasos, hoy)
    try:
        tareas, error_tareas = cargar_tareas(), None
    except Exception as e:
        tareas, error_tareas = None, e

    if mensaje := st.session_state.pop("error_marcar", None):
        bloques.error_marcar(mensaje)

    general, pestana_tareas, pestana_proyectos = st.tabs(["General", "Tareas", "Proyectos"])
    with general:
        izquierda, derecha = st.columns([2, 3])
        with izquierda:
            if error_tareas:
                bloques.error_notion(error_tareas)
            else:
                bloques.tareas_para_hoy(calculos.tareas_para_hoy(tareas, hoy), hoy, marcar_tarea)
        with derecha:
            bloques.en_curso(calculos.en_curso(df), {})
    with pestana_tareas:
        if error_tareas:
            bloques.error_notion(error_tareas)
        else:
            grupos = calculos.tareas_por_grupo(tareas, hoy)
            bloques.tareas(calculos.calendario_tareas(grupos, hoy), grupos["Hechas"], hoy, marcar_tarea)
    with pestana_proyectos:
        proyectos(df, pasos, hoy)


st.title("Seguimiento")
dashboard()
