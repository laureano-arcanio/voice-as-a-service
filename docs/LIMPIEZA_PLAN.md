# Limpieza: un solo motor, sin parches de modelo

Decisiones del 26-oct-2026, después de implementar las herramientas del cliente (`docs/TOOLS_PLAN.md`).
Criterio: la plataforma no corrige por código ni por prompt lo que el modelo hace mal; los tests prueban el
código (LLM falso), los evals miden el modelo y no bloquean, y nada se acopla a un modelo. Reglas en
`AGENTS.md`, "Reglas de desarrollo".

## Decisiones

| Tema | Decisión |
|---|---|
| Motores | **Uno solo.** Se quitan `assistant` (con sus tests, UI y docs) y la distinción `classic`/`external`: "Tu propio agente" pasa a ser una opción del agente (el LLM es la conexión del cliente y el prompt es suyo, sin extracción). La UI no pregunta el motor. Las definiciones guardadas se siguen leyendo. |
| Fin y derivación | Herramientas nativas de plataforma `end_call` y `transfer_call` para todos; se borran las marcas `[FIN]`, `[CORTAR]` y `[DERIVAR:]` y su parseo. |
| Apps por cliente | **Se quitan** (registro, herramientas MCP, vistas, outbox, jobs, operadores de WhatsApp, tablas en una migración, UI y `docs/APPS*.md`). `asistente_sugym` se **archiva**. |
| Confirmación de herramientas | **Sin confirmación de plataforma.** `confirm` solo agrega a la descripción que pida confirmación; el modelo decide. Se borran `is_yes`, lo pendiente y la ejecución por palabras clave. |
| Reglas de prompt de herramientas | Se borran las de comportamiento; queda solo la semántica del resultado (`ok`, `error`). |
| Fecha | No se inyecta. `{{now}}` y `{{today}}` quedan como variables para las reglas y la base de conocimiento del agente. |
| Duplicadas en un turno | Se borra el cache; protege el `Idempotency-Key`. |
| `messages.failed` | La dice la plataforma por el TTS, sin pasar por el modelo. |
| Tope por turno | Configurable por agente (`tool_settings.max_calls_per_turn`): al llegar, el turno termina con un error de plataforma, sin forzar al modelo a responder. |
| Tests | Solo LLM falso con respuestas grabadas. Lo que valida respuestas del modelo real (`tests/test_llm.py` y otros) sale de `make test` y pasa a evals. |
| `make e2e-tools` | LLM falso (determinista): prueba API, MCP, sandbox y la API falsa. Bloquea si se rompe el código. |
| `make eval-tools` | LLM real, siempre termina en 0 y deja el reporte. |
| Escenarios del eval | Vuelven los originales: el agente sin "no hace falta especialidad", "el viernes" en un turno. Quedan: consultar antes de reservar y `reserva_cancelada` sin exigir llamada (eran expectativas mal escritas). |
| SSRF | Transport propio con `httpcore.AsyncConnectionPool(network_backend=...)`, sin atributos privados de httpx. |
| `TOOLS_PRIVATE_HOSTS` | Sale de la configuración: solo lo setean los tests y el e2e en código. |
| Campos de `structured` | Se borran (`answered`, `next_objective`, `progress.asked`, `answered_empty`, `next_objective` de la API). |
| Versiones de herramientas | Historial: tabla `tool_versions` con cada revisión. |
| Alcance | Todo el repo: los parches anteriores se deciden caso por caso (sección siguiente). |
| Despliegue | Al terminar, con `make calls-active` antes de recrear. |
| Motor `assistant` y apps | Se quitan (código, tests, UI, MCP, migración 0033); `asistente_sugym` se archiva. "Tu propio agente" es una opción del agente (`external`), no un motor. |
| Página `/asistentes` de la landing | Se quita con sus links (menú, pie, 404); `render.yaml` la redirige a la home. |
| Agentes vigentes | Reciben las reglas generales (antes en el prompt) como versión nueva al desplegar: `make agent-rules APPLY=1`. |

## Parches anteriores (auditoría del 26-oct-2026)

| Caso | Decisión |
|---|---|
| Teléfono: recordatorio oculto en el turno del usuario (regex de 8+ dígitos) y "pedilo antes de despedirte" | Se borra todo: el teléfono es un dato más del agente. |
| Frases de comportamiento del prompt del motor ("no vuelvas a preguntar", "una pregunta por turno", "nunca inventes", "si ya te despediste…", "dos intentos antes de cortar por fuera de tema", "no lo vuelvas a intentar derivar") | Salen del código y van como Reglas en la plantilla y en los agentes de referencia (editables). |
| Texto para el TTS (números, fechas, emails en palabras; `VOICE_NOTE_RULES`, regla de la plantilla) | **Normalizador en código** entre el LLM y el TTS (números, horas, fechas, moneda, emails, códigos; por frase; español), con tests. Se borran las reglas de prompt de voz. |
| Extracción: rechazar un email que el usuario no dijo, convertir "arroba/punto", ver solo hasta el mensaje del usuario | Se borra todo: se guarda lo que extrae el modelo, con el tipo del campo. |
| Prompt de extracción | Solo la tarea (qué campos y su formato); se borran las reglas de comportamiento. |
| Resultado `incompleta` | Queda: regla de negocio. |
| Proveedores sin JSON guiado (sacar ``` y esquema en el prompt) | Se exige salida guiada: una conexión que no la soporta se rechaza al probarla. |
| Primer de idioma del STT | Queda como configuración del modelo de STT (`stt/`, `STT_PRIMER_WAV`). |
| Muestreo por familia, presupuestos de razonamiento, timeout con razonamiento | A configuración (`.env` / override del modelo). La compatibilidad de parámetros de Anthropic queda (es del proveedor). |
| Tiempos de fin de turno | A configuración; se borra el modo dictado (código muerto). |
| Voz obligatoria del TTS | Queda: protege el servicio. |
| "No se pregunta" en la descripción de un dato | Se borra (un dato que no se pregunta no lleva `question`). |
| Historial con una derivación (lo de la persona dentro de un mensaje del usuario) | Mensajes con su rol y el nombre de la persona; solo se juntan los seguidos del mismo rol. |
| Resumen de la derivación | Queda el respaldo "una consulta"; sale "sin datos inventados". |
| Comentario de `check_updates` ("se le informan al LLM") | Se corrige: no se informan. |

## Orden

1. Reglas en `AGENTS.md`.
2. Quitar `assistant` y las apps (código, migración, UI, MCP, tests, docs, compose y `deploy/boot.sh`).
3. Un solo motor: `engine` deja de existir (se lee), "Tu propio agente" es `external` en la definición, `end_call` y `transfer_call` nativos, sin marcas.
4. Herramientas sin parches (confirmación, reglas, fecha, duplicadas), `failed` por la plataforma, tope por turno, `tool_versions`, SSRF con API pública, `TOOLS_PRIVATE_HOSTS` fuera de la config.
5. Parches anteriores (tabla de arriba), normalizador de texto para el TTS y campos de `structured`.
6. Tests con LLM falso, `e2e-tools` con LLM falso, `eval-tools` que solo informa, escenarios originales.
7. Documentación y despliegue.

## Estado

Implementado y desplegado el 26-oct-2026:

- Migración 0033 probada contra el backup de las 03:30 (`make migrate-test`) y aplicada: `asistente_sugym`
  archivado, tablas de apps y operadores borradas, `tool_versions` creada.
- `APPS_PUBLIC_HOST` y `APPS_DEPLOY_TOKEN` sacados del `.env` (diff enmascarado, copia en `scratch/env.bak-limpieza`).
- `app` y `agent` recreados sin llamadas en curso (`make calls-active && make up-agent`).
- `make agent-rules APPLY=1`: los 11 agentes vigentes recibieron las 7 reglas generales como versión nueva; una
  segunda corrida no encuentra nada.
- Aperturas pregeneradas regeneradas con el normalizador (`atentina_comercial` v27, `erpwoosync_gaby` v18) y
  borradas las de versiones anteriores.
- Pruebas: 1273 tests de Python, 244 de la UI, `make e2e-tools` (API y MCP, con el sandbox) en verde.

Observado en producción (prueba por texto con `atentina_comercial`, LLM propio): al despedirse, el modelo no llamó
a `end_call` (la conversación quedó activa). Con las marcas, el cierre era `[FIN]` en el texto. No se corrige por
código (reglas de desarrollo): hay que medirlo con `make eval-llm` (cierre) y `make eval-tools`, y si el modelo no
cierra, decidir entre otro modelo o una regla más explícita en los agentes. Mientras tanto, una llamada termina
cuando corta la persona o por el tope de duración, y un chat de WhatsApp por la ventana de inactividad.

Pendiente:

- Re-medir con el LLM propio: `make eval-llm` (cierre con `end_call`, fuera de tema, datos) y `make eval-tools`;
  los números anteriores son con las marcas y las reglas de prompt que se quitaron.
- El contenedor `app-sugym-gestion` (repo `atentina-apps`) y la red `atentina-apps` quedaron sin uso: bajarlos es
  decisión aparte. La ruta `apps.` del túnel de Cloudflare la saca el usuario.
- Publicar la landing (sin `/asistentes`, con la redirección de `render.yaml`).
- `ToolVersionOut` sin el email de quien guardó cada revisión (la UI muestra el id).
