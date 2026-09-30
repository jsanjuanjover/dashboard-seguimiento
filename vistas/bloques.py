import pandas as pd
import streamlit as st

from datos.calculos import DIAS_PARADO, LIMITE_WIP, TIPOS


def _fecha(valor):
    return "sin fecha" if pd.isna(valor) else f"{valor:%d/%m/%Y}"


def _dias(valor):
    if pd.isna(valor):
        return "sin fecha"
    return "hoy" if valor == 0 else f"hace {int(valor)} días"


def _avance(r):
    if r.pasos_total > 0:
        return f"{r.pasos_hechos}/{r.pasos_total} pasos"
    if pd.isna(r.total):
        return "sin datos"
    actual = 0 if pd.isna(r.actual) else r.actual
    return f"{actual:.0f}/{r.total:.0f} {r.unidad}"


def _metrica_wip(n):
    if n > LIMITE_WIP:
        delta, color, flecha = f"+{n - LIMITE_WIP} sobre el límite", "inverse", "auto"
    elif n == LIMITE_WIP:
        delta, color, flecha = "en el límite", "off", "off"
    else:
        delta, color, flecha = f"-{LIMITE_WIP - n} de margen", "inverse", "auto"
    st.metric("En curso", f"{n}/{LIMITE_WIP}", delta, delta_color=color, delta_arrow=flecha, border=True)


def fila_metricas(m):
    with st.container(horizontal=True):
        st.metric("Terminados este año", m["terminados_anio"], border=True)
        st.metric("Empezados este año", m["empezados_anio"], border=True)
        st.metric("Terminados este mes", m["terminados_mes"], border=True)
        st.metric("Empezados este mes", m["empezados_mes"], border=True)
        _metrica_wip(m["en_curso"])


def filtros(df):
    areas = sorted(df["area"].dropna().unique())
    with st.container(horizontal=True):
        tipos = st.pills("Tipo", TIPOS, selection_mode="multi", key="filtro_tipo")
        sel_areas = st.pills("Área", areas, selection_mode="multi", key="filtro_area")
    return tipos or [], sel_areas or []


def en_curso(df):
    with st.container(border=True):
        st.subheader("En curso")
        if df.empty:
            st.caption("Nada en curso.")
        for r in df.itertuples():
            texto = f"**{r.nombre}** · {_avance(r)} · {_dias(r.dias_sin_tocar)}"
            if r.parado:
                texto = f":material/warning: {texto} · :red[más de {DIAS_PARADO} días sin tocar]"
            st.progress(r.pct, text=texto)


def pausados(df):
    with st.container(border=True):
        st.subheader("Pausados")
        if df.empty:
            st.caption("Nada pausado.")
        for r in df.itertuples():
            st.markdown(f"- **{r.nombre}** · desde {_fecha(r.ult_act_efectiva)}")


def finalizados(por_tipo):
    with st.container(border=True):
        st.subheader("Últimos finalizados")
        pestanas = st.tabs([f"{tipo}s" for tipo in por_tipo])
        for pestana, df in zip(pestanas, por_tipo.values()):
            with pestana:
                if df.empty:
                    st.caption("Todavía ninguno.")
                lineas = [f"{i}. **{r.nombre}** · {_fecha(r.fin)}" for i, r in enumerate(df.itertuples(), start=1)]
                st.markdown("\n".join(lineas))


def desglose(por_tipo, por_area):
    with st.container(border=True):
        st.subheader("Desglose")
        st.markdown("**Por tipo**")
        st.dataframe(por_tipo)
        st.markdown("**Por área**")
        st.dataframe(por_area)
