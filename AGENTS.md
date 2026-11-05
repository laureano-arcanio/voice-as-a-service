# AGENTS.md

Atentina: agentes de voz (teléfono, web y WhatsApp) con **inferencia propia**: LLM, STT y TTS corren en GPUs
locales. Plataforma multi-cliente (clientes, tiers, agentes versionados en JSON, números) con API `/api/v1`,
UI React en `web/`, worker de voz LiveKit y MCP. En producción desde el 28-oct-2026. **Producción: server2 (192.168.1.98), siempre en `main`.**
El host `192.168.1.99`, donde se trabaja con el repo, es el **entorno de desarrollo** ([`docs/DESARROLLO.md`](docs/DESARROLLO.md)); sus tres modelos no reciben producción: server2 atiende solo ([`docs/INFRA.md`](docs/INFRA.md)).

## Dónde está cada cosa

| Tema | Doc |
|---|---|
| Qué es, levantar, claves de `.env` | [`README.md`](README.md) |
| Entorno de desarrollo y deploy | [`docs/DESARROLLO.md`](docs/DESARROLLO.md) |
| Arquitectura: componentes, código, modelo de datos, definición del agente, flujos, planes, auth, API | [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) |
| Infraestructura: host, GPUs, servicios del compose, reglas de inferencia, backup, límites para escalar | [`docs/INFRA.md`](docs/INFRA.md) |
| Cada función de la plataforma (modelo, API, flujo, trampas, cómo desplegar, pendientes) | [`docs/features/`](docs/features/) |
| Cómo se usa la UI | [`docs/GUIA_UI.md`](docs/GUIA_UI.md) |
| API de inferencia para clientes | [`docs/API_INFERENCIA.md`](docs/API_INFERENCIA.md) |
| Telefonía (Anura ↔ Asterisk ↔ LiveKit) | [`docs/TELEFONIA_ANURA.md`](docs/TELEFONIA_ANURA.md) |
| Monitoreo y alertas | [`docs/OBSERVABILIDAD.md`](docs/OBSERVABILIDAD.md) |
| Server nuevo o migración | [`docs/MIGRACION_SERVER.md`](docs/MIGRACION_SERVER.md) |
| Capacidad, evals, benchmark de GPU | [`docs/capacity/`](docs/capacity/README.md), [`docs/eval/`](docs/eval/README.md), [`docs/gpubench/`](docs/gpubench/README.md) |
| Voces del TTS | [`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md) |
| Diseño: landing / dashboard | [`docs/DESIGN_GUIDELINE.md`](docs/DESIGN_GUIDELINE.md) / [`docs/DESIGN_GUIDELINE_APP.md`](docs/DESIGN_GUIDELINE_APP.md) |
| Comercial (mercado, prospectos, competencia) y marketing (videos, PDFs) | [`comercial/`](comercial/), [`marketing/`](marketing/README.md) |

Docs de features en `docs/features/`: [`WHATSAPP`](docs/features/WHATSAPP.md), [`META_APP_REVIEW`](docs/features/META_APP_REVIEW.md),
[`CAMPANAS`](docs/features/CAMPANAS.md), [`EQUIPO_TELEFONIA`](docs/features/EQUIPO_TELEFONIA.md) (derivaciones y llamadas
directas), [`LINK_LLAMADA`](docs/features/LINK_LLAMADA.md), [`HERRAMIENTAS`](docs/features/HERRAMIENTAS.md),
[`LLM_CONEXIONES`](docs/features/LLM_CONEXIONES.md) (BYOK y tu propio agente), [`MCP`](docs/features/MCP.md),
[`REPORTES`](docs/features/REPORTES.md), [`LLM_REPLICAS`](docs/features/LLM_REPLICAS.md) (segundo server y
balanceo del LLM), [`COBROS`](docs/features/COBROS.md), [`LEGAL`](docs/features/LEGAL.md),
[`LANDING`](docs/features/LANDING.md), [`ESTUDIO`](docs/features/ESTUDIO.md) (texto a voz y transcripción), [`PRIMERA_VEZ`](docs/features/PRIMERA_VEZ.md) (asistente de primera vez,
Inicio y llamada de prueba al celular), [`CRM`](docs/features/CRM.md) y [`CRM_API`](docs/features/CRM_API.md).

Cada doc dice su estado y sus pendientes; este archivo no repite estados. Al cambiar una función, se actualiza su
doc (y ARQUITECTURA si cambia el modelo o la API) en el mismo commit.

## Ciclo de desarrollo

Todo cambio de código o de configuración versionada (`app/`, `web/`, `landing/`, `migrations/`, `stt/`, `crm/`, `tools-runner/`, `deploy/`,
`asterisk/`, compose, `Makefile`) sigue este orden. La **sesión principal orquesta**: lanza cada agente, guarda el plan en
`scratch/planes/<slug>.md` y le pasa esa ruta a los siguientes; no implementa por su cuenta.

1. [`technical-leader`](.claude/agents/technical-leader.md): analiza, clasifica y devuelve el plan con sus tareas. No modifica nada. Si trae decisiones para el usuario, se le preguntan antes de seguir.
2. [`validador`](.claude/agents/validador.md): ataca el plan contra el código. No modifica nada. Si el veredicto es `CAMBIOS` o `RECHAZADO`, vuelve al paso 1 con las objeciones (hasta 2 vueltas; después decide el usuario).
3. [`desarrollador`](.claude/agents/desarrollador.md): una instancia por tarea, con el `model` del nivel de esa tarea. En paralelo solo lo que el plan marca como paralelo.
4. [`qa`](.claude/agents/qa.md): verifica en el entorno local, en el navegador si hay UI; si no, por API, MCP o código. Si `FALLA`, vuelve al paso 3 con los detalles técnicos y QA repite (hasta 3 vueltas; después decide el usuario). Si la falla es del diseño, vuelve al paso 1. A la segunda falla de una tarea, sube un modelo.
5. [`documentador`](.claude/agents/documentador.md): actualiza lo que ya existe y crea un doc solo si hace falta.

Commit y deploy siguen siendo pedidos del usuario, con la documentación en el mismo commit.

**Saltear el análisis:** solo si el usuario lo autoriza de forma explícita para ese pedido ("sin plan", "directo a desarrollo"). No se
infiere de la urgencia ni del tamaño, y no vale para el pedido siguiente. Se pasa al paso 3 con el modelo del nivel que calcule la sesión
principal; QA y documentación siguen, salvo que también los excluya.

**Fuera del ciclo:** preguntas e investigación; cambios que son solo docs o que no tocan el producto (`comercial/`, `marketing/`); y el trabajo
de los agentes `deploy`, `server2`, `ventas`, `videos`, `documentos` y `tts-finetune`; tests de capacidad y evals.

### Clasificación por impacto

Gana el nivel más alto de cualquier fila, no el promedio. En la duda, el de arriba. El nivel de cada tarea se calcula igual; el del plan es el de su tarea más alta.

| Factor | Nivel 1 | Nivel 2 | Nivel 3 |
|---|---|---|---|
| Alcance | Un área, pocos archivos, sin decisiones de diseño | Varias capas de una función (API + UI) | Varios componentes, o una pieza que usan muchas funciones |
| Datos | Sin cambio de esquema | Migración que solo agrega | Migración que transforma o borra datos existentes |
| Contratos (API, MCP, definición del agente) | Sin cambios | Agrega, compatible | Cambia o quita algo que ya se usa |
| Seguridad y clientes | No toca | Permisos o tier de una función | Login, sesión, CSRF/CSP, SSRF, sandbox, secretos, aislamiento entre clientes |
| Plata | No toca | Muestra importes o consumos | Cobros, reserva o descuento de minutos |
| Voz | No toca | Worker, fuera de la llamada en vivo | Camino de la llamada: `app/voice/`, STT, TTS, LLM, Asterisk, LiveKit, compose, GPU |
| Vuelta atrás | `git revert` y deploy | `git revert` y deploy, en orden | No alcanza con un revert |

| Nivel | Modelo del desarrollador | Validador | QA |
|---|---|---|---|
| 1 | `haiku` si es mecánica y está especificada; si no, `sonnet` | `sonnet`, revisión breve | Lo pedido y los tests |
| 2 | `sonnet` | `opus` | Criterios del plan y lo cercano que pudo romperse |
| 3 | `opus` | `opus`, completa | Además, intentar romperlo: otro cliente, otro tier, concurrencia |

El modelo se pasa en el parámetro `model` de cada lanzamiento. El `technical-leader` siempre corre en `opus`, porque clasifica antes de que se conozca el nivel.

## Pedidos frecuentes

| Pedido | Qué hacer |
|---|---|
| Test de capacidad ("registralo") | [`docs/capacity/README.md`](docs/capacity/README.md): límites de GPU, `make capacity-monitor PERFIL=<perfil>` antes de la carga, el usuario corre `make capacity` en la laptop, después `make capacity-monitor-stop`, `make capacity-analyze` y registrar `docs/capacity/CAP-NNN-<slug>/`. |
| Probar otro modelo o reparto de GPU | Override `docker-compose.<nombre>.yml` ([`docs/INFRA.md`](docs/INFRA.md)); confirmar antes de reiniciar; medir con capacidad y eval. |
| Evaluar un LLM | [`docs/eval/README.md`](docs/eval/README.md): `make eval-llm`, `make eval-llm-juez`, registrar `docs/eval/EVAL-NNN-<slug>/`. |
| Entrenar una voz del TTS | Agente [`tts-finetune`](.claude/agents/tts-finetune.md) ([`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md)). El 1.7B necesita parar `vllm-tts`: confirmar antes. |
| Crear cliente, tier, agente o número | Por la UI o la API (`/api/v1`, OpenAPI en `/api/v1/docs`). Los agentes de la landing y del número propio son del cliente `atentina`; el admin los edita entrando como el cliente. |
| Consultar o editar la base de producción | Permitido, **en server2**: `ssh server2`, `cd voice-as-a-service`, `make psql`, o `docker exec -i voice-as-a-service-db-1 sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'` para scripts. |
| Admin / "ver como cliente" | [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md), "Soporte del admin": `/admin/*`, header `X-Atentina-Client`, 403 `support_read_only` en cuenta, plan y cobros. |
| Una función: texto a voz o transcripción, WhatsApp, campañas, derivaciones, llamadas directas, link para llamar, herramientas, BYOK, MCP, reportes, cobros, términos, landing | Su doc en [`docs/features/`](docs/features/). |
| Cambiar la UI del dashboard | React + Mantine en `web/` (`make web-check`), [`docs/DESIGN_GUIDELINE_APP.md`](docs/DESIGN_GUIDELINE_APP.md). Lo nuevo se resuelve en `web/src/theme.ts` y `web/src/components/`. |
| Cambiar la landing | Astro + Tailwind en `landing/` ([`docs/features/LANDING.md`](docs/features/LANDING.md)), [`docs/DESIGN_GUIDELINE.md`](docs/DESIGN_GUIDELINE.md). |
| Monitoreo, alertas, "¿por qué hubo un pico?" | [`docs/OBSERVABILIDAD.md`](docs/OBSERVABILIDAD.md): pantalla Sistema del admin, `make monitoring-status`, reglas en `deploy/monitoring/rules.yml` (anotar el porqué de cada umbral). |
| Server nuevo o migración | [`docs/MIGRACION_SERVER.md`](docs/MIGRACION_SERVER.md), en orden. Nunca dos Asterisk ni dos `cloudflared` a la vez. |
| Réplica de inferencia, balanceador, "¿qué réplica atiende?" | [`docs/features/LLM_REPLICAS.md`](docs/features/LLM_REPLICAS.md): en server2, `make llm-lb-status`, `make up-llm-lb` (recrea y se niega con llamadas en curso; ventana y usuarios que no cubre en el doc). |
| Función, bug o cambio de código | [Ciclo de desarrollo](#ciclo-de-desarrollo): `technical-leader` → `validador` → `desarrollador` → `qa` → `documentador`. |
| Probar un cambio | Entorno local: `make dev-up`, http://192.168.1.99:8211 ([`docs/DESARROLLO.md`](docs/DESARROLLO.md)). |
| Desplegar a producción | Agente [`deploy`](.claude/agents/deploy.md), solo desde `main` y después de probar en local. `make deploy-status` muestra lo pendiente. |
| Operar el server principal (server2, 192.168.1.98), salvo deploys | Agente [`server2`](.claude/agents/server2.md): SSH por clave como `atentina-ops`, `sudo -n`. Es producción. Para el usuario, `make server2-ssh CMD='...'`. |
| Prospectos, mails, seguimiento | Agente [`ventas`](.claude/agents/ventas.md); el registro es el CRM ([`docs/features/CRM_API.md`](docs/features/CRM_API.md), `make crm-up`). Propuesta con PDF y video: skill [`propuesta-prospecto`](.claude/skills/propuesta-prospecto/SKILL.md). |
| Video o PDF | Agentes [`videos`](.claude/agents/videos.md) ([`marketing/VIDEOS.md`](marketing/VIDEOS.md)) y [`documentos`](.claude/agents/documentos.md) ([`marketing/DOCUMENTOS.md`](marketing/DOCUMENTOS.md)). |

## Reglas de desarrollo

- **Sin parches de modelo.** No se corrige por código ni por prompt lo que un modelo (LLM, STT o TTS) hace mal: nada
  de listas de palabras para interpretar respuestas, reintentos o filtros sobre la salida del modelo, ni reglas de
  prompt nacidas de una falla medida. Si un modelo falla, se reporta (eval), se prueba otro modelo o lo resuelve el
  cliente en la definición de su agente. Sí son de la plataforma: el protocolo (herramientas y su resultado), los
  límites de recursos (topes, timeouts), la seguridad (SSRF, secretos, sandbox) y el formato del canal (normalizar
  el texto para el TTS).
- **El prompt del motor solo lleva la definición del agente y el protocolo.** Las instrucciones de comportamiento
  van en la plantilla (`app/agents/templates/asistente.json`, `GENERIC_RULES`) y en los agentes de referencia
  (`app/agents/reference/`), a la vista y editables. Nada de un cliente en el código.
- **Tests sin modelo real.** `make test` usa un LLM falso con respuestas grabadas; ningún test depende de un servicio
  real ni valida lo que contesta un modelo.
- **Los evals informan, no bloquean.** Terminan en 0. Los escenarios no se ajustan para que pase un modelo; una
  expectativa se corrige solo si estaba mal escrita, y se anota por qué.
- **Sin acople a un modelo.** El código funciona con cualquier modelo compatible (API de OpenAI o Anthropic con
  `tools` y salida JSON guiada). Lo propio de un modelo (muestreo, razonamiento, parser de herramientas, primer del
  STT) vive en su configuración (`.env`, override de compose, `stt/`).
- **Esquema por migraciones** (`migrations/`, `make migrate`; antes de una migración nueva, `make migrate-test`).
  Los agentes viven en la base, versionados.
- **Todo cambio de modelo, reparto de GPU, flags de memoria o hardware se mide** con el test de capacidad y se
  registra en `docs/capacity/`. Los comentarios del compose explican el porqué medido de cada flag: mantenerlos al día.

## Cómo trabajar en este server

- **Todo desarrollo se prueba primero en el entorno local** (`make dev-up`) y llega a producción solo por `main` y el agente
  `deploy`. Nunca se edita código en server2.
- El stack de producción está **en server2**; `make up*` se niega en este host (`STACK_ROLE=replica`) y, en server2, fuera de `main`
  o con cambios locales. Puede haber otras
  sesiones de agente en el repo y en los contenedores: mirar `git status` y `docker ps` antes de cambiar algo, y no revertir
  cambios ajenos.
- No reiniciar servicios ni lanzar pruebas que nadie pidió. Antes de recrear algo que corta llamadas:
  `make calls-active` (falla si hay alguna). Ej.: `make calls-active && make up-agent`.
- **Comandos para el usuario, siempre con `make`.** Si un paso no tiene target, se agrega al `Makefile` con
  `## descripción`.
- Al editar `.env`: diff enmascarado contra un backup antes de reiniciar.
- Archivos temporales (audios, scripts de prueba, descargas, clones): en `scratch/` del repo, nunca en `/tmp`.
- Docs y comentarios en español, breves y con datos medidos. Sin historia en los docs: lo que se quita, se borra
  (queda en git).

## Trampas que rompen producción

Detalle y resto en [`docs/INFRA.md`](docs/INFRA.md).

- **Pedido al TTS sin `voice` o con `voice="default"` mata el engine de `vllm-tts`** (todo da 500 hasta reiniciarlo).
  Mandar siempre una voz del checkpoint (`multi41`, catálogo en `tts/finetune/voces.tsv`).
- **El nombre del modelo** en `VLLM_LLM_MODEL` tiene que coincidir entre `vllm-llm` y `app`/`agent`: al cambiarlo,
  recrear los tres. El parser de herramientas de `vllm-llm` tiene que ser el del modelo, o todo agente da 400.
- **TTS no comparte GPU con el LLM ni con otra réplica.** `--gpu-memory-utilization` es fracción de la memoria total;
  los que comparten GPU no arrancan a la vez (`depends_on` los encadena).
- **La 3090 de .99 tiene tope de 280 W** (`atentina-gpu-limits.service`): sin tope, un pico apagó ese server. La de
  server2 va a 350 W por decisión del usuario (`GPU_SIN_TOPE=1`), con el pico bajo carga sin medir.
- **Redis de LiveKit no persiste**: tras reiniciar el host, `make livekit-sip` (lo hace `make up` y el arranque).
- **DTMF `*` en Anura corta otra llamada activa de la cuenta**: los códigos para personas van con `#`.
- **`/api/v1/demo` es la única parte pública sin login**; el dashboard (`app.atentina.com.ar`) se defiende solo
  (sesión revocable, CSRF por `Origin`, CSP con hash): no relajar CSP, `APP_ORIGINS` ni `TRUSTED_PROXY_CIDRS` sin
  medir con `CSP_REPORT_ONLY=true`.
- **Al cambiar un tier, un reporte o el MCP**, actualizar `/desarrolladores/docs/api` y `/docs/mcp` de la landing
  (`make mcp-docs` regenera el catálogo).
