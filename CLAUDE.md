# dashboard-seguimiento

Dashboard personal para ver de un vistazo los proyectos, cursos y libros abiertos y terminados, y su progreso. Se muestra en un iPad táctil (y en el PC) y se actualiza solo cuando cambia la hoja de cálculo.

## Por qué existe

El problema de fondo es empezar muchos proyectos sin terminar otros. El dashboard tiene que hacer visible:
- cuántas cosas hay en curso a la vez (con un límite de "en curso", tipo límite WIP de Kanban),
- empezados frente a terminados este año y este mes,
- lo que lleva semanas sin tocarse.

Regla del proyecto: la v1 (que incluye los bloques descritos en "Contenido de la v1") se termina en una sesión y no se añaden más funciones hasta haberla usado dos semanas. Si una idea nueva aparece, se apunta como fila en la hoja, no se implementa.

## Arquitectura

```
Google Sheet "dashboard-seguimiento" (pestaña Items)   <- fuente única de datos
   ^ edición a mano (app de Sheets) y desde chats de Claude (conector de Google Sheets)
   |
   | lectura con cuenta de servicio (solo lectura)
   v
App Streamlit (este repo)  ->  Streamlit Community Cloud  ->  URL en tablet y PC
```

- La hoja solo guarda filas, sin fórmulas. Todos los recuentos los calcula la app.
- Actualización por sondeo: `conn.read(ttl="1m")` + `@st.fragment(run_every="1m")`. Un cambio en la hoja aparece en la tablet en 1–2 min.

## Cuentas (importante)

- La hoja y el proyecto de Google Cloud pertenecen a una cuenta **Gmail personal**. La cuenta de la UOC tiene Google Cloud desactivado por el administrador, así que no sirve para esto.
- La hoja está compartida con la cuenta de la UOC como Editora (para editarla desde Claude) y debe estarlo con la cuenta de servicio como Lectora.
- Todo es gratis: Sheets API y Drive API sin facturación, Streamlit Community Cloud gratis. No activar facturación ni la prueba gratuita de Google Cloud.

## Esquema de la hoja (pestaña `Items`)

Configuración regional es_ES: las fechas se muestran como `dd/mm/aaaa`.

| columna | tipo | valores / notas |
|---|---|---|
| nombre | texto | clave legible del ítem |
| tipo | desplegable | Proyecto, Curso, Libro |
| area | desplegable | Trabajo, Aprendizaje, Personal/Casa (se pueden añadir más editando el desplegable; el dashboard admite hasta 3 de momento) |
| estado | desplegable | Idea, En curso, Pausado, Finalizado, Abandonado |
| inicio | fecha | dd/mm/aaaa |
| fin | fecha | solo si está Finalizado o Abandonado |
| actual | número | páginas leídas, módulos hechos o % |
| total | número | total de páginas, módulos o 100 |
| unidad | texto | págs, módulos, % |
| ult_act | fecha | última vez que se tocó; sirve para detectar lo parado |

Para libros y cursos, progreso = `actual / total` (recortado a 0–1). Para ítems con pasos en la pestaña `Pasos`, el progreso sale de los pasos (ver abajo) y `actual/total` se ignora.

## Esquema de la hoja (pestaña `Pasos`)

Una fila por paso (subfase u objetivo) de un proyecto. Dos niveles: fase > paso.

| columna | tipo | valores / notas |
|---|---|---|
| proyecto | desplegable | nombres de `Items!A2:A` (clave de cruce con `Items.nombre`) |
| fase | texto | p. ej. "1. Datos"; el prefijo numérico ordena las fases |
| paso | texto | subfase u objetivo concreto |
| orden | número | secuencia del paso dentro del proyecto |
| estado | desplegable | Pendiente, En curso, Hecho |
| fecha_hecho | fecha | dd/mm/aaaa; solo cuando estado = Hecho |

Todos los pasos pesan igual (decisión de diseño; si hiciera falta, más adelante se añade una columna `peso`).

Cálculos en la app a partir de `Pasos`:
- Progreso del proyecto = pasos Hecho / pasos totales.
- Progreso por fase (p. ej. "Datos 2/3 · Modelos 0/4").
- Progresión en el tiempo: curva acumulada de pasos hechos por semana frente al total, a partir de `fecha_hecho` (no se guardan históricos).
- Siguiente paso: el primer paso no Hecho por `orden`.
- `ult_act` efectiva = máximo entre `Items.ult_act` y el último `fecha_hecho` del proyecto.

## Estado actual

Hecho:
- [x] Decidida la opción: Google Sheet + Streamlit en Community Cloud.
- [x] Hoja `dashboard-seguimiento` creada en la cuenta Gmail, compartida con la cuenta de la UOC como Editora (comprobado: Claude puede leer y escribir en ella).
- [x] Pestaña renombrada a `Items`, cabeceras, fila 1 congelada, desplegables en `tipo` y `estado`, formato de fecha en `inicio`, `fin` y `ult_act`.
- [x] Precarga: una fila, `TFM HAR` (Proyecto, Máster, En curso, total 100, unidad %). Faltan su fecha de inicio, `actual` y `ult_act`.
- [x] Pestaña `Pasos` creada: cabeceras, fila 1 congelada, desplegable de `proyecto` ligado a `Items!A2:A`, desplegable de `estado`, formato de fecha en `fecha_hecho`. Vacía: las fases del TFM las define el usuario.
- [x] Proyecto de Google Cloud en la cuenta Gmail con Google Sheets API y Google Drive API habilitadas.
- [x] Cuenta de servicio creada con su clave JSON (guardada fuera de cualquier repo).

Pendiente:
- [ ] Confirmar que la hoja está compartida con el email de la cuenta de servicio como Lectora.
- [ ] Completar la fila del TFM y añadir el resto de proyectos, cursos y libros.
- [ ] Crear el repo en GitHub (`jsanjuanjover`), privado si la app debe ser privada.
- [ ] Estructura mínima: `app.py`, `requirements.txt` (`streamlit`, `st-gsheets-connection`), `.gitignore` con `.streamlit/secrets.toml` **antes del primer commit**.
- [ ] `.streamlit/secrets.toml` con `[connections.gsheets]`: `spreadsheet = "<URL de la hoja>"` y todos los campos del JSON de la cuenta de servicio.
- [ ] `app.py` v1 funcionando en local (`streamlit run app.py`).
- [ ] Push y despliegue en Streamlit Community Cloud; pegar el contenido de `secrets.toml` en los Secrets de la app.
- [ ] iPad: abrir la URL (acceso directo en la pantalla de inicio), login con Google (la app es privada). El iPad se bloquea solo tras ~1 h; no hace falta pantalla siempre encendida.
- [ ] Más adelante: mini-skill `seguimiento` para que cualquier chat de Claude actualice la hoja con las mismas reglas.
- [ ] Opcional: tarea programada semanal que revise lo parado.

## Contenido de la v1

- Métricas: terminados este año, empezados este año, terminados este mes, empezados este mes, en curso con el límite WIP = 5 (`n/5`, en rojo si se supera).
- Filtros táctiles por tipo (Proyecto/Curso/Libro) y por área.
- Lista de lo que está en curso con barra de progreso, ordenada por `ult_act`, marcando lo que lleva más de 21 días sin tocar. Sin `ult_act` se muestra "—" y no se alerta.
- Bloque Pausados: nombre y desde cuándo.
- Bloque Últimos finalizados: lista corta ordenada por `fin`.
- Desglose por tipo y por área (recuentos).
- Tema automático (sigue el del sistema).
- Diseño apaisado pensado para el iPad que también funcione en el PC.

- Por proyecto con pasos: barra de progreso por fase, siguiente paso y curva acumulada de pasos hechos por semana.

"Terminado" = `estado == "Finalizado"` con `fin` en el periodo. "Empezado" = `inicio` en el periodo.

## Punto de partida para `app.py`

Probado con filas simuladas (no aún contra la hoja real). Solo cubre `Items`; falta añadir la lectura de `Pasos` (`conn.read(worksheet="Pasos", ttl="1m")`) y los cálculos de la sección anterior:

```python
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Seguimiento", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

@st.fragment(run_every="1m")  # se repinta sola cada minuto
def dashboard():
    df = conn.read(worksheet="Items", ttl="1m")  # relee la hoja como mucho 1 vez/min
    for col in ["inicio", "fin", "ult_act"]:
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
    df["pct"] = (df["actual"] / df["total"]).clip(0, 1).fillna(0)
    hoy = pd.Timestamp.today()

    def este_anio(s): return s.dt.year.eq(hoy.year)
    def este_mes(s): return este_anio(s) & s.dt.month.eq(hoy.month)
    terminado = df["estado"].eq("Finalizado")
    wip = df[df["estado"].eq("En curso")].sort_values("ult_act")

    c = st.columns(5)
    c[0].metric("Terminados este año", int((terminado & este_anio(df["fin"])).sum()))
    c[1].metric("Empezados este año", int(este_anio(df["inicio"]).sum()))
    c[2].metric("Terminados este mes", int((terminado & este_mes(df["fin"])).sum()))
    c[3].metric("Empezados este mes", int(este_mes(df["inicio"]).sum()))
    c[4].metric("En curso", len(wip))

    for _, r in wip.iterrows():
        alerta = "⚠️ " if (hoy - r["ult_act"]).days > 21 else ""
        st.progress(r["pct"], text=f"{alerta}{r['nombre']} · {r['actual']:.0f}/{r['total']:.0f} {r['unidad']}")

dashboard()
```

## Riesgos conocidos

- Community Cloud solo permite **una app privada a la vez**; los viewers se invitan por email.
- La app hiberna tras 12 h sin tráfico y hay que despertarla con un botón. No está confirmado si una sesión abierta que se refresca sola cuenta como tráfico. Como el iPad se bloquea a ~1 h, al desbloquearlo puede hacer falta refrescar la URL.
- Si la lectura falla con "permission denied" o "not found", casi seguro es que la hoja no está compartida con la cuenta de servicio.
- Columnas vacías pueden llegar como NaN: la app no debe romper con filas incompletas.
