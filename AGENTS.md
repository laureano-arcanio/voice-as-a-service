# AGENTS.md

Atentina: agentes de voz (teléfono, web y WhatsApp) con **inferencia propia**: LLM, STT y TTS corren en GPUs
locales. Plataforma multi-cliente (clientes, tiers, agentes versionados en JSON, números) con API `/api/v1`,
UI React en `web/`, worker de voz LiveKit y MCP. En producción desde el 28-oct-2026, en un solo server.

## Dónde está cada cosa

| Tema | Doc |
|---|---|
| Qué es, levantar, claves de `.env` | [`README.md`](README.md) |
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
[`REPORTES`](docs/features/REPORTES.md), [`COBROS`](docs/features/COBROS.md), [`LEGAL`](docs/features/LEGAL.md),
[`LANDING`](docs/features/LANDING.md), [`CRM`](docs/features/CRM.md) y [`CRM_API`](docs/features/CRM_API.md).

Cada doc dice su estado y sus pendientes; este archivo no repite estados. Al cambiar una función, se actualiza su
doc (y ARQUITECTURA si cambia el modelo o la API) en el mismo commit.

## Pedidos frecuentes

| Pedido | Qué hacer |
|---|---|
| Test de capacidad ("registralo") | [`docs/capacity/README.md`](docs/capacity/README.md): límites de GPU, `make capacity-monitor PERFIL=<perfil>` antes de la carga, el usuario corre `make capacity` en la laptop, después `make capacity-monitor-stop`, `make capacity-analyze` y registrar `docs/capacity/CAP-NNN-<slug>/`. |
| Probar otro modelo o reparto de GPU | Override `docker-compose.<nombre>.yml` ([`docs/INFRA.md`](docs/INFRA.md)); confirmar antes de reiniciar; medir con capacidad y eval. |
| Evaluar un LLM | [`docs/eval/README.md`](docs/eval/README.md): `make eval-llm`, `make eval-llm-juez`, registrar `docs/eval/EVAL-NNN-<slug>/`. |
| Entrenar una voz del TTS | Agente [`tts-finetune`](.claude/agents/tts-finetune.md) ([`docs/TTS_FINETUNE.md`](docs/TTS_FINETUNE.md)). El 1.7B necesita parar `vllm-tts`: confirmar antes. |
| Crear cliente, tier, agente o número | Por la UI o la API (`/api/v1`, OpenAPI en `/api/v1/docs`), nunca a mano en la base. Los agentes de la landing y del número propio son del cliente `atentina`; el admin los edita entrando como el cliente. |
| Admin / "ver como cliente" | [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md), "Soporte del admin": `/admin/*`, header `X-Atentina-Client`, 403 `support_read_only` en cuenta, plan y cobros. |
| Una función: WhatsApp, campañas, derivaciones, llamadas directas, link para llamar, herramientas, BYOK, MCP, reportes, cobros, términos, landing | Su doc en [`docs/features/`](docs/features/). |
| Cambiar la UI del dashboard | React + Mantine en `web/` (`make web-check`), [`docs/DESIGN_GUIDELINE_APP.md`](docs/DESIGN_GUIDELINE_APP.md). Lo nuevo se resuelve en `web/src/theme.ts` y `web/src/components/`. |
| Cambiar la landing | Astro + Tailwind en `landing/` ([`docs/features/LANDING.md`](docs/features/LANDING.md)), [`docs/DESIGN_GUIDELINE.md`](docs/DESIGN_GUIDELINE.md). |
| Monitoreo, alertas, "¿por qué hubo un pico?" | [`docs/OBSERVABILIDAD.md`](docs/OBSERVABILIDAD.md): pantalla Sistema del admin, `make monitoring-status`, reglas en `deploy/monitoring/rules.yml` (anotar el porqué de cada umbral). |
| Server nuevo o migración | [`docs/MIGRACION_SERVER.md`](docs/MIGRACION_SERVER.md), en orden. Nunca dos Asterisk ni dos `cloudflared` a la vez. |
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

- El stack está en producción y puede haber otras sesiones de agente en el repo y en los contenedores: mirar
  `git status` y `docker ps` antes de cambiar algo, y no revertir cambios ajenos.
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
- **Las 3090 tienen tope de 280 W** (`atentina-gpu-limits.service`): sin tope, un pico apagó el server.
- **Redis de LiveKit no persiste**: tras reiniciar el host, `make livekit-sip` (lo hace `make up` y el arranque).
- **DTMF `*` en Anura corta otra llamada activa de la cuenta**: los códigos para personas van con `#`.
- **`/api/v1/demo` es la única parte pública sin login**; el dashboard (`app.atentina.com.ar`) se defiende solo
  (sesión revocable, CSRF por `Origin`, CSP con hash): no relajar CSP, `APP_ORIGINS` ni `TRUSTED_PROXY_CIDRS` sin
  medir con `CSP_REPORT_ONLY=true`.
- **Al cambiar un tier, un reporte o el MCP**, actualizar `/desarrolladores/docs/api` y `/docs/mcp` de la landing
  (`make mcp-docs` regenera el catálogo).
