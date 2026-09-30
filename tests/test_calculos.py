import numpy as np
import pandas as pd
import pytest

from datos.calculos import (
    desglose,
    en_curso,
    enriquecer,
    filtrar,
    finalizados_por_tipo,
    metricas,
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
        fila("curso"),
    )
    m = metricas(enriquecer(df, SIN_PASOS, HOY), HOY)
    assert m == {
        "terminados_anio": 2,
        "empezados_anio": 2,
        "terminados_mes": 1,
        "empezados_mes": 1,
        "en_curso": 1,
    }


def test_en_curso_ordena_por_mas_parado_primero():
    df = items(fila("nuevo", ult_act="29/09/2026"), fila("viejo", ult_act="01/08/2026"), fila("pausa", estado="Pausado"))
    r = en_curso(enriquecer(df, SIN_PASOS, HOY))
    assert list(r["nombre"]) == ["viejo", "nuevo"]


def test_ultimos_finalizados_recientes_y_limitados():
    filas = [fila(f"l{i}", estado="Finalizado", fin=f"{i:02d}/01/2026") for i in range(1, 8)]
    r = ultimos_finalizados(enriquecer(items(*filas), SIN_PASOS, HOY), n=5)
    assert list(r["nombre"]) == ["l7", "l6", "l5", "l4", "l3"]


def test_finalizados_separados_por_tipo_con_limite_por_tipo():
    filas = [fila(f"l{i}", tipo="Libro", estado="Finalizado", fin=f"{i:02d}/01/2026") for i in range(1, 8)]
    filas += [fila("c1", tipo="Curso", estado="Finalizado", fin="01/02/2026"), fila("p1", tipo="Proyecto")]
    r = finalizados_por_tipo(enriquecer(items(*filas), SIN_PASOS, HOY), n=5)
    assert list(r) == ["Proyecto", "Curso", "Libro"]
    assert list(r["Libro"]["nombre"]) == ["l7", "l6", "l5", "l4", "l3"]
    assert list(r["Curso"]["nombre"]) == ["c1"]
    assert r["Proyecto"].empty


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
