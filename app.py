import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

from datos import calculos
from datos.carga import leer_hojas
from vistas import bloques

st.set_page_config(page_title="Seguimiento", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)


@st.fragment(run_every="1m")
def dashboard():
    hoy = pd.Timestamp.today().normalize()
    try:
        items, pasos = leer_hojas(conn)
    except Exception as e:
        st.error(f"No se pudo leer la hoja ({type(e).__name__}). ¿Está compartida con la cuenta de servicio?")
        return
    df = calculos.enriquecer(items, pasos, hoy)

    bloques.fila_metricas(calculos.metricas(df, hoy))
    tipos, areas = bloques.filtros(df)
    vista = calculos.filtrar(df, tipos, areas)

    izquierda, derecha = st.columns([3, 2])
    with izquierda:
        bloques.en_curso(calculos.en_curso(vista))
    with derecha:
        bloques.pausados(calculos.pausados(vista))
        bloques.finalizados(calculos.finalizados_por_tipo(vista))
        bloques.desglose(calculos.desglose(vista, "tipo"), calculos.desglose(vista, "area"))


st.title("Seguimiento")
dashboard()
