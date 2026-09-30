# PLAN — dashboard-seguimiento

## 1. Qué se espera del dashboard

Hacer visible, de un vistazo y en el iPad, lo que el problema de fondo esconde: empezar muchas cosas sin terminar otras.

- Cuántas cosas hay en curso a la vez, con límite WIP = 5.
- Empezados frente a terminados este año y este mes.
- Lo que lleva más de 21 días sin tocarse.

Uso: lectura y filtrado táctil. La edición se hace en Google Sheets o desde Claude. Se actualiza solo cada 1 h y con un botón "Actualizar" para forzarlo.

Decisiones cerradas:

| Tema | Decisión |
|---|---|
| Límite WIP | 5; `n/5` en rojo si se supera; cuenta solo lo empezado (progreso > 0) |
| Dispositivo | iPad nuevo táctil, apaisado (el iPad Air 2 no carga la app); también PC |
| Bloqueo del iPad | automático a ~1 h (no siempre encendido) |
| Tema | automático (sigue el del sistema) |
| Privacidad | app privada en Community Cloud |
| Parado | 21 días fijos; sin `ult_act` se muestra "sin fecha", sin alerta |
| Alcance v1 | incluye filtros, No empezados, Pausados, Últimos finalizados y desglose |

## 2. Pantalla (v1)

1. **Fila de 5 métricas:** terminados año, empezados año, terminados mes, empezados mes, En curso `n/5`.
2. **Filtros táctiles:** tipo (Proyecto/Curso/Libro) y área.
3. **Lista En curso:** desplegable (por defecto "Todos", ordenada por progreso descendente) o detalle de un ítem; barra de progreso, ⚠️ si >21 días.
4. **No empezados:** debajo de En curso; ítems En curso al 0 %, que suben solos al tener avance. La métrica En curso solo cuenta lo empezado.
5. **Pausados:** nombre y desde cuándo.
6. **Últimos finalizados:** lista corta ordenada por `fin`.
7. **Desglose:** recuentos por tipo y por área.

## 3. Reglas de datos

- Terminado = `estado == "Finalizado"` con `fin` en el periodo. Empezado = `inicio` en el periodo.
- Progreso = `actual / total`, recortado a 0–1. Con pasos en `Pasos`, pasos Hecho / pasos totales. Un `total` vacío o <= 0 (sin pasos) cuenta como "sin datos" y progreso 0 %.
- En curso = estado En curso con progreso > 0. No empezados = estado En curso con progreso 0.
- La app no debe romper con NaN ni con filas incompletas.
- La hoja solo guarda filas; todos los cálculos van en la app.

## 4. Fases

| Fase | Contenido | Hecho cuando | Estado |
|---|---|---|---|
| F0 Cuentas y hoja | Compartir la hoja con la cuenta de servicio (Lectora); cargar proyectos, cursos y libros | La cuenta de servicio lee la hoja y hay datos reales | ✅ |
| F1 Repo | `.gitignore` con `.streamlit/secrets.toml` antes del primer commit; `pyproject.toml` + `uv.lock` y `requirements.txt` exportado; `secrets.toml` local | Repo creado sin secretos versionados | ✅ |
| F2 App base | `app.py` en local: métricas, lista En curso y aviso WIP | `streamlit run app.py` muestra la hoja real | ✅ |
| F3 Extras v1 | Filtros, No empezados, Pausados, Últimos finalizados, desglose, detalle por ítem | Los bloques responden a los filtros | ✅ (PR #1 y #2) |
| F4 Despliegue | Community Cloud privado; Secrets pegados | URL privada funcionando | Pendiente |
| F5 iPad | Acceso directo en pantalla de inicio; login Google | Tras editar la hoja, el botón "Actualizar" muestra el cambio al instante | Pendiente |
| F6 Uso | 2 semanas de uso; ideas nuevas como filas en la hoja | Revisión de qué sobra o falta | Pendiente |

Después: skill `seguimiento` para actualizar la hoja desde cualquier chat y tarea semanal de lo parado.

## 5. Riesgos y verificación

- "permission denied" o "not found": la hoja no está compartida con la cuenta de servicio.
- Hibernación tras 12 h: puede hacer falta despertar la app. Con el bloqueo del iPad a ~1 h, puede que haya que refrescar al desbloquear.
- Solo 1 app privada en Community Cloud.
- Pueden acumularse ítems En curso al 0 % sin que el límite WIP avise, porque solo cuenta lo empezado.
- Verificación: primero con filas simuladas, luego con la hoja real; comprobar la vista en iPad y PC, y modo claro y oscuro.

## 6. Decisiones sobre áreas y listas

- Áreas: Trabajo, Aprendizaje, Personal/Casa, con desplegable en la hoja. Se puede añadir alguna más en el futuro editando el desplegable.
- Últimos finalizados: 5 ítems.
- Desglose y filtros por área: solo 3 áreas de momento. Si en el futuro se añaden más, se revisará el diseño (no se implementa ahora).
- No empezados: los ítems con estado `Idea` no entran. Un ítem con `actual > 0` pero sin `total` válido ni pasos cuenta como 0 %, no consume el límite y aparece en No empezados con un aviso; se deja así a propósito.

## 7. Siguiente paso

F0 y F1 están completas. Queda, en orden:
- [ ] Ver la app en el navegador (`uv run streamlit run app.py`) y ajustar lo visual, sobre todo en el iPad.
- [ ] F4: desplegar en Streamlit Community Cloud (privado) y pegar el contenido de `secrets.toml` en los Secrets de la app.
- [ ] F5: abrir la URL en el iPad, añadirla a la pantalla de inicio y entrar con Google.
- [ ] F6: usarla dos semanas antes de añadir funciones.

## 8. Tareas que se derivan

- [x] En la hoja: pasar la columna `area` a desplegable con las 3 áreas y revisar los valores ya escritos (p. ej. la fila TFM HAR tenía "Máster").
