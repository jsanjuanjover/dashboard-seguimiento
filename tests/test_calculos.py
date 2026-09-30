import numpy as np
import pandas as pd
import pytest

from datos.calculos import (
    desglose,
    detalle,
    en_curso,
    en_progreso,
    enriquecer,
    filtrar,
    finalizados_por_tipo,
    metricas,
    no_empezados,
    ultimos_finalizados,
)
from datos.carga import tipar_items, tipar_pasos

HOY = pd.Timestamp("2026-09-30")


def items(*filas):
    cols = ["nombre", "tipo", "area", "estado", "inicio", "fin", "actual", "total", "unidad", "ult_act"]
    return tipar_items(pd.DataFrame(filas, columns=cols))


def pasos(*filas):
    cols = ["proyecto", "fase", "paso", "orden", "estado", "fecha_hecho"]
    return tipar_pasos(pd.DataFrame(filas, columns=cols))


def fila(nombre="X", tipo="Libro", area="Aprendizaje", estado="En curso", inicio=None, fin=None,
         actual=None, total=None, unidad="págs", ult_act=None):
    return [nombre, tipo, area, estado, inicio, fin, actual, total, unidad, ult_act]


SIN_PASOS = pasos()


def test_fechas_se_leen_como_dia_mes_anio():
    df = items(fila(inicio="01/02/2026"))
    assert df["inicio"].iloc[0] == pd.Timestamp("2026-02-01")


def test_columnas_vacias_no_rompen():
    df = items(fila(fin=np.nan, actual=np.nan, total=np.nan, ult_act=np.nan))
    assert df["fin"].isna().all()
    assert enriquecer(df, SIN_PASOS, HOY)["pct"].iloc[0] == 0


def test_progreso_por_cifras_recortado():
    df = items(fila("a", actual=270, total=540), fila("b", actual=800, total=540), fila("c", actual=None, total=100))
    pct = enriquecer(df, SIN_PASOS, HOY).set_index("nombre")["pct"]
    assert pct["a"] == 0.5
    assert pct["b"] == 1
    assert pct["c"] == 0


def test_progreso_por_pasos_ignora_cifras():
    df = items(fila("TFM", tipo="Proyecto", actual=90, total=100))
    p = pasos(
        ["TFM", "1. Datos", "a", 1, "Hecho", "20/09/2026"],
        ["TFM", "1. Datos", "b", 2, "Pendiente", None],
        ["TFM", "2. Modelos", "c", 3, "Pendiente", None],
        ["TFM", "2. Modelos", "d", 4, "Pendiente", None],
    )
    r = enriquecer(df, p, HOY).iloc[0]
    assert r["pct"] == 0.25
    assert (r["pasos_hechos"], r["pasos_total"]) == (1, 4)


def test_ult_act_efectiva_es_el_maximo():
    df = items(fila("TFM", ult_act="01/09/2026"), fila("Otro", ult_act="15/09/2026"))
    p = pasos(["TFM", "f", "a", 1, "Hecho", "20/09/2026"], ["Otro", "f", "a", 1, "Hecho", "01/09/2026"])
    r = enriquecer(df, p, HOY).set_index("nombre")["ult_act_efectiva"]
    assert r["TFM"] == pd.Timestamp("2026-09-20")
    assert r["Otro"] == pd.Timestamp("2026-09-15")


@pytest.mark.parametrize(
    "ult_act, parado",
    [("08/09/2026", True), ("09/09/2026", False), ("30/09/2026", False), (None, False)],
)
def test_parado_a_partir_de_21_dias(ult_act, parado):
    df = items(fila(ult_act=ult_act))
    assert enriquecer(df, SIN_PASOS, HOY)["parado"].iloc[0] == parado


def test_metricas_en_los_bordes_de_periodo():
    df = items(
        fila("mes", estado="Finalizado", fin="01/09/2026", inicio="01/09/2026"),
        fila("anio", estado="Finalizado", fin="31/08/2026", inicio="31/08/2026"),
        fila("anio_pasado", estado="Finalizado", fin="31/12/2025", inicio="31/12/2025"),
        fila("mismo_mes_otro_anio", estado="Finalizado", fin="15/09/2025"),
        fila("abandonado", estado="Abandonado", fin="10/09/2026"),
        fila("curso", actual=5, total=10),
    )
    m = metricas(enriquecer(df, SIN_PASOS, HOY), HOY)
    assert m == {
        "terminados_anio": 2,
        "empezados_anio": 2,
        "terminados_mes": 1,
        "empezados_mes": 1,
        "en_curso": 1,
    }


def test_en_curso_ordena_por_progreso_descendente():
    df = items(
        fila("medio", actual=5, total=10),
        fila("cero", actual=0, total=10),
        fila("casi", actual=9, total=10),
        fila("pausa", estado="Pausado", actual=10, total=10),
    )
    r = en_curso(enriquecer(df, SIN_PASOS, HOY))
    assert list(r["nombre"]) == ["casi", "medio"]


def test_en_curso_empate_de_progreso_mas_parado_primero_y_sin_fecha_al_final():
    df = items(
        fila("nuevo", actual=5, total=10, ult_act="29/09/2026"),
        fila("sin_fecha", actual=5, total=10, ult_act=None),
        fila("viejo", actual=5, total=10, ult_act="01/08/2026"),
    )
    r = en_curso(enriquecer(df, SIN_PASOS, HOY))
    assert list(r["nombre"]) == ["viejo", "nuevo", "sin_fecha"]


def test_no_empezados_son_los_en_curso_al_cero_por_ciento():
    df = items(
        fila("empezado", actual=1, total=10),
        fila("cero", actual=0, total=10),
        fila("vacio", actual=None, total=10),
        fila("idea", estado="Idea", actual=0, total=10),
        fila("pausa", estado="Pausado", actual=0, total=10),
    )
    d = enriquecer(df, SIN_PASOS, HOY)
    assert list(no_empezados(d)["nombre"]) == ["cero", "vacio"]
    assert list(en_curso(d)["nombre"]) == ["empezado"]


def test_en_curso_y_no_empezados_no_se_solapan_y_suman_los_marcados():
    df = items(*[fila(f"i{i}", actual=i, total=4) for i in range(5)])
    d = enriquecer(df, SIN_PASOS, HOY)
    assert set(en_curso(d)["nombre"]).isdisjoint(no_empezados(d)["nombre"])
    assert len(en_curso(d)) + len(no_empezados(d)) == 5


def test_un_item_sube_a_en_curso_en_cuanto_tiene_avance():
    antes = enriquecer(items(fila("libro", actual=0, total=100)), SIN_PASOS, HOY)
    despues = enriquecer(items(fila("libro", actual=1, total=100)), SIN_PASOS, HOY)
    assert list(no_empezados(antes)["nombre"]) == ["libro"] and en_curso(antes).empty
    assert list(en_curso(despues)["nombre"]) == ["libro"] and no_empezados(despues).empty


def test_item_con_pasos_y_ninguno_hecho_es_no_empezado_sin_marcar_sin_datos():
    p = pasos(["TFM", "1", "a", 1, "Pendiente", None], ["TFM", "1", "b", 2, "Pendiente", None])
    d = enriquecer(items(fila("TFM", tipo="Proyecto")), p, HOY)
    assert list(no_empezados(d)["nombre"]) == ["TFM"]
    assert not d["sin_datos"].iloc[0]


def test_sin_datos_solo_sin_total_valido_ni_pasos():
    df = items(fila("vacio"), fila("total_cero", total=0), fila("normal", actual=0, total=10))
    d = enriquecer(df, SIN_PASOS, HOY).set_index("nombre")
    assert list(d["sin_datos"]) == [True, True, False]
    assert list(no_empezados(d.reset_index())["nombre"]) == ["normal", "total_cero", "vacio"]


def test_metrica_en_curso_cuenta_solo_lo_empezado():
    df = items(fila("a", actual=3, total=10), fila("b", actual=0, total=10), fila("c"))
    assert metricas(enriquecer(df, SIN_PASOS, HOY), HOY)["en_curso"] == 1


def test_ultimos_finalizados_recientes_y_limitados():
    filas = [fila(f"l{i}", estado="Finalizado", fin=f"{i:02d}/01/2026") for i in range(1, 8)]
    r = ultimos_finalizados(enriquecer(items(*filas), SIN_PASOS, HOY), n=5)
    assert list(r["nombre"]) == ["l7", "l6", "l5", "l4", "l3"]


def test_desglose_cuadra_con_celdas_vacias():
    df = items(
        fila("a", area="Trabajo"),
        fila("b", area=None),
        fila("c", area="Trabajo", estado=None),
        fila("d", tipo=None, area="Trabajo"),
    )
    por_area = desglose(df, "area")
    assert por_area.to_numpy().sum() == len(df)
    assert por_area.loc["(sin asignar)", "En curso"] == 1
    assert por_area.loc["Trabajo", "(sin asignar)"] == 1
    assert desglose(df, "tipo").to_numpy().sum() == len(df)


def test_finalizados_separados_por_tipo_con_limite_por_tipo():
    filas = [fila(f"l{i}", tipo="Libro", estado="Finalizado", fin=f"{i:02d}/01/2026") for i in range(1, 8)]
    filas += [fila("c1", tipo="Curso", estado="Finalizado", fin="01/02/2026"), fila("p1", tipo="Proyecto")]
    r = finalizados_por_tipo(enriquecer(items(*filas), SIN_PASOS, HOY), n=5)
    assert list(r) == ["Proyecto", "Curso", "Libro"]
    assert list(r["Libro"]["nombre"]) == ["l7", "l6", "l5", "l4", "l3"]
    assert list(r["Curso"]["nombre"]) == ["c1"]
    assert r["Proyecto"].empty


def test_total_cero_se_trata_como_sin_datos():
    df = items(fila(actual=30, total=0), fila("neg", actual=30, total=-5))
    assert list(enriquecer(df, SIN_PASOS, HOY)["pct"]) == [0, 0]


def test_en_progreso_excluye_0_y_100():
    df = items(fila("cero", actual=0, total=10), fila("medio", actual=5, total=10), fila("lleno", actual=10, total=10))
    r = en_progreso(enriquecer(df, SIN_PASOS, HOY))
    assert list(r["nombre"]) == ["medio"]


def test_detalle_fases_siguiente_paso_y_curva():
    p = pasos(
        ["TFM", "2. Modelos", "e", 5, "Pendiente", None],
        ["TFM", "1. Datos", "b", 2, "Hecho", "10/09/2026"],
        ["TFM", "2. Modelos", "d", 4, "Hecho", "22/09/2026"],
        ["TFM", "1. Datos", "c", 3, "Pendiente", None],
        ["TFM", "1. Datos", "a", 1, "Hecho", "08/09/2026"],
        ["Otro", "X", "z", 1, "Hecho", "01/09/2026"],
    )
    d = detalle(p, "TFM", HOY)
    assert list(d["fases"]["fase"]) == ["1. Datos", "2. Modelos"]
    assert list(d["fases"]["hechos"]) == [2, 1]
    assert list(d["fases"]["total"]) == [3, 2]
    assert d["siguiente"] == {"fase": "1. Datos", "paso": "c"}
    assert list(d["curva"]["Hechos"]) == [2, 2, 3, 3]
    assert list(d["curva"]["Total"]) == [5, 5, 5, 5]
    assert d["curva"].index[0] == pd.Timestamp("2026-09-07")


def test_detalle_sin_pasos_no_rompe():
    d = detalle(SIN_PASOS, "TFM", HOY)
    assert d["fases"].empty and d["siguiente"] is None and d["curva"].empty


def test_filtrar_seleccion_vacia_es_todos():
    df = items(fila("a", tipo="Libro"), fila("b", tipo="Curso", area="Trabajo"))
    assert len(filtrar(df, [], [])) == 2
    assert list(filtrar(df, ["Curso"], [])["nombre"]) == ["b"]
    assert list(filtrar(df, [], ["Trabajo"])["nombre"]) == ["b"]


def test_desglose_incluye_todos_los_estados():
    df = items(fila("a", tipo="Libro"), fila("b", tipo="Libro", estado="Pausado"), fila("c", tipo="Curso"))
    t = desglose(df, "tipo")
    assert t.loc["Libro", "En curso"] == 1
    assert t.loc["Libro", "Pausado"] == 1
    assert t.loc["Curso", "Finalizado"] == 0
