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
| Límite WIP | 5; `n/5` en rojo si se supera |
| Dispositivo | iPad táctil, apaisado; también PC |
| Bloqueo del iPad | automático a ~1 h (no siempre encendido) |
| Tema | automático (sigue el del sistema) |
| Privacidad | app privada en Community Cloud |
| Parado | 21 días fijos; sin `ult_act` se muestra "sin fecha", sin alerta |
| Alcance v1 | incluye filtros, Pausados, Últimos finalizados y desglose |

## 2. Pantalla (v1)

1. **Fila de 5 métricas:** terminados año, empezados año, terminados mes, empezados mes, En curso `n/5`.
2. **Filtros táctiles:** tipo (Proyecto/Curso/Libro) y área.
3. **Lista En curso:** barra de progreso, orden por `ult_act`, ⚠️ si >21 días.
4. **Pausados:** nombre y desde cuándo.
5. **Últimos finalizados:** lista corta ordenada por `fin`.
6. **Desglose:** recuentos por tipo y por área.

## 3. Reglas de datos

- Terminado = `estado == "Finalizado"` con `fin` en el periodo. Empezado = `inicio` en el periodo.
- Progreso = `actual / total`, recortado a 0–1.
- La app no debe romper con NaN ni con filas incompletas.
- La hoja solo guarda filas; todos los cálculos van en la app.

## 4. Fases

| Fase | Contenido | Hecho cuando |
|---|---|---|
| F0 Cuentas y hoja | Compartir la hoja con la cuenta de servicio (Lectora); completar la fila del TFM; cargar proyectos, cursos y libros | La cuenta de servicio lee la hoja y hay datos reales |
| F1 Repo | `.gitignore` con `.streamlit/secrets.toml` antes del primer commit; `requirements.txt`; `secrets.toml` local | Repo creado sin secretos versionados |
| F2 App base | `app.py` en local: métricas, lista En curso y aviso WIP | `streamlit run app.py` muestra la hoja real |
| F3 Extras v1 | Filtros, Pausados, Últimos finalizados, desglose | Los bloques responden a los filtros |
| F4 Despliegue | Community Cloud privado; Secrets pegados | URL privada funcionando |
| F5 iPad | Acceso directo en pantalla de inicio; login Google | Tras editar la hoja, el botón "Actualizar" muestra el cambio al instante |
| F6 Uso | 2 semanas de uso; ideas nuevas como filas en la hoja | Revisión de qué sobra o falta |

Después: skill `seguimiento` para actualizar la hoja desde cualquier chat y tarea semanal de lo parado.

## 5. Riesgos y verificación

- "permission denied" o "not found": la hoja no está compartida con la cuenta de servicio.
- Hibernación tras 12 h: puede hacer falta despertar la app. Con el bloqueo del iPad a ~1 h, puede que haya que refrescar al desbloquear.
- Solo 1 app privada en Community Cloud.
- Verificación: primero con filas simuladas, luego con la hoja real; comprobar la vista en iPad y PC, y modo claro y oscuro.

## 6. Decisiones sobre áreas y listas

- Áreas: Trabajo, Aprendizaje, Personal/Casa, con desplegable en la hoja. Se puede añadir alguna más en el futuro editando el desplegable.
- Últimos finalizados: 5 ítems.
- Desglose y filtros por área: solo 3 áreas de momento. Si en el futuro se añaden más, se revisará el diseño (no se implementa ahora).

## 7. Para continuar mañana (30/09/2026)

F0, a mano:
- [ ] Copiar `client_email` del JSON de la cuenta de servicio y compartir la hoja con ese email como Lectora.
- [ ] Completar la fila del TFM: `inicio`, `actual` y `ult_act`.
- [ ] Cargar el resto de proyectos, cursos y libros (áreas: Trabajo, Aprendizaje, Personal/Casa).

Después, F1 (con Claude):
- [ ] Crear el repo con `.gitignore` con `.streamlit/secrets.toml` antes del primer commit.
- [ ] `requirements.txt` (`streamlit`, `st-gsheets-connection`); Claude pregunta antes de instalar.
- [ ] `.streamlit/secrets.toml` local con `[connections.gsheets]`.

## 8. Tareas que se derivan

- [x] En la hoja: pasar la columna `area` a desplegable con las 3 áreas y revisar los valores ya escritos (p. ej. la fila TFM HAR tenía "Máster").
