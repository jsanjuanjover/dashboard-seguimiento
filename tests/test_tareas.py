import pandas as pd

from datos.calculos import calendario_tareas, fin_semana_siguiente, tareas_para_hoy, tareas_por_grupo
from streamlit.testing.v1 import AppTest

from datos import notion
from datos.notion import propiedades_estado, propiedades_nueva_tarea, tipar_tareas

HOY = pd.Timestamp("2026-11-04")  # miércoles


def pagina(tarea="T", estado="Pendiente", fecha=None, prioridad=None, proyecto=None, realizada=None,
           editada="2026-11-01"):
    def opcion(tipo, valor):
        return {"type": tipo, tipo: {"name": valor} if valor else None}

    def texto(tipo, valor):
        return {"type": tipo, tipo: [{"plain_text": valor}] if valor else []}

    return {
        "id": f"id-{tarea}",
        "last_edited_time": f"{editada}T10:00:00.000Z",
        "properties": {
            "Tarea": texto("title", tarea),
            "Estado": opcion("status", estado),
            "Fecha límite": {"type": "date", "date": {"start": fecha, "end": None} if fecha else None},
            "Prioridad": opcion("select", prioridad),
            "Proyecto": opcion("select", proyecto),
            "Notas": texto("rich_text", None),
            "Fecha realizada": {"type": "date", "date": {"start": realizada, "end": None} if realizada else None},
        },
    }


def tareas(*paginas):
    return tipar_tareas(list(paginas))


def test_tipar_tolera_propiedades_vacias_y_fechas_con_hora():
    t = tareas(pagina("a"), pagina("b", fecha="2026-11-04T09:30:00.000+01:00", prioridad="Alta"), pagina(None))
    assert list(t["tarea"]) == ["a", "b"]
    assert pd.isna(t["fecha"].iloc[0]) and pd.isna(t["prioridad"].iloc[0])
    assert t["fecha"].iloc[1] == HOY
    assert t["editada"].iloc[0] == pd.Timestamp("2026-11-01")


def test_tipar_sin_paginas_no_rompe():
    assert tareas().empty


def test_para_hoy_incluye_atrasadas_y_sin_fecha_y_excluye_hechas_y_futuras():
    t = tareas(
        pagina("hoy", fecha="2026-11-04"),
        pagina("atrasada", fecha="2026-10-20", estado="En curso"),
        pagina("sin_fecha"),
        pagina("manana", fecha="2026-11-05"),
        pagina("hecha", fecha="2026-11-04", estado="Hecha"),
    )
    assert list(tareas_para_hoy(t, HOY)["tarea"]) == ["atrasada", "hoy", "sin_fecha"]


def test_para_hoy_misma_fecha_ordena_por_prioridad():
    t = tareas(
        pagina("baja", fecha="2026-11-04", prioridad="Baja"),
        pagina("ninguna", fecha="2026-11-04"),
        pagina("alta", fecha="2026-11-04", prioridad="Alta"),
    )
    assert list(tareas_para_hoy(t, HOY)["tarea"]) == ["alta", "baja", "ninguna"]


def test_fin_semana_siguiente_es_el_domingo_de_la_proxima_semana():
    assert fin_semana_siguiente(HOY) == pd.Timestamp("2026-11-15")
    assert fin_semana_siguiente(pd.Timestamp("2026-11-02")) == pd.Timestamp("2026-11-15")  # lunes
    assert fin_semana_siguiente(pd.Timestamp("2026-11-08")) == pd.Timestamp("2026-11-15")  # domingo


def test_futuras_solo_hasta_el_domingo_de_la_semana_que_viene():
    t = tareas(
        pagina("viernes", fecha="2026-11-06"),
        pagina("domingo_prox", fecha="2026-11-15"),
        pagina("lunes_siguiente", fecha="2026-11-16"),
        pagina("hecha_futura", fecha="2026-11-10", estado="Hecha"),
    )
    assert list(tareas_por_grupo(t, HOY)["Futuras"]["tarea"]) == ["viernes", "domingo_prox"]


def test_calendario_dos_semanas_de_lunes_a_domingo_con_hoy_recogiendo_atrasadas():
    t = tareas(
        pagina("hoy", fecha="2026-11-04"),
        pagina("atrasada", fecha="2026-11-02"),
        pagina("sin_fecha"),
        pagina("viernes", fecha="2026-11-06"),
        pagina("domingo_prox", fecha="2026-11-15"),
        pagina("fuera", fecha="2026-11-16"),
        pagina("hecha", fecha="2026-11-06", estado="Hecha"),
    )
    cal = calendario_tareas(tareas_por_grupo(t, HOY), HOY)
    dias = list(cal)
    assert len(dias) == 14 and dias[0] == pd.Timestamp("2026-11-02") and dias[-1] == pd.Timestamp("2026-11-15")
    assert list(cal[HOY]["tarea"]) == ["atrasada", "hoy", "sin_fecha"]
    assert cal[pd.Timestamp("2026-11-02")].empty
    assert list(cal[pd.Timestamp("2026-11-06")]["tarea"]) == ["viernes"]
    assert list(cal[pd.Timestamp("2026-11-15")]["tarea"]) == ["domingo_prox"]


def test_hechas_usan_fecha_realizada_antes_que_la_edicion():
    t = tareas(
        pagina("realizada_vieja", estado="Hecha", realizada="2026-09-01", editada="2026-11-03"),
        pagina("realizada_reciente", estado="Hecha", realizada="2026-11-02", editada="2026-11-01"),
        pagina("sin_realizada", estado="Hecha", editada="2026-11-03"),
    )
    assert list(tareas_por_grupo(t, HOY)["Hechas"]["tarea"]) == ["sin_realizada", "realizada_reciente"]


def test_hechas_sin_fecha_realizada_ultimos_30_dias_por_edicion():
    t = tareas(
        pagina("reciente", estado="Hecha", editada="2026-11-03"),
        pagina("limite", estado="Hecha", editada="2026-10-05"),
        pagina("vieja", estado="Hecha", editada="2026-10-04"),
        pagina("pendiente", editada="2026-11-03"),
    )
    assert list(tareas_por_grupo(t, HOY)["Hechas"]["tarea"]) == ["reciente", "limite"]


def test_tipar_guarda_el_id_de_la_pagina():
    assert list(tareas(pagina("a"), pagina("b"))["id"]) == ["id-a", "id-b"]


def test_marcar_hecha_pone_estado_y_fecha_realizada_de_hoy():
    assert propiedades_estado(True, HOY) == {
        "Estado": {"status": {"name": "Hecha"}},
        "Fecha realizada": {"date": {"start": "2026-11-04"}},
    }


def test_desmarcar_vuelve_a_pendiente_y_borra_fecha_realizada():
    assert propiedades_estado(False, HOY) == {
        "Estado": {"status": {"name": "Pendiente"}},
        "Fecha realizada": {"date": None},
    }


def test_cambiar_estado_actualiza_la_pagina_indicada(monkeypatch):
    llamadas = []

    class Paginas:
        def update(self, **kwargs):
            llamadas.append(kwargs)

    class ClienteFalso:
        def __init__(self, auth):
            self.auth, self.pages = auth, Paginas()

    monkeypatch.setattr(notion, "Client", ClienteFalso)
    notion.cambiar_estado("tok", "id-a", True, HOY)
    assert llamadas == [{"page_id": "id-a", "properties": propiedades_estado(True, HOY)}]


def _vista_casillas(filas, hoy):
    import streamlit as st

    from datos.notion import tipar_tareas
    from vistas import bloques

    def al_marcar(page_id, hecha, clave):
        st.session_state.setdefault("marcadas", []).append((page_id, hecha, clave))

    df = tipar_tareas(filas)
    bloques.tareas_para_hoy(df[df["estado"].ne("Hecha")], hoy, al_marcar)


def test_casilla_pendiente_al_marcarla_avisa_con_hecha_true():
    at = AppTest.from_function(_vista_casillas, args=([pagina("a"), pagina("b")], HOY)).run()
    assert [c.value for c in at.checkbox] == [False, False]
    at.checkbox(key="tarea_pendiente_id-b").check().run()
    assert at.session_state["marcadas"] == [("id-b", True, "tarea_pendiente_id-b")]


def test_casilla_hecha_al_desmarcarla_avisa_con_hecha_false():
    def vista(filas, hoy):
        import streamlit as st

        from datos.notion import tipar_tareas
        from vistas import bloques

        def al_marcar(page_id, hecha, clave):
            st.session_state.setdefault("marcadas", []).append((page_id, hecha, clave))

        cal = {hoy: tipar_tareas([])}
        bloques.tareas(cal, tipar_tareas(filas), hoy, al_marcar)

    filas = [pagina("hecha", estado="Hecha", realizada="2026-11-03")]
    at = AppTest.from_function(vista, args=(filas, HOY)).run()
    assert [c.value for c in at.checkbox] == [True]
    at.checkbox(key="tarea_hecha_id-hecha").uncheck().run()
    assert at.session_state["marcadas"] == [("id-hecha", False, "tarea_hecha_id-hecha")]


def test_nueva_tarea_pendiente_con_fecha_y_sin_opcionales():
    assert propiedades_nueva_tarea("  Llamar al banco ", HOY) == {
        "Tarea": {"title": [{"text": {"content": "Llamar al banco"}}]},
        "Estado": {"status": {"name": "Pendiente"}},
        "Fecha límite": {"date": {"start": "2026-11-04"}},
    }


def test_nueva_tarea_con_proyecto_y_prioridad():
    props = propiedades_nueva_tarea("Revisar", pd.Timestamp("2026-11-20"), "TFM", "Alta")
    assert props["Fecha límite"] == {"date": {"start": "2026-11-20"}}
    assert props["Proyecto"] == {"select": {"name": "TFM"}}
    assert props["Prioridad"] == {"select": {"name": "Alta"}}


def test_crear_tarea_la_crea_en_la_fuente_de_datos_de_la_base(monkeypatch):
    creadas = []

    class ClienteFalso:
        def __init__(self, auth):
            self.databases = type("D", (), {"retrieve": lambda _, database_id: {"data_sources": [{"id": "ds-1"}]}})()
            self.pages = type("P", (), {"create": lambda _, **kw: creadas.append(kw)})()

    monkeypatch.setattr(notion, "Client", ClienteFalso)
    notion.crear_tarea("tok", "db-1", "Nueva", HOY, proyecto="Otros")
    assert creadas == [{"parent": {"data_source_id": "ds-1"},
                        "properties": propiedades_nueva_tarea("Nueva", HOY, "Otros")}]


def _vista_inbox(hoy):
    import streamlit as st

    from vistas import bloques

    def al_crear():
        estado = st.session_state
        estado["enviado"] = (estado["inbox_tarea"], estado["inbox_fecha"], estado["inbox_proyecto"],
                             estado["inbox_prioridad"])

    bloques.inbox(hoy, al_crear)


def test_inbox_fecha_hoy_por_defecto_y_sin_dias_pasados():
    at = AppTest.from_function(_vista_inbox, args=(HOY.date(),)).run()
    assert at.date_input(key="inbox_fecha").value == HOY.date()
    assert at.date_input(key="inbox_fecha").min == HOY.date()
    assert at.selectbox(key="inbox_proyecto").value is None


def test_inbox_envia_lo_escrito_con_fecha_futura():
    at = AppTest.from_function(_vista_inbox, args=(HOY.date(),)).run()
    at.text_input(key="inbox_tarea").input("Preparar clase")
    at.date_input(key="inbox_fecha").set_value(pd.Timestamp("2026-11-12").date())
    at.selectbox(key="inbox_proyecto").select("Docencia")
    at.button[0].click().run()
    assert at.session_state["enviado"] == ("Preparar clase", pd.Timestamp("2026-11-12").date(), "Docencia", None)
