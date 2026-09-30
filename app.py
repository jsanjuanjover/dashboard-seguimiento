import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

from datos import calculos
from datos.carga import leer_hojas
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


@st.fragment(run_every=INTERVALO)
def dashboard():
    hoy = ahora().normalize()
    with st.container(horizontal=True, vertical_alignment="center"):
        if st.button("Actualizar", icon=":material/refresh:"):
            cargar.clear()
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

    bloques.fila_metricas(calculos.metricas(df, hoy))
    tipos, areas = bloques.filtros(df)
    vista = calculos.filtrar(df, tipos, areas)

    izquierda, derecha = st.columns([3, 2])
    with izquierda:
        en_curso = calculos.en_curso(vista)
        detalles = {r.nombre: calculos.detalle(pasos, r.nombre, hoy) for r in calculos.en_progreso(en_curso).itertuples()}
        bloques.en_curso(en_curso, detalles)
    with derecha:
        bloques.pausados(calculos.pausados(vista))
        bloques.finalizados(calculos.finalizados_por_tipo(vista))
        bloques.desglose(calculos.desglose(vista, "tipo"), calculos.desglose(vista, "area"))


st.title("Seguimiento")
dashboard()
