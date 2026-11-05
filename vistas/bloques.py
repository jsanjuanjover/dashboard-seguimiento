import pandas as pd
import streamlit as st

from datos.calculos import DIAS_HECHAS, DIAS_PARADO, LIMITE_WIP, PRIORIDADES, PROYECTOS, TIPOS


def _fecha(valor):
    return "sin fecha" if pd.isna(valor) else f"{valor:%d/%m/%Y}"


def _dias(valor):
    if pd.isna(valor):
        return "sin fecha"
    return "hoy" if valor == 0 else f"hace {int(valor)} días"


def _avance(r):
    if r.pasos_total > 0:
        return f"{r.pasos_hechos}/{r.pasos_total} pasos"
    if pd.isna(r.total) or r.total <= 0:
        return "sin datos"
    actual = 0 if pd.isna(r.actual) else r.actual
    unidad = "" if pd.isna(r.unidad) else f" {r.unidad}"
    return f"{actual:.0f}/{r.total:.0f}{unidad}"


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


def _barra(pct, texto):
    barra, cifra = st.columns([9, 1], vertical_alignment="bottom")
    barra.progress(pct, text=texto)
    cifra.markdown(f"**{int(pct * 100)} %**")


def _lista_en_curso(df):
    if df.empty:
        st.caption("Nada en curso.")
    for r in df.itertuples():
        avance = _avance(r) if pd.isna(r.siguiente_paso) else f"Siguiente: {r.siguiente_paso}"
        texto = f"**{r.nombre}** · {avance} · {_dias(r.dias_sin_tocar)}"
        if r.parado:
            texto = f":material/warning: {texto} · :red[más de {DIAS_PARADO} días sin tocar]"
        _barra(r.pct, texto)


def _detalle_item(r, d):
    _barra(r.pct, f"**{r.nombre}** · {_avance(r)}")
    if d["fases"].empty:
        st.caption("Este ítem no tiene pasos en la pestaña Pasos de la hoja.")
        return
    st.markdown("**Fases**")
    for f in d["fases"].itertuples():
        _barra(f.pct, f"{f.fase} · {f.hechos}/{f.total}")
    if d["siguiente"]:
        st.markdown(f"**Siguiente paso:** {d['siguiente']['paso']} ({d['siguiente']['fase']})")
    if not d["curva"].empty:
        st.markdown("**Pasos hechos por semana (acumulado)**")
        st.line_chart(d["curva"], height=200)


def en_curso(df, detalles):
    with st.container(border=True):
        st.subheader("En curso")
        if not detalles:
            _lista_en_curso(df)
            return
        elegido = st.selectbox("Detalle", ["Todos", *detalles], label_visibility="collapsed")
        if elegido == "Todos":
            _lista_en_curso(df)
        else:
            _detalle_item(next(df[df["nombre"].eq(elegido)].itertuples()), detalles[elegido])


def no_empezados(df):
    with st.container(border=True):
        st.subheader("No empezados")
        if df.empty:
            st.caption("Nada pendiente de empezar.")
        for r in df.itertuples():
            aviso = " · :orange[revisa `actual` y `total` en la hoja]" if r.sin_datos else ""
            st.markdown(f"- **{r.nombre}** · {_avance(r)}{aviso}")


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


def _linea_tarea(r, hoy):
    partes = [f"**{r.tarea}**"]
    partes += [v for v in (r.proyecto, r.prioridad) if not pd.isna(v)]
    if r.estado == "Hecha":
        partes.append(f"hecha el {_fecha(r.realizada)}")
    elif pd.isna(r.fecha):
        partes.append("sin fecha")
    elif r.fecha < hoy:
        partes.append(f":red[atrasada desde {_fecha(r.fecha)}]")
    else:
        partes.append(_fecha(r.fecha))
    return "- " + " · ".join(partes)


def _casillas_tareas(df, hoy, al_marcar, vacio):
    """Una casilla por tarea; al tocarla se llama a `al_marcar(id, hecha, clave)`."""
    if df.empty:
        st.caption(vacio)
    for r in df.itertuples():
        hecha = r.estado == "Hecha"
        clave = f"tarea_{'hecha' if hecha else 'pendiente'}_{r.id}"
        st.checkbox(_linea_tarea(r, hoy).removeprefix("- "), value=hecha, key=clave,
                    on_change=al_marcar, args=(r.id, not hecha, clave))


def tareas_para_hoy(df, hoy, al_marcar):
    with st.container(border=True):
        st.subheader("Tareas para hoy")
        _casillas_tareas(df, hoy, al_marcar, "Nada pendiente para hoy.")


DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def _tarea_en_dia(r, hoy):
    detalle = " · ".join(v for v in (r.proyecto, r.prioridad) if not pd.isna(v))
    if pd.isna(r.fecha):
        detalle = " · ".join(filter(None, [detalle, "sin fecha"]))
    elif r.fecha < hoy:
        detalle = " · ".join(filter(None, [detalle, f":red[atrasada {r.fecha:%d/%m}]"]))
    return f"**{r.tarea}**" + (f"  \n:gray[{detalle}]" if detalle else "")


def _dia(dia, df, hoy):
    titulo = f"{DIAS_SEMANA[dia.weekday()]} {dia:%d/%m}"
    st.markdown(f":blue-background[**{titulo} · hoy**]" if dia == hoy else f"**{titulo}**")
    if dia < hoy:
        return
    for r in df.itertuples():
        st.markdown(_tarea_en_dia(r, hoy))


def inbox(hoy, al_crear):
    """Formulario para crear una tarea; la fecha es hoy por defecto y no admite días pasados."""
    with st.form("inbox", border=True):
        st.subheader("Nueva Tarea")
        st.text_input("Tarea", key="inbox_tarea", placeholder="Qué hay que hacer")
        fecha, proyecto, prioridad = st.columns(3)
        fecha.date_input("Fecha límite", value=hoy, min_value=hoy, format="DD/MM/YYYY", key="inbox_fecha")
        proyecto.selectbox("Proyecto", PROYECTOS, index=None, placeholder="Sin proyecto", key="inbox_proyecto")
        prioridad.selectbox("Prioridad", PRIORIDADES, index=None, placeholder="Sin prioridad", key="inbox_prioridad")
        st.form_submit_button("Añadir tarea", icon=":material/add:", on_click=al_crear)


def tareas(calendario, hechas, hoy, al_marcar):
    with st.container(border=True):
        st.subheader("Esta semana y la siguiente")
        dias = list(calendario.items())
        for semana in (dias[:7], dias[7:]):
            for columna, (dia, df) in zip(st.columns(7, border=True), semana):
                with columna:
                    _dia(dia, df, hoy)
    with st.container(border=True):
        st.subheader(f"Hechas (últimos {DIAS_HECHAS} días)")
        st.caption("Desmarca una tarea para devolverla a Pendiente.")
        _casillas_tareas(hechas, hoy, al_marcar, "Ninguna.")


def error_marcar(mensaje):
    st.warning(mensaje, icon=":material/sync_problem:")


def aviso_inbox(tipo, mensaje):
    if tipo == "ok":
        st.success(mensaje, icon=":material/check:")
    else:
        st.warning(mensaje, icon=":material/sync_problem:")


def error_notion(e):
    st.error(f"No se pudieron leer las tareas de Notion: {type(e).__name__}: {e}. "
             "Comprueba el token y que la base de datos esté conectada a la integración.")


def desglose(por_tipo, por_area):
    with st.container(border=True):
        st.subheader("Desglose")
        st.markdown("**Por tipo**")
        st.dataframe(por_tipo)
        st.markdown("**Por área**")
        st.dataframe(por_area)
