import pandas as pd

LIMITE_WIP = 5
DIAS_PARADO = 21
ESTADOS = ["Idea", "En curso", "Pausado", "Finalizado", "Abandonado"]
TIPOS = ["Proyecto", "Curso", "Libro"]


def enriquecer(items, pasos, hoy):
    """Añade a cada ítem su progreso y cuánto lleva sin tocarse."""
    df = items.copy()
    totales = pasos.groupby("proyecto").size()
    hechos = pasos[pasos["estado"].eq("Hecho")].groupby("proyecto").size()
    ultimo_hecho = pasos.groupby("proyecto")["fecha_hecho"].max()

    df["pasos_total"] = df["nombre"].map(totales).fillna(0).astype(int)
    df["pasos_hechos"] = df["nombre"].map(hechos).fillna(0).astype(int)
    con_pasos = df["pasos_total"] > 0

    pct_pasos = df["pasos_hechos"] / df["pasos_total"].where(con_pasos)
    pct_cifras = (df["actual"] / df["total"]).clip(0, 1)
    df["pct"] = pct_pasos.where(con_pasos, pct_cifras).fillna(0)

    fecha_ultimo_hecho = ultimo_hecho.reindex(df["nombre"]).set_axis(df.index)
    ultimos = pd.concat([df["ult_act"], fecha_ultimo_hecho], axis=1)
    df["ult_act_efectiva"] = ultimos.max(axis=1)
    df["dias_sin_tocar"] = (hoy - df["ult_act_efectiva"]).dt.days
    df["parado"] = df["dias_sin_tocar"].gt(DIAS_PARADO)
    return df


def _este_anio(fechas, hoy):
    return fechas.dt.year.eq(hoy.year)


def _este_mes(fechas, hoy):
    return _este_anio(fechas, hoy) & fechas.dt.month.eq(hoy.month)


def metricas(df, hoy):
    terminado = df["estado"].eq("Finalizado")
    return {
        "terminados_anio": int((terminado & _este_anio(df["fin"], hoy)).sum()),
        "empezados_anio": int(_este_anio(df["inicio"], hoy).sum()),
        "terminados_mes": int((terminado & _este_mes(df["fin"], hoy)).sum()),
        "empezados_mes": int(_este_mes(df["inicio"], hoy).sum()),
        "en_curso": int(df["estado"].eq("En curso").sum()),
    }


def filtrar(df, tipos, areas):
    """Una selección vacía significa 'todos'."""
    if tipos:
        df = df[df["tipo"].isin(tipos)]
    if areas:
        df = df[df["area"].isin(areas)]
    return df


def en_curso(df):
    return df[df["estado"].eq("En curso")].sort_values("ult_act_efectiva")


def pausados(df):
    return df[df["estado"].eq("Pausado")].sort_values("ult_act_efectiva")


def ultimos_finalizados(df, n=5):
    finalizados = df[df["estado"].eq("Finalizado")]
    return finalizados.sort_values("fin", ascending=False).head(n)


def finalizados_por_tipo(df, n=5):
    return {tipo: ultimos_finalizados(df[df["tipo"].eq(tipo)], n) for tipo in TIPOS}


def desglose(df, por):
    """Recuento de ítems por `por` (tipo o area) y estado."""
    tabla = pd.crosstab(df[por], df["estado"])
    return tabla.reindex(columns=ESTADOS, fill_value=0)
