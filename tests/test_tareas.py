import pandas as pd

from datos.calculos import calendario_tareas, fin_semana_siguiente, tareas_para_hoy, tareas_por_grupo
from datos.notion import tipar_tareas

HOY = pd.Timestamp("2026-11-04")  # miércoles


def pagina(tarea="T", estado="Pendiente", fecha=None, prioridad=None, proyecto=None, realizada=None,
           editada="2026-11-01"):
    def opcion(tipo, valor):
        return {"type": tipo, tipo: {"name": valor} if valor else None}

    def texto(tipo, valor):
        return {"type": tipo, tipo: [{"plain_text": valor}] if valor else []}

    return {
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
