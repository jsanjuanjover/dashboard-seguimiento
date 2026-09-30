import pandas as pd

LIMITE_WIP = 5
DIAS_PARADO = 21
ESTADOS = ["Idea", "En curso", "Pausado", "Finalizado", "Abandonado"]
TIPOS = ["Proyecto", "Curso", "Libro"]
SIN_ASIGNAR = "(sin asignar)"


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
    total_valido = df["total"].where(df["total"] > 0)
    pct_cifras = (df["actual"] / total_valido).clip(0, 1)
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
    return df[df["estado"].eq("En curso")].sort_values(["pct", "ult_act_efectiva"], ascending=[False, True])


def en_progreso(df):
    """Ítems ya empezados y aún no completados (ni 0 % ni 100 %)."""
    return df[(df["pct"] > 0) & (df["pct"] < 1)]


def _curva(p, hecho, hoy):
    fechas = p.loc[hecho, "fecha_hecho"].dropna()
    if fechas.empty:
        return pd.DataFrame()
    inicio_semana = fechas.dt.to_period("W-SUN").dt.start_time
    por_semana = inicio_semana.value_counts().sort_index()
    esta_semana = pd.Period(hoy, "W-SUN").start_time
    semanas = pd.date_range(por_semana.index.min(), max(por_semana.index.max(), esta_semana), freq="7D")
    acumulado = por_semana.reindex(semanas, fill_value=0).cumsum()
    return pd.DataFrame({"Hechos": acumulado, "Total": len(p)})


def detalle(pasos, nombre, hoy):
    """Fases, siguiente paso y curva semanal acumulada de un ítem con pasos."""
    p = pasos[pasos["proyecto"].eq(nombre)].sort_values("orden")
    hecho = p["estado"].eq("Hecho")
    fases = p.assign(hecho=hecho).groupby("fase", sort=False)["hecho"].agg(hechos="sum", total="size")
    fases["pct"] = fases["hechos"] / fases["total"]
    pendientes = p[~hecho]
    siguiente = None if pendientes.empty else pendientes.iloc[0][["fase", "paso"]].to_dict()
    return {"fases": fases.reset_index(), "siguiente": siguiente, "curva": _curva(p, hecho, hoy)}


def pausados(df):
    return df[df["estado"].eq("Pausado")].sort_values("ult_act_efectiva")


def ultimos_finalizados(df, n=5):
    finalizados = df[df["estado"].eq("Finalizado")]
    return finalizados.sort_values("fin", ascending=False).head(n)


def finalizados_por_tipo(df, n=5):
    return {tipo: ultimos_finalizados(df[df["tipo"].eq(tipo)], n) for tipo in TIPOS}


def desglose(df, por):
    """Recuento de ítems por `por` (tipo o area) y estado."""
    filas = df[por].fillna(SIN_ASIGNAR)
    estados = df["estado"].fillna(SIN_ASIGNAR)
    tabla = pd.crosstab(filas, estados)
    extra = [c for c in tabla.columns if c not in ESTADOS]
    return tabla.reindex(columns=ESTADOS + extra, fill_value=0)
