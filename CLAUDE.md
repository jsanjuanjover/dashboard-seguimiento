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
Google Sheet "dashboard-seguimiento" (pestañas Items y Pasos)   <- fuente única de datos
   ^ edición a mano (app de Sheets) y desde chats de Claude (conector de Google Sheets)
   |
   | lectura con cuenta de servicio (solo lectura)
   v
App Streamlit (este repo)  ->  Streamlit Community Cloud  ->  URL en tablet y PC
```

- La hoja solo guarda filas, sin fórmulas. Todos los recuentos los calcula la app.
- Actualización por sondeo cada 1 h: lectura en caché con `ttl="1h"` + `@st.fragment(run_every="1h")`. Como la hoja cambia 2-3 veces al día, hay un botón "Actualizar" que vacía la caché y relee al instante, y junto a él se muestra la hora de la última lectura real.

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
- [x] Pestaña `Pasos` creada: cabeceras, fila 1 congelada, desplegable de `proyecto` ligado a `Items!A2:A`, desplegable de `estado`, formato de fecha en `fecha_hecho`.
- [x] Desplegable en `area` con Trabajo, Aprendizaje y Personal/Casa.
- [x] Datos reales cargados en `Items` y `Pasos` (fases y pasos del TFM y de otros cursos).
- [x] Proyecto de Google Cloud en la cuenta Gmail con Google Sheets API y Google Drive API habilitadas.
- [x] Cuenta de servicio creada con su clave JSON (guardada fuera de cualquier repo) y hoja compartida con ella como Lectora (comprobado: la app lee las dos pestañas).
- [x] Repo privado en GitHub (`jsanjuanjover/dashboard-seguimiento`), con `.gitignore` (incluye `.streamlit/secrets.toml`) antes del primer commit.
- [x] Entorno con `uv` (`pyproject.toml` + `uv.lock`) y `requirements.txt` exportado para la nube.
- [x] `.streamlit/secrets.toml` local con `[connections.gsheets]` (ignorado por git).
- [x] `app.py` v1 escrita (capa `datos/`, capa `vistas/`, 21 tests) y comprobada de forma automática contra la hoja real.

Pendiente:
- [ ] Ver la app en el navegador (`uv run streamlit run app.py`) y ajustar lo visual, sobre todo en el iPad.
- [ ] Revisar y fusionar la rama `feat/dashboard-v1` en `main`.
- [ ] Despliegue en Streamlit Community Cloud; pegar el contenido de `secrets.toml` en los Secrets de la app.
- [ ] iPad: abrir la URL (acceso directo en la pantalla de inicio), login con Google (la app es privada). El iPad se bloquea solo tras ~1 h; no hace falta pantalla siempre encendida.
- [ ] Más adelante: mini-skill `seguimiento` para que cualquier chat de Claude actualice la hoja con las mismas reglas.
- [ ] Opcional: tarea programada semanal que revise lo parado.

## Contenido de la v1

- Botón "Actualizar" y hora de la última lectura real (hora de Madrid).
- Métricas: terminados este año, empezados este año, terminados este mes, empezados este mes, en curso con el límite WIP = 5 (`n/5`, delta en rojo si se supera). Las métricas y el límite se calculan siempre sobre todos los ítems, sin filtros.
- Filtros táctiles por tipo (Proyecto/Curso/Libro) y por área. Afectan solo a las listas y al desglose; una selección vacía significa "todos".
- Cada barra de progreso (lista, ítem y fases) lleva a la derecha su porcentaje, cortado hacia abajo: solo muestra 100 % cuando está completo.
- Bloque En curso, con un desplegable (por defecto "Todos"):
  - "Todos": lista de todos los ítems en curso con barra de progreso, ordenada por progreso de mayor a menor (los del 0 % al final). Entre ítems con el mismo progreso va primero el más parado, y los que no tienen `ult_act` al final. Marca lo que lleva más de 21 días sin tocar; sin `ult_act` se muestra "sin fecha" y no se alerta.
  - Una opción por ítem con progreso entre 0 % y 100 % (los que están al 0 % no aparecen como opción): barra por fase, siguiente paso y curva acumulada de pasos hechos por semana (solo si el ítem tiene pasos en `Pasos`). Con filtros activos, el desplegable ofrece solo los ítems filtrados.
- Bloque Pausados: nombre y desde cuándo.
- Bloque Últimos finalizados: pestañas por tipo (Proyectos, Cursos, Libros), con los últimos 5 de cada uno en lista numerada, ordenados por `fin`.
- Desglose por tipo y por área (recuentos por estado). Los ítems con celdas vacías aparecen como "(sin asignar)" para que los totales cuadren.
- Tema automático (sigue el del sistema).
- Diseño apaisado pensado para el iPad que también funcione en el PC.

"Terminado" = `estado == "Finalizado"` con `fin` en el periodo. "Empezado" = `inicio` en el periodo. Un total `<= 0` cuenta como "sin datos" (progreso 0 %).

## Estructura del código

```
app.py                 # entrada: configuración, conexión, caché de lectura (1 h), botón y orden de los bloques
datos/
  carga.py             # lee las hojas y convierte fechas dd/mm/aaaa y números (tolera huecos)
  calculos.py          # reglas: progreso, parado, métricas, listas, detalle por pasos, desglose
vistas/
  bloques.py           # solo dibuja: métricas, filtros, En curso, Pausados, Finalizados, Desglose
tests/
  test_calculos.py     # comprueba las reglas con filas inventadas (bordes de fechas, huecos, etc.)
```

- `datos/` no importa Streamlit; `vistas/` no calcula; `app.py` conecta ambas capas.
- La hora que se usa para los periodos y para "Actualizado a las" es Europe/Madrid (Community Cloud funciona en UTC).
- Ejecutar en local: `uv run streamlit run app.py`. Tests: `uv run pytest`.
- Community Cloud lee `requirements.txt`. Tras cambiar dependencias con `uv add`, regenerarlo: `uv export --no-hashes --no-dev --no-emit-project -o requirements.txt`.

## Riesgos conocidos

- Community Cloud solo permite **una app privada a la vez**; los viewers se invitan por email.
- La app hiberna tras 12 h sin tráfico y hay que despertarla con un botón. No está confirmado si una sesión abierta que se refresca sola cuenta como tráfico. Como el iPad se bloquea a ~1 h, al desbloquearlo puede hacer falta refrescar la URL.
- Si la lectura falla con "permission denied" o "not found", casi seguro es que la hoja no está compartida con la cuenta de servicio.
- Columnas vacías pueden llegar como NaN: la app no debe romper con filas incompletas.
