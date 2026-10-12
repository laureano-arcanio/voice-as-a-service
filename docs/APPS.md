# Apps por cliente y asistente (referencia)

Cómo funciona hoy la integración de Atentina con las apps de los clientes: contrato, motor
`assistant`, controles, configuración y puesta en marcha. El diseño, las decisiones y la historia de
las pruebas están en [`APPS_PLAN.md`](APPS_PLAN.md). El código de las apps está en el repo
`/home/laureano/atentina-apps`, con su `SPEC.md`; cada app tiene su `README.md`.

## Qué es

Un asistente personal por WhatsApp para el dueño de un negocio. Lo propio del negocio vive en una
**app**: un contenedor generado desde una plantilla, con su SQLite, su API, herramientas por MCP y
vistas web. Atentina pone el resto:
- el canal (texto, audio y archivos);
- el LLM y el bucle de herramientas;
- las confirmaciones y los controles;
- los links a las vistas, la entrega de mensajes y los avisos programados.

```text
dueño ──WhatsApp──► app (Atentina) ──MCP + HTTP (red interna atentina-apps)──► app-<slug>:8000
                     operador → agente assistant → herramientas de sus apps
dueño ◄── link ── apps.atentina.com.ar ── gateway (Atentina) ──► /views/<vista> de la app
```

## Piezas en Atentina

| Pieza | Código | Qué hace |
|---|---|---|
| Registro | `app/apps/registry.py`, `POST /api/v1/apps` | Pide `/health` y `/manifest` con el `APP_TOKEN`, valida el contrato y guarda la app (token cifrado con `WA_TOKEN_KEY`). Chequeo de salud cada 60 s |
| Cliente | `app/apps/client.py` | MCP mínimo sin SDK (JSON-RPC por POST a `/mcp`, `initialize` y respuesta JSON o SSE) y GET/POST HTTP. Todo con `Authorization: Bearer <APP_TOKEN>` y `X-Atentina-Actor` |
| Catálogo | `app/apps/tools.py` | Las herramientas de las apps del cliente que lista `tools` del agente (`$ref` resueltos, `anyOf` con null aplanados) más `abrir_vista`, una por app |
| Motor `assistant` | `app/conversation/assistant.py` | El bucle de pasos con sus controles (abajo) |
| Operadores | `wa_operators`, `app/whatsapp/service.py` | Por un número compartido, el `wa_id` del dueño va a su agente y su cliente |
| Archivos | `app/apps/attachments.py` | Imagen o PDF del operador → OCR (tesseract `spa`, CPU) → `[archivo recibido · sha256 …]` + texto |
| Links y gateway | `app/apps/links.py`, `app/apps/gateway.py` | Link firmado a una vista; `apps.atentina.com.ar` atiende solo el gateway |
| Outbox | `app/apps/outbox.py` | Entrega lo que devuelve una herramienta `send` ya confirmada y avisa a la app |
| Jobs | `app/apps/jobs.py`, `app_job_runs` | Corre los avisos del manifest a su hora, una vez por día, y los manda a los operadores |

## Contrato con la app (v1.1)

| Ruta de la app | Para qué |
|---|---|
| `GET /health`, `GET /manifest` | Registro y salud. El manifest trae `views`, `tools` (con `kind` e `input_schema`) y `jobs` |
| `POST /mcp` | Herramientas (Streamable HTTP, sin estado) |
| `GET /views/<vista>?…&formato=csv` | Vistas HTML o CSV, con `X-Forwarded-Prefix` |
| `POST /outbox/<ref>` | Resultado de la entrega de un mensaje (`enviado`, `simulado`, `error`) |
| `POST /jobs/<name>` | Corre un aviso: `{"message", "view"}` |

- **`kind` de cada herramienta:**
  - `read`: consulta;
  - `write`: registra;
  - `destructive`: se confirma antes;
  - `send`: llega a terceros y se confirma antes.
- **Convenciones en los resultados:**
  - `"ambiguo": true` cuando no está claro de quién se habla;
  - `outbox: [...]` en una herramienta `send`;
  - los ids se llaman `*_id`.
- Hasta 20 herramientas por app y 400 caracteres por descripción. Las descripciones van en cada paso
  al LLM.

## Motor `assistant`

Un agente con `engine: "assistant"` y `tools: [{"app": "<slug>", "tools": ["*"]}]` no extrae datos:
usa herramientas. Cada turno:

1. **El prompt** lleva:
   - las reglas del asistente, la fecha y hora (`ASSISTANT_TIMEZONE`) y las herramientas;
   - los últimos 16 mensajes;
   - en la respuesta anterior, los resultados de sus herramientas (si no, el LLM inventaba los ids al
     seguir el pedido).
2. **Cada paso** es un pedido al LLM con JSON guiado. La respuesta es una de:
   - `reply`: responde y termina el turno;
   - `call`: una herramienta, con argumentos según su esquema;
   - `confirm` o `cancel`: lo que quedó pendiente.

   Hay hasta 6 pasos. No usa el tool calling nativo de vLLM.
3. **Razonamiento:** prendido (`ASSISTANT_THINKING`), con tope de 512 tokens y 2048 por paso.
   - Medido con Gemma 4, 12-oct-2026: de 0,5 a ~2,2 s por paso, y una mediana de 2,7–3,4 s por turno
     (1,5 s sin razonamiento).
   - Las llamadas de voz no razonan (`LLM_THINKING`).
4. **Confirmación:** una herramienta `destructive` o `send` no se ejecuta; queda en
   `progress.pending` y el asistente pregunta.
   - En el turno siguiente, un sí claro ("sí", "dale, mandalo", "confirmo") la ejecuta la plataforma
     sin pasar por el LLM, y un no claro la cancela.
   - Con otra respuesta, decide el LLM.
   - Lo pendiente vale un solo turno.
5. **Respuesta** siempre en texto, aunque el usuario mande audio: listados y links no van en una nota
   de voz.

### Controles de la plataforma

Cada uno salió de un error real con Gemma 4 (casos de uso de SUGYM, 12-oct-2026). El prompt solo no
alcanzaba.

| Control | Qué evita |
|---|---|
| Un `*_id` en una herramienta que escribe tiene que haber salido de un resultado | Dar de baja a otra persona con un id inventado |
| Después de una consulta con `"ambiguo": true`, nada escribe en ese turno | "Vino Juan" registraba a Juan Pérez, o a los dos Juanes |
| Un valor que es el nombre de un campo (`"alumno": "alumno_id"`) no se ejecuta | Errores de la temperatura 1.0 |
| El link de una vista lo pone el sistema: el LLM ve `[[linkN]]`; una marca sin vista pedida no sale | Tokens copiados con un carácter de menos; `[[link1]]` literal |
| Un link que no salió de una herramienta no sale | Links inventados |
| La misma herramienta con los mismos argumentos no se repite; después de una repetición, y en el último paso, solo puede responder | Quedarse sin pasos y contestar "no pude completar eso" |
| Una salida que no es JSON se reintenta una vez | JSON cortado por el tope de tokens |

## Configuración (`.env`)

| Variable | Default | Qué es |
|---|---|---|
| `APPS_PUBLIC_HOST` | vacío | Host del gateway (`apps.atentina.com.ar`); vacío = sin vistas |
| `APPS_DEPLOY_TOKEN` | vacío | Lo usa `make register` de atentina-apps; solo registra y relee apps |
| `APPS_LINK_TTL_DAYS` | 7 | Vida de un link |
| `APPS_OUTBOX_MODE` | `simulate` | `simulate` no manda nada; `whatsapp` manda por el número del chat (fuera de la ventana de 24 h, Meta lo rechaza) |
| `APPS_HTTP_TIMEOUT`, `APPS_HEALTH_SECONDS`, `APPS_JOBS_SECONDS` | 15, 60, 60 | |
| `ASSISTANT_THINKING`, `ASSISTANT_THINKING_BUDGET`, `ASSISTANT_MAX_STEP_TOKENS` | `true`, 512, 2048 | Razonamiento del motor `assistant` |
| `ASSISTANT_MAX_STEPS`, `ASSISTANT_HISTORY_MESSAGES`, `ASSISTANT_TIMEZONE` | 6, 16, Argentina | |
| `LLM_SAMPLING` | `auto` | Sampling recomendado según el modelo: Gemma 4 1.0 / 0.95 / 64 (model card); Qwen como antes |

`WA_TOKEN_KEY` es obligatoria para registrar apps (cifra el `APP_TOKEN`). La red `atentina-apps` la
crean `make apps-network` y `deploy/boot.sh`; sin ella `app` no arranca.

## Poner una app en marcha

1. **Atentina:**
   - `.env` con `APPS_PUBLIC_HOST` y `APPS_DEPLOY_TOKEN` (diff enmascarado antes de reiniciar);
   - `make up-app`;
   - la ruta del túnel `apps.<dominio>` → `http://localhost:8011`.
2. **atentina-apps:**
   - `.env` con `ATENTINA_URL=http://127.0.0.1:8011` y `ATENTINA_DEPLOY_TOKEN` (igual a
     `APPS_DEPLOY_TOKEN`);
   - `make deploy A=<cliente>/<app>` (o `make dev` con datos de prueba, y después `make register`).
3. **En el panel:**
   - **Apps:** asignarla al cliente;
   - **Agentes:** motor Asistente, y la app en **Herramientas**;
   - **WhatsApp → Operadores:** el número compartido, el `wa_id` del dueño y ese agente. El número
     sigue con su agente para todos los demás.
4. **Probar:** `make casos A=<cliente>/<app>` desde atentina-apps (casos de uso contra el asistente
   real) y después por WhatsApp.

## Pruebas

- `tests/test_apps.py`: registro, catálogo, motor, controles, gateway, outbox, jobs, archivos y
  operadores (la app se simula).
- Casos de uso de punta a punta: el runner es `scripts/apps/casos.py`; los casos son de cada app
  (`clients/<c>/<app>/casos/casos.yaml` en atentina-apps). Lo lanza `make casos`, con una copia
  descartable de la app y el código de Atentina del working tree.
  - SUGYM, 12-oct-2026: 46 casos, entre 44 y 46 por corrida con razonamiento.
  - Cada error que encuentra un usuario entra como caso.

## Pendiente

- **Plantillas de WhatsApp,** para avisos y mensajes fuera de la ventana de 24 h. Hoy el outbox está
  simulado y el aviso diario solo llega si el operador escribió en las últimas 24 h.
- **El eval con razonamiento repetido (N=5),** con audios reales y comprobantes fotografiados.
- **Desplegar lo último de esta tanda** (razonamiento, controles y vista de pagos): hace falta
  `make up-app`.
