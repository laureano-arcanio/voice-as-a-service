# Respuesta a la revisión de producción del 7-oct-2026

Respuesta a [`revision-produccion-2026-10-07.html`](revision-produccion-2026-10-07.html) (commit
auditado `3fc800b`). Fecha: 8-oct-2026.

**Resumen:**
- Los 14 hallazgos y los 7 casos extra se verificaron contra el árbol: todos son reales.
- **Decisión del usuario:** salir a producción multi-cliente abierta e implementarlos todos, P1 y P2.
- **Estado:** implementado en el árbol, **sin commit y sin desplegar**. El despliegue (migración 0009,
  rebuild, recrear, `make livekit-sip`, recargar Asterisk) lo decide y lo corre el usuario; pasos en
  [`PRODUCCION.md`](PRODUCCION.md), 3.1.
- **Pruebas:**
  - `.venv/bin/python -m pytest -q` (SQLite): 480 pasan, 13 se saltean (piden vLLM o `TEST_DB_DSN`).
  - En un PostgreSQL 16 desechable (`TEST_DB_DSN`): la suite entera (476) antes de las últimas
    correcciones, y los 43 tests de los archivos tocados después.
  - `make web-check`: 81 tests.
- **Requiere al usuario:** alertas, copia externa, `.env` de seguridad, el router, el CAP con Gemma y
  WhatsApp Calling para terceros (sección final).

Abreviaturas de la tabla de cada hallazgo: **Veredicto** (lo verificado, con matices), **Decisión**,
**Hecho** (qué se implementó y dónde), **Comprobado** (cómo) y **Falta**.

## H01 (P1): un número puede quedar con el agente de otro cliente

- **Veredicto:** confirmado.
  - El PATCH leía sin lock y `set_agent` comparaba contra el objeto en memoria.
  - `release` no tomaba lock.
  - La entrante no comparaba el cliente del agente con el del número.
  - La base solo tenía `ck_phone_numbers_agent_needs_client`.
- **Decisión:** cerrarlo en la app y en la base.
- **Hecho:**
  - `services/phone_numbers.lock()` bloquea el cliente y después el número (el mismo orden que
    `assign`) y relee.
  - El PATCH y `release` lo usan: si el número cambió de cliente, 409 `number_changed`, y si el que
    pide ya no tiene acceso, 404.
  - FK compuesta `phone_numbers(agent_id, client_id)` → `agents(id, client_id)` en la 0009. La
    migración se niega a correr si ya hay números cruzados.
  - La entrante con un agente de otro cliente se corta: `number_agent_mismatch`.
  - Archivos: `app/services/phone_numbers.py`, `app/api/routers/phone_numbers.py`,
    `app/services/calls.py` y `migrations/versions/0009_produccion.py`.
- **Comprobado:**
  - `tests/test_prod_aislamiento.py`: intercalado con dos sesiones.
  - `tests/test_prod_postgres.py`, en PostgreSQL:
    - el PATCH espera al release del admin y después ve el cambio;
    - la FK rechaza el cruce, por ORM y por SQL;
    - un release que esperó a un assign da `number_changed`.
  - `make restore-test` con el dump de producción del 8-oct: la 0009 migró sin números cruzados.
- **Falta:** desplegar.

## H02 (P1): las entrantes no respetan la duración máxima

- **Veredicto:** confirmado.
  - El temporizador estaba solo en la rama de prueba y loadtest.
  - El watchdog no atrapaba errores de base.
  - Pasados 900 + 600 s, una llamada dejaba de contar para la concurrencia y para los minutos.
  - El trunk entrante y Asterisk no tenían tope.
  - Matiz: si el worker caía sin finalizar, la fila quedaba `en_curso` para siempre y sumaba 0.
- **Decisión:** tope duro **por tier** (`tiers.max_call_duration_seconds`; vacío = 900 s), en todas
  las modalidades, también en los tiers ilimitados y en la línea de Atentina.
- **Hecho:**
  - Vigilante único `guard_call` en `app/voice/worker.py`. Corta al menor entre el tope del tier, el
    del pedido y los minutos que quedan; un error de base se registra y se reintenta.
  - La saliente sale con `max_call_duration` = tope + 30 s.
  - Techo de plataforma `CALL_DURATION_CEILING_SECONDS` (3600 s), aplicado en tres lugares:
    - el trunk entrante de LiveKit (`max_call_duration`, `scripts/livekit_sip_setup.py`);
    - Asterisk (`L()` en los tres `Dial`, `asterisk/conf/extensions.conf`);
    - el chequeo `livekit_sip_setup --check`, que da error si el trunk no lo tiene.
  - Una llamada vencida sin finalizar sigue consumiendo hasta el tope (`app/services/quota.py`).
  - Conciliación nueva, `app/services/reconcile.py`, en el líder: cierra las activas cuya room ya no
    existe (`room_gone`) y, si LiveKit no responde, no toca nada.
- **Comprobado:** `tests/test_prod_llamadas.py` (19 tests):
  - una entrante en un tier ilimitado se corta al tope;
  - el vigilante sobrevive a un error de base;
  - una vencida sigue contando;
  - la conciliación funciona con LiveKit simulado, también caído.
- **Falta:**
  - Desplegar, `make livekit-sip` y `make up-pbx` (el dialplan nuevo no está cargado).
  - Una entrante y una saliente reales.
  - Matar `agent` en una llamada de prueba y ver `room_gone`.

## H03 (P1): WhatsApp confirma mensajes que puede perder

- **Veredicto:** confirmado.
  - El webhook daba 200 aunque fallara.
  - El cuerpo vivía solo en memoria (debounce de 2 s), y un reenvío de Meta se descartaba como
    duplicado.
  - Cada deploy o reinicio con mensajes en la ventana los perdía.
  - Un test fijaba el 200 ante la falla.
- **Decisión:** WhatsApp durable completo.
- **Hecho:**
  - El cuerpo se guarda en `wa_messages` antes del 200; si la base falla, 500 y Meta reintenta.
  - Estados `received` → `processing` (reclamo atómico con `claimed_at` y `attempts`) → `answered`,
    `ignored` o `error`.
  - Recuperación al arrancar y cada 60 s, en el líder.
  - Tope `WA_MAX_ATTEMPTS`. El envío a Meta se trata como incierto: `processed_at` se marca antes de
    mandar, y si cae en el medio queda en `error` sin reenvío ciego.
  - Ante una falla del LLM se responde `WA_ERROR_REPLY`.
  - Al apagar, se esperan hasta 8 s los turnos en curso.
  - Archivos: `app/whatsapp/webhook.py`, `service.py` y `store.py`, y `app/main.py`.
- **Comprobado:**
  - `tests/test_prod_whatsapp.py`.
  - 14 casos en PostgreSQL: durable, muerte del proceso y recuperación, dedupe, error del LLM, dos
    senders y retención.
  - El test que fijaba el 200 ahora es `test_falla_al_guardar_da_500`.
- **Falta:**
  - Desplegar.
  - Prueba real: un mensaje y `docker stop app` en medio del turno. Se tiene que responder ~5 min
    después.
  - Al primer arranque, los `received` viejos sin cuerpo pasan a `error`: son los que ya se perdieron.

## H04 (P1): sin presupuesto global de capacidad

- **Veredicto:** confirmado.
  - `quota.admit` lockeaba solo al cliente.
  - El texto de WhatsApp no pasaba por admisión.
  - Los cupos de audio eran por proceso y las previews de TTS solo tenían límite horario.
  - La capacidad con Gemma no está medida.
- **Decisión:** tope global, con prioridad para las entrantes.
- **Hecho:**
  - `admit` toma `pg_advisory_xact_lock` global y después el lock del cliente.
  - `MAX_CONCURRENT_CALLS_GLOBAL` (20) e `INBOUND_RESERVE_CALLS` (4); si se pasa, 429 `platform_busy`.
  - Cupos fuera de llamadas:
    - `WA_MAX_CONCURRENT_TURNS` (8; los turnos encolan);
    - `TTS_PREVIEW_MAX_CONCURRENT` (2), compartido entre previews y demo (503 `tts_busy`);
    - `DEMO_SESSION_TTS_MAX`;
    - `API_MAX_CONCURRENT_TURNS` (4; 503 `llm_busy`).
- **Comprobado:**
  - En PostgreSQL, 12 admisiones de dos clientes con tope 3 entran exactamente 3. Sin el lock
    consultivo entran 4 y el test falla.
  - Una prueba aparte dio 10 concurrentes → 3 y 7 `platform_busy`.
- **Falta:** **CAP con Gemma** con llamadas, WhatsApp, previews y extracción para fijar los valores.
  20, 8, 4 y 2 son provisionales. Para la rampa hay que subir el tope global en `.env` durante la
  medición.

## H05 (P1): un cliente sin números llama con la identidad compartida

- **Veredicto:** confirmado en la admisión. `_caller_id` daba `None`, el worker mandaba
  `sip_number=""` y Asterisk caía en `ANURA_DID`. No se hizo una llamada real.
- **Decisión:** 409 `no_caller_id` para clientes, sin fallback; el admin queda exento.
- **Hecho:**
  - `app/services/calls.py`.
  - Asterisk (extra e): sin caller ID sale con `ANURA_DID` (solo pasa con un admin), y un caller ID
    inválido se rechaza.
  - La UI deshabilita "Llamar" y explica el error.
- **Comprobado:** `tests/test_prod_aislamiento.py`, con usuario y con API key.
- **Falta:**
  - Desplegar y recargar Asterisk.
  - Avisar a los clientes sin número.

## H06 (P1): el monitoreo da "todo bien" sin atender

- **Veredicto:** confirmado.
  - Solo se miraba `State.Status`.
  - `/health` daba siempre ok.
  - `agent` no tenía healthcheck.
  - El recordatorio horario estaba roto.
  - No había canal de alertas.
  - Matiz: las 46 h de "falla certificado SIP" del `health.log` (6-oct 10:28 a 8-oct 08:12) no eran
    el certificado, que vence el 4-ene-2027. Asterisk se recreó sin `method=sslv23` y servía TLS 1.0.
    Se arregló solo con el reinicio del host. El chequeo tenía razón, pero no le avisó a nadie.
- **Decisión:** chequeos funcionales y alertas externas.
- **Hecho** (`scripts/ops/healthcheck.sh`, ya activo por cron):
  - Salud de los contenedores y `/health/ready`, que responde solo a pares locales y da 503 sin base.
  - Relojes de las GPUs y TLS 1.2 con SNI.
  - Backup de más de 26 h.
  - Trunks y dispatch rule cada 10 min, que repara con `make livekit-sip`.
  - El recordatorio usa `health.alerted`.
  - Si faltan los canales de alerta, lo anota una vez por día.
  - Healthcheck de `agent` en :8081 y `stop_grace_period` de 30 s.
  - Redis de LiveKit con AOF (`docker-compose.livekit.yml`).
- **Comprobado:**
  - Con estado en `scratch/`: falla, silencio, recordatorio a los 61 min y vuelta a la normalidad.
  - Redis persiste tras un restart, probado en un contenedor desechable.
  - Incidente menor el 8-oct de 16:18 a 16:22: el chequeo nuevo corrió `make livekit-sip` contra la
    imagen vieja. Falló antes de escribir en LiveKit, sin efecto, y quedó en pausa hasta desplegar.
- **Falta:**
  - **Usuario:** `ALERT_NTFY_TOPIC` y `HEALTHCHECKS_PING_URL` en `.env`. Sin ellos nadie se entera.
  - Inducir fallas en un entorno aislado.

## H07 (P2): sesiones de base retenidas

- **Veredicto:** confirmado por código, sin medir en PostgreSQL.
  - `get_principal` no hacía commit con cookie, así que la conexión quedaba "idle in transaction"
    durante el LLM o Meta.
  - El pool era el default (5 + 10).
- **Decisión:** transacciones cortas.
- **Hecho:**
  - Commit al autenticar, y el turno de texto cierra la sesión antes del LLM.
  - En WhatsApp y el sender, la base va en `asyncio.to_thread`; `signup.release` hace commit antes
    de llamar a Meta.
  - Pool `DB_POOL_SIZE`/`DB_MAX_OVERFLOW`/`DB_POOL_TIMEOUT` (10 + 10, 10 s).
  - Archivos: `app/api/deps.py`, `app/db.py`, `app/whatsapp/*` y los routers.
- **Comprobado:** un test que verifica que no queda transacción abierta después de autenticar.
- **Falta:**
  - Prueba con PostgreSQL lento y concurrencia: retraso del loop y ocupación del pool.
  - El motor sigue con base síncrona dentro del loop.

## H08 (P2): la API de texto modifica conversaciones de llamadas

- **Veredicto:** confirmado. Solo se rechazaba WhatsApp, y el store reescribía todo sin versión.
- **Decisión:** cerrar la ruta y agregar control optimista.
- **Hecho:**
  - 409 `call_conversation`, `conversation_completed`, `turn_in_progress` y `conversation_conflict`.
  - `conversations.version` con `UPDATE … WHERE version = :v`.
  - El motor relee antes de guardar y reintenta una vez el guardado de la extracción.
  - La retención sube la versión.
  - Archivos: `app/api/routers/conversations.py`, `app/conversation/store.py` y `engine.py`.
- **Comprobado:**
  - `tests/test_prod_aislamiento.py`.
  - En PostgreSQL, el segundo guardado concurrente da conflicto.
- **Falta:** desplegar.

## H09 (P2): las estadísticas cargan el historial en memoria

- **Veredicto:** confirmado.
- **Decisión:** agregar en SQL y bajar el refresco.
- **Hecho:**
  - `/stats` y `/stats/daily` son agregaciones SQL, y la lista ya no lee `messages`.
  - Sin fechas, se toman los últimos 30 días; más de 366 días da 422.
  - UI: lista cada 5 s, en vivo 3 s, stats 30 s, daily 60 s. Archivos: `app/services/reports.py` y
    `web/src/features/calls/api.ts`.
- **Comprobado:**
  - Con 30.000 conversaciones en PostgreSQL: stats pasa de 4,7 s a 0,12 s, y daily de 366 días tarda
    0,17 s.
  - Los tests comparan fila por fila contra el cálculo anterior.
- **Falta:**
  - Desplegar.
  - Avisar que `/stats` sin fechas ahora cuenta 30 días.

## H10 (P1): los respaldos siguen dentro del host

- **Veredicto:** confirmado. Matiz: los dumps locales estaban al día; lo viejo era la restauración
  probada (migración 0005).
- **Decisión:** copia externa cifrada y restauración probada de la versión actual.
- **Hecho:**
  - `backup.sh` suma `storage/` y `asterisk/letsencrypt`, cifra con GPG lo que sube y deja
    `backup.ok`.
  - `scripts/ops/restore-test.sh` (`make restore-test`) restaura en un Postgres desechable y migra.
- **Comprobado:** `make restore-test` con `db-20261008-0330`: 2,6 s en total y 0008 → 0009; 2
  clientes, 7 agentes, 3 números y 2 cuentas de WhatsApp.
- **Falta:**
  - **Usuario:** `RCLONE_REMOTE`, `BACKUP_GPG_RECIPIENT` y la clave pública en el host.
  - Simulacro completo en otra máquina desde la copia externa (base, `.env`, checkpoint del TTS).
  - Definir RPO y RTO: con un dump diario, el RPO es de hasta 24 h.

## H11 (P2): el contexto crece sin presupuesto de tokens

- **Veredicto:** confirmado.
  - No había `max_tokens` y se mandaba el historial entero.
  - Ante un 400, la voz quedaba muda y WhatsApp trabado.
  - Un comentario decía 32768 de contexto y el real es 16384.
- **Decisión:** presupuesto total y respuesta de recuperación.
- **Hecho:**
  - `max_tokens` en cada pedido.
  - Recorte del historial a `LLM_CONTEXT_TOKENS` (`app/llm/budget.py`).
  - Deadline del pedido entero (20 s el turno, 45 s la extracción).
  - Errores con tipo (`app/llm/errors.py`).
  - Tope de `knowledge` y del prompt fijo al guardar (`app/agents/limits.py`).
  - Frase de respaldo en voz y `WA_ERROR_REPLY` en WhatsApp.
- **Comprobado:**
  - `tests/test_prod_llm.py`.
  - Los agentes de referencia entran: el más grande usa ~4,3k tokens, con un tope de 10.240.
- **Falta:**
  - Medir el deadline con Gemma.
  - Revisar (solo lectura) el tamaño de `knowledge` de los agentes de producción antes de desplegar.
  - Corregir el comentario del `.env`.

## H12 (P2): suspender y limitar a un cliente son controles incompletos

- **Veredicto:** confirmado.
  - Auth no miraba `Client.active`.
  - Los límites eran por principal, así que cada API key los multiplicaba.
  - Las API keys eran ilimitadas.
- **Decisión:** cliente inactivo = **solo lectura**: ve y exporta el historial; se niega lo que
  consume y crear API keys.
- **Hecho:**
  - `ActiveClientPrincipal` y `ensure_client_active` (`app/api/deps.py`) en llamadas, texto,
    previews, WhatsApp, campañas, agentes, números y API keys (403 `client_inactive`).
  - Los entrantes de WhatsApp quedan `ignored`, y al cerrar un chat no se corre la extracción final.
  - Límites por cliente (`per="client"`).
  - Tope de `MAX_API_KEYS_PER_CLIENT` (10).
  - Banner de solo lectura en la UI.
- **Comprobado:** `tests/test_prod_aislamiento.py` y `test_prod_revision.py`.
- **Falta:**
  - Desplegar y probar con un cliente inactivo real.
  - Avisar del cambio de límites.

## H13 (P2): exposición del host y configuración web

- **Veredicto:** confirmado en el host.
  - `app` estaba en `0.0.0.0:8011`.
  - El proxy en `0.0.0.0:8100` dejaba pasar rutas completas.
  - En `.env`, `AUTH_COOKIE_SECURE=false` y `CSP_REPORT_ONLY=true`.
  - Matiz: el router no se puede verificar desde acá. La contradicción del 8100 (AGENTS decía que se
    reenvía; PRODUCCION, README y MIGRACION, que no) queda **a confirmar por el usuario**, y los
    documentos ahora lo dicen así.
- **Decisión:** reducir la exposición; el `.env` lo cambia el usuario.
- **Hecho:**
  - `${APP_BIND:-127.0.0.1}:8011` en el compose.
  - Lista blanca en `proxy/nginx.conf`: health, models y el endpoint de cada servicio; el resto da
    404.
  - `server_tokens off`.
- **Comprobado:** nginx real con backends falsos, 21 casos: lo permitido pasa, y `/metrics`,
  `/tokenize`, la raíz y `../` dan 404.
- **Falta (usuario):**
  - `AUTH_COOKIE_SECURE=true`.
  - `CSP_REPORT_ONLY=false`, después de revisar los reportes con Embedded Signup.
  - Confirmar el reenvío del 8100 en el router y cerrarlo si no se usa el modo remoto.
  - Apuntar las rutas del túnel a `127.0.0.1:8011`.

## H14 (P2): más workers o réplicas duplican trabajo

- **Veredicto:** confirmado por diseño. Hoy hay un solo uvicorn, pero nada lo garantizaba.
- **Decisión:** un consumidor activo verificable.
- **Hecho:**
  - `app/services/leader.py`: `pg_try_advisory_lock` en una conexión propia, renovado cada 15 s. Los
    loops corren solo en el líder.
  - Reclamo atómico `pending → sending` en el sender (`claimed_at`).
  - `recover` solo marca como failed los `sending` vencidos.
- **Comprobado:**
  - En PostgreSQL, de dos `Leader` toma el lock uno solo, y al soltarlo lo toma el otro.
  - De 8 senders sobre el mismo destinatario, gana uno.
- **Falta:**
  - El debounce y el lock por contacto, los límites por hora y los cupos siguen en memoria. **Un solo
    uvicorn** (Dockerfile y comentario del compose).
  - Para escalar `app` hay que pasarlos a la base.

## Otros casos de la revisión

| Caso | Veredicto | Hecho | Falta |
|---|---|---|---|
| Idempotencia de `POST /calls` y conciliación de huérfanas | Confirmado | Header `Idempotency-Key` con huella del pedido (409 `idempotency_key_reused`), carrera resuelta por UNIQUE; el despacho fallido suelta la clave. Huérfanas: conciliación (H02) | Desplegar |
| Minutos facturados con la extracción | Confirmado | `finalize` toma la hora de fin antes de esperar `engine.finish` | — |
| Retención y trazabilidad | Confirmado | Retención por tier con override por cliente (`retention_days`; vacío = sin borrado), en el líder: anonimiza conversaciones, enmascara teléfonos y borra cuerpos de WhatsApp y datos de campañas viejas; conserva la fila de llamada y las bajas (`app/services/retention.py`) | Cargar `retention_days` en los tiers. **Log de auditoría** de acciones administrativas: no hecho |
| WhatsApp Calling de terceros | Confirmado | El DID que no se puede leer se corta (ya no cae en el agente de Atentina) | **Auth SIP por número** en `pjsip_whatsapp.conf`: pendiente, antes de habilitarlo a terceros |
| Dependencias y despliegue | Confirmado | Todas las imágenes por digest (compose, Dockerfile, `CERTBOT_IMAGE`), `requirements.lock` y `stt/requirements.lock` como constraints, `apk` de Asterisk `~22.9` | Rebuild; escaneo de vulnerabilidades no hecho; la imagen de `agent` es más vieja que la de `app` (livekit-agents 1.8.4 contra 1.8.5) |
| Voz del TTS sin validar | Confirmado | El worker nunca manda `default`; `agent` no arranca si `VLLM_TTS_VOICE` no está servida | — |
| Descarga de media con redirecciones | Confirmado (sin URL explotable demostrada) | Redirecciones a mano, hasta 3, cada salto revalidado (https y host de Meta); errores hasta 64 KB | — |

## Documentación reconciliada

| Afirmación de la revisión | Qué se cambió |
|---|---|
| README y capacidad: ~32 llamadas vigentes | README y AGENTS ya decían que con Gemma no hay CAP. El tope global (20) quedó como provisional en AGENTS y PRODUCCION, y `capacity/README.md` explica cómo subirlo para medir |
| ARQUITECTURA: TTS de WhatsApp en la 5060 Ti | Corregido: GPU 1 del reparto 2 × 3090 |
| AGENTS: caller ID único `ANURA_DID` | AGENTS, ARQUITECTURA, TELEFONIA_ANURA y el comentario del worker: caller ID del cliente, `ANURA_DID` solo para un admin |
| PRODUCCION: faltan backups y arranque | La tabla del 2-oct quedó marcada como histórica; estado actual en las secciones 3 y 3.1 |
| Proxy 8100 reenviado o no | "A confirmar por el usuario" en AGENTS, README, PRODUCCION y el comentario del compose |
| Inferencia propia = ningún dato afuera | PRODUCCION, sección 1: Meta, Cloudflare, Anura y `meet.livekit.io` sí reciben datos |

## Qué requiere al usuario

1. **Desplegar** en una ventana sin llamadas ([`PRODUCCION.md`](PRODUCCION.md), 3.1) y hacer las
   pruebas en vivo.
2. **`.env`**, con el diff enmascarado antes de reiniciar:
   - alertas: `ALERT_NTFY_TOPIC` y `HEALTHCHECKS_PING_URL`;
   - copia externa: `RCLONE_REMOTE` y `BACKUP_GPG_RECIPIENT`;
   - seguridad: `AUTH_COOKIE_SECURE=true` y `CSP_REPORT_ONLY=false`;
   - `APP_BIND` sin definir.
3. **Router y Cloudflare:** confirmar el 8100 y apuntar las rutas del túnel a `127.0.0.1:8011`.
4. **CAP con Gemma** para fijar `MAX_CONCURRENT_CALLS_GLOBAL`, los cupos y el deadline del LLM.
5. **WhatsApp Calling de terceros:** auth SIP por número antes de ofrecerlo.
6. **Retención:** cargar `retention_days` por tier.
7. **Avisar a los clientes:**
   - sin número propio no hay salientes;
   - los límites por hora se comparten entre usuarios y claves;
   - hay un tope de 10 API keys;
   - `/stats` sin fechas cuenta 30 días.
8. **SLA:** [`SLA/SLA-Atentina.md`](SLA/SLA-Atentina.md) queda como objetivo, con la lista de lo que
   falta al inicio. No se muestra a clientes.
