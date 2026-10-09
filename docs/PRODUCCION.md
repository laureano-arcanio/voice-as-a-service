# Plan de producción

Versión del 2-oct-2026, actualizada el 8-oct-2026 con la revisión externa del 7-oct (sección 3.1). **Decisión propuesta:**
- Este server pasa a producción con la IP fija `181.104.113.28`.
- Inferencia propia (LLM, STT y TTS), sin nube.
- Base local.
- Con el primer cliente pago, un segundo server igual y UPS.

Se apoya en:
- la capacidad medida ([`capacity/`](capacity/README.md): CAP-001, 002 y 004);
- el hardware ([`SERVER_HARDWARE.md`](SERVER_HARDWARE.md));
- el plan comercial ([`mercado/plan-salida-al-mercado.md`](mercado/plan-salida-al-mercado.md));
- la [calculadora de costos](calculadora-costos.html).

## 1. Validación: ¿tiene sentido?

**Sí, con condiciones.** Es la tesis del plan comercial y los datos la sostienen. La ventaja no es tener
el hardware: es lo que el hardware permite. Y solo vale si la disponibilidad es aceptable para el cliente.

| A favor | Dato |
|---|---|
| **Costo por minuto** | Con inferencia propia se puede cobrar USD 0,08–0,15 por minuto. Un agente armado sobre Vapi más Twilio cuesta 0,19–0,26, y los agentes locales cobran 0,28–0,35 (plan comercial, sección 1). Las GPUs de un server tipo CAP-002 cuestan ~ARS 2,9 M (calculadora, tipo A). |
| **Latencia** | Todo en una máquina: STT, LLM y TTS por loopback, y el worker lee y escribe la conversación en Postgres varias veces por turno. El piso medido ya es el punto débil (p50 1,66 s, CAP-002). Cualquier salto de red lo empeora. |
| **Datos en Argentina** | La inferencia (audio y texto) no sale a OpenAI, Google ni ElevenLabs (Ley 25.326). Pesa en Estado, salud y cobranzas. Sí pasan por terceros: los mensajes de WhatsApp (Meta), el dashboard, la demo y el webhook (Cloudflare, por el túnel), la telefonía (Anura) y el link de la llamada de prueba (`meet.livekit.io`, con token). |
| **Capacidad** | Con el Qwen3.5-9B (antes del 6-oct-2026; con Gemma 4 26B, el vigente, sin medir): un server: ~22 llamadas con p95 ≤ 2,8 s, ~163.000 minutos por mes en horario comercial. El objetivo a 6 meses son 50–100 mil minutos por mes: **alcanza un server** (30–60 %; a revalidar con la capacidad de Gemma). |

| En contra (lo que hay que resolver) | Por qué importa |
|---|---|
| **Disponibilidad** | Hoy todo depende de una casa: energía, internet, una máquina y una persona. Un corte es una campaña de cobranza que no sale. |
| **Operación 24×7** | Desde el 2-oct-2026 el stack vuelve solo después de un reinicio (sección 3), pero el TTS sobrecargado se cae y no se recupera, y `docker` lo sigue viendo `running`. Alguien tiene que enterarse y actuar. |
| **Host compartido** | Hoy corren otros proyectos en la misma máquina, y el segundo cuello medido es la CPU del host. |

**Base de datos: local es lo correcto.** El worker de voz (`app/voice/worker.py`) usa la base dentro de cada
turno. Una base en la nube (Render no tiene región en Sudamérica, ~150 ms de ida y vuelta desde Córdoba)
sumaría varias idas y vueltas por turno de llamada. La nube sirve para los backups, no para la base en uso.

## 2. Estado del server relevado el 2-oct-2026 (histórico)

**Tabla histórica:** es el registro del relevamiento del 2-oct-2026 y no describe el estado actual. Lo
resuelto después está en las secciones 3 y 3.1.

| Hallazgo | Riesgo | Qué hacer |
|---|---|---|
| `nvidia-smi` muestra **2 × RTX 3090 a 350 W**. `AGENTS.md` y CAP-002 dicen 5060 Ti + 3090 a 280 W. | **Bloqueante.** Sin tope, dos 3090 ya apagaron el server por un pico. Además, la capacidad vigente se midió con otro hardware. | Confirmar el hardware real. Aplicar el tope y que sobreviva al reinicio (sección 3, D). Si quedan 2 × 3090, rige CAP-001 (~32 llamadas con p95 ≤ 3 s) y hay que actualizar `AGENTS.md`. |
| El tope de GPU no sobrevive al reinicio. La inferencia queda en `Exited (128)`. El Redis de LiveKit no persiste y se borran los trunks SIP. | Después de un corte de luz el servicio no vuelve solo. | Arranque automático (4, D). |
| Corren **Dify** (14 contenedores) y **sim-poc** (Postgres y Redis) en el mismo host. | Compiten por la CPU (cuello desde ~55 llamadas) y la RAM (34 de 62 GB usados). | **Se quedan** (decisión del 2-oct-2026). Vigilar la CPU en el test de capacidad. |
| La 3090 también dibuja el escritorio. | VRAM y riesgo de que la sesión gráfica afecte la inferencia. | Host sin sesión gráfica (o video integrado). |
| El proxy de inferencia está publicado en el router, en el **8100**: HTTP plano, protegido solo por `VLLM_API_KEY`. | Inferencia expuesta a internet. | En producción no se usa el modo remoto: cerrar el 8100 en el router. |
| `app` (8011) escucha en `0.0.0.0`. | Expuesta a la LAN, sin pasar por el túnel. | Firewall del host: solo localhost, el túnel y la LAN de administración. |
| **No hay backup de la base** (ni cron ni dump), ni de `.env`, ni del checkpoint del TTS (`tts/finetune/work/`, no versionado). | Si se pierde, hay que **reentrenar las voces**. Sin `WA_TOKEN_KEY`, los tokens de clientes no se pueden leer. | Backups (4, E). |
| No hay monitoreo externo ni alertas. | Nadie se entera de una caída. | Monitoreo (4, F). |
| CAP-004: 5060 Ti por riser x1 con errores de enlace (replays). | El TTS se cayó con el enlace malo. | Si vuelve la 5060 Ti: slot directo, nada de riser. |

## 3. Implementado (2-oct-2026)

| Qué | Dónde | Estado |
|---|---|---|
| Topes de las 3090 en cada arranque (280 W, núcleo ≤ 1800 MHz, memoria 9501 MHz, *persistence mode*) | `deploy/gpu-limits.sh`, `deploy/systemd/atentina-gpu-limits.service` | **Activo** (instalado con `sudo deploy/install.sh`) |
| Stack en el arranque: compose sin build, túnel, trunks SIP y calentamiento del TTS | `deploy/boot.sh`, `deploy/systemd/atentina-stack.service` | **Activo, probado** en el reinicio del 8-oct-2026: topes aplicados a los 15 s del boot y stack listo (TTS caliente) en ~2 min (`journalctl -u atentina-stack`). No probado con un corte de luz ni con un pull de imágenes pendiente |
| Backup diario a las 03:30 de la base (`pg_dump`), `.env` y checkpoint del TTS, 30 días, a `~/atentina-backups` (otro disco que Docker) | `scripts/ops/backup.sh`, cron del usuario | **Activo.** Restauración probada el 8-oct-2026 con `make restore-test` (ver la fila del backup ampliado); la anterior, del 2-oct, fue con la migración 0005. Pasos manuales en [`MIGRACION_SERVER.md`](MIGRACION_SERVER.md), 4.2. Si el host está apagado a las 03:30, ese día no hay backup (cron no recupera la corrida). Copia externa cifrada con `RCLONE_REMOTE` y `BACKUP_GPG_RECIPIENT` en `.env`: pendiente |
| Fraude telefónico: reenvío del 5080 (SIP de LiveKit Cloud) borrado del router y ACL en el endpoint `livekit` (loopback y LAN) | router; `asterisk/conf/pjsip.conf` | **Activo.** Quedan reenviados el RTP de Anura (10000–10199), la demo web (7881, 7882) y, desde el 6-oct-2026, el TCP 5061 (llamadas de WhatsApp). El 8100 ya no estaba reenviado ese día (visto por el usuario en el router; el estado actual lo confirma el usuario: desde el host solo se ve que el proxy escucha en `0.0.0.0:8100`). Tabla completa en [`MIGRACION_SERVER.md`](MIGRACION_SERVER.md), 6 |
| Reparto de GPU de CAP-001 (LLM solo en la GPU 0; TTS + STT en la GPU 1), sin el override de la 5060 Ti | `.env` (`COMPOSE_FILE`), `make up-inference` | **Activo.** ~4 min sin servicio al cambiarlo; TTS 0,8 s el primer pedido. Desde el 6-oct-2026 el LLM de la GPU 0 es Gemma 4 26B (`docker-compose.gemma4-26b.yml`) |
| Chequeo cada 2 min: contenedores, app local, dashboard y webhook por el túnel, tope de las GPUs, certificado SIP de WhatsApp (<14 días) | `scripts/ops/healthcheck.sh`, cron del usuario; log en `~/atentina-ops/health.log` | **Activo**, ampliado el 8-oct-2026 (fila siguiente). Alertas: `ALERT_NTFY_TOPIC` (app ntfy) y vigilante externo `HEALTHCHECKS_PING_URL`: pendientes |
| Revisión de producción del 7-oct-2026, en el árbol (8-oct-2026; despliegue pendiente: migración 0009, `make build`, recrear, `make livekit-sip`) | `docs/revision-produccion-2026-10-07.html`, `tests/test_prod_*.py` | Tope global de llamadas (`MAX_CONCURRENT_CALLS_GLOBAL`), duración por tier con techo en LiveKit y Asterisk, conciliación de llamadas huérfanas, WhatsApp durable, líder único para los loops, retención por tier o cliente, cliente inactivo en solo lectura, `/health/ready`, healthcheck de `agent`, Redis de LiveKit persistente, `app` en 127.0.0.1, lista blanca del proxy e imágenes por digest |
| Chequeo ampliado (8-oct-2026): salud de contenedores, `/health/ready`, relojes de las GPUs, TLS 1.2 del SIP, backup de más de 26 h, trunks de LiveKit cada 10 min (repara con `make livekit-sip`) y recordatorio horario arreglado (`health.alerted`) | `scripts/ops/healthcheck.sh` | **En la rama**: cron corre el script del árbol, así que queda activo al pasar el árbol a la rama. Sin `ALERT_NTFY_TOPIC` ni `HEALTHCHECKS_PING_URL` no avisa a nadie: así pasaron 46 h de "falla certificado SIP" (6 al 8-oct; era Asterisk sin `method=sslv23`, TLS 1.0) |
| Backup ampliado (8-oct-2026): suma `storage/` y `asterisk/letsencrypt`, cifra la copia externa con GPG y deja `backup.ok`. Prueba de restauración: `make restore-test` (Postgres desechable en :55433, último dump y `alembic upgrade head`) | `scripts/ops/backup.sh`, `scripts/ops/restore-test.sh` | **Restauración probada el 8-oct-2026** con `db-20261008-0330` (56 KB): Postgres listo en 1,3 s, dump en 0,2 s, migración 0008 → 0009 en 0,7 s (sin números cruzados entre clientes), 2,6 s en total; 2 clientes, 7 agentes, 3 números, 2 cuentas de WhatsApp. Es solo la base y desde el disco local: falta un simulacro desde la copia externa, con `.env` y checkpoint del TTS. La primera corrida de cron con `storage/` y el certificado es la del 9-oct a las 03:30. Copia externa: pendiente (`RCLONE_REMOTE`, `BACKUP_GPG_RECIPIENT`) |
| Renovación diaria (04:15) del certificado de `sip.atentina.com.ar` (llamadas de WhatsApp): renueva a 30 días del vencimiento y reinicia Asterisk solo sin llamadas en curso | `scripts/ops/sip-cert-renew.sh`, cron del usuario; log en `~/atentina-ops/sip-cert.log` | **Activo** (6-oct-2026). Ver [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md), 5.4 |

## 3.1 Revisión de producción del 7-oct-2026: estado al 8-oct-2026

La revisión externa ([`revision-produccion-2026-10-07.html`](revision-produccion-2026-10-07.html), 14
hallazgos) se verificó contra el código: todos eran reales. El usuario decidió salir a **producción
multi-cliente abierta** e implementar todos. Detalle por hallazgo (veredicto, decisión, archivos,
pruebas) en [`revision-produccion-2026-10-07-respuesta.md`](revision-produccion-2026-10-07-respuesta.md).

**Todo está en la rama `produccion-multicliente` (9-oct-2026), sin desplegar; `main` sigue con lo que corre.** Tests: 480 pasan en SQLite (13 se saltean: piden
vLLM o PostgreSQL). En un PostgreSQL desechable (`TEST_DB_DSN`) pasó la suite entera (476) antes de las
últimas correcciones, y después los 43 de los archivos tocados, incluidas las carreras de
`tests/test_prod_postgres.py`.

| Hallazgo | En el árbol | Falta |
|---|---|---|
| H01 número con agente de otro cliente | Lock y relectura en PATCH/release, FK compuesta (0009), chequeo en la entrante | Desplegar |
| H02 entrantes sin tope | Tope por tier en todas las modalidades, techo de 3600 s en LiveKit y Asterisk, conciliación con LiveKit | Desplegar, `make livekit-sip`, `make up-pbx`; matar `agent` en una llamada de prueba y ver `room_gone` |
| H03 WhatsApp pierde mensajes | Cuerpo en la base antes del 200, estados, reintentos y recuperación | Desplegar; prueba con un mensaje real y `docker stop app` en medio del turno |
| H04 sin tope global | `MAX_CONCURRENT_CALLS_GLOBAL` (20) con reserva de entrantes (4), cupos de WhatsApp, previews y texto | **CAP con Gemma** para fijar los valores (hoy provisionales) |
| H05 saliente sin número propio | 409 `no_caller_id` (admin exento) | Avisar a los clientes sin número |
| H06 monitoreo ciego | Chequeo ampliado (activo), `/health/ready`, healthcheck de `agent`, Redis de LiveKit persistente | **Alertas:** `ALERT_NTFY_TOPIC` y `HEALTHCHECKS_PING_URL` |
| H07 sesiones retenidas | Commit al autenticar, sesiones cortas, base de WhatsApp en threads, pool 10 + 10 | Desplegar; medir con Postgres lento |
| H08 texto escribe en llamadas | 409 por canal y estado, control optimista (`version`) | Desplegar |
| H09 estadísticas en memoria | Agregación SQL (stats de 30.000 conversaciones: 4,7 s → 0,12 s), rango máximo de 366 días, refresco de la UI más lento | Desplegar |
| H10 backup solo local | Backup ampliado y `make restore-test` (probado) | **Copia externa:** `RCLONE_REMOTE` y `BACKUP_GPG_RECIPIENT`; simulacro desde afuera; definir RPO y RTO |
| H11 contexto sin tope | `max_tokens`, recorte del historial, deadline, tope de `knowledge` | Medir el deadline con Gemma |
| H12 cliente inactivo consume | Solo lectura, límites por cliente, tope de 10 API keys | Desplegar; avisar a los clientes |
| H13 exposición | `APP_BIND` (127.0.0.1), lista blanca de nginx | **Usuario:** `AUTH_COOKIE_SECURE=true`, `CSP_REPORT_ONLY=false` después de revisar los reportes, confirmar el 8100 del router, rutas del túnel a `127.0.0.1:8011` |
| H14 varios procesos | Líder por lock consultivo, reclamo atómico de campañas | Sigue un solo uvicorn (debounce y locks por contacto en memoria) |
| Extras | Idempotencia de `POST /calls`, duración sin la extracción, voz del TTS validada, redirecciones de media, DID de WhatsApp desconocido cortado, imágenes por digest y `requirements.lock`, retención por tier o cliente | **WhatsApp Calling de terceros:** auth SIP por número (hoy uno global). Cargar `retention_days` en los tiers |

**Despliegue:** en la rama `produccion-multicliente`, de punta a punta (preparación, corte, verificación,
vuelta atrás y lo que sigue) en [`DESPLIEGUE_REVISION_PRODUCCION.md`](DESPLIEGUE_REVISION_PRODUCCION.md).

**Cambios de `.env` propuestos** (no aplicados; con el diff enmascarado antes de reiniciar):
`AUTH_COOKIE_SECURE=true`, `CSP_REPORT_ONLY=false` (después de revisar reportes), `ALERT_NTFY_TOPIC`,
`HEALTHCHECKS_PING_URL`, `RCLONE_REMOTE`, `BACKUP_GPG_RECIPIENT`, `APP_BIND` sin definir (0.0.0.0 solo
durante el test de capacidad, junto con `MAX_CONCURRENT_CALLS_GLOBAL=200`) y corregir el comentario que
dice 32768 de contexto (es 16384).

**Avisar a los clientes:** sin número propio ya no hay salientes; los límites por hora se comparten
entre usuarios y API keys; tope de 10 API keys activas; `/stats` sin fechas cuenta los últimos 30 días.

## 4. Qué falta para declarar producción con un server

Va en orden de prioridad. Las letras se usan en la sección 7.

- **A. Energía:**
  - UPS senoidal, *online* o *line-interactive*.
  - Carga a cubrir: ~570 W para 3090 + 5060 Ti y ~710 W para 2 × 3090 a 280 W (calculadora, tipos A y B), más el router y la ONT. Es decir, una UPS de 1500–2200 VA (≥ 1000 W reales) con 10–15 min de autonomía.
  - Apagado ordenado por USB con NUT. Los cortes largos no se cubren: quedan como caída aceptada hasta tener un segundo sitio.
- **B. Internet:**
  - Confirmar si la IP fija es de un plan residencial o de empresa (términos y SLA).
  - Sumar una segunda conexión (otra fibra o 4G). Con ella, el túnel de Cloudflare (dashboard, demo, WhatsApp) sigue andando con cualquier IP. La **telefonía** (SIP de Anura y medios de LiveKit con `LIVEKIT_NODE_IP`) depende de la IP fija: confirmar con Anura si admite un segundo destino.
- **C. Host dedicado:**
  - Dejar de usarlo para desarrollo, loadtests y sesiones de agentes: hace falta un **equipo de desarrollo aparte**.
  - Tope de concurrencia global por server, porque con ~110 llamadas el TTS se cae. Hecho en el árbol el 8-oct-2026 (`MAX_CONCURRENT_CALLS_GLOBAL`, 20 provisional): falta medir el valor con un CAP con Gemma.
- **D. Arranque automático** (unidades de systemd, versionadas en el repo):
  - tope de potencia y relojes de cada GPU, más *persistence mode*;
  - `make up` al bootear;
  - Redis de LiveKit con persistencia, o `make livekit-sip` automático (las dos hechas en el árbol el 8-oct-2026);
  - calentamiento del TTS (> 20 s el primer pedido).
- **E. Backups:**
  - `pg_dump` diario cifrado a almacenamiento externo (por ejemplo R2 o B2). Retención de 30 días y **restauración probada**. Al 8-oct-2026: el cifrado y la subida están en `backup.sh` y la restauración local se probó; falta configurar el remoto y probar desde ahí.
  - `.env` en un gestor de secretos.
  - Copia externa de `tts/finetune/work/`.
- **F. Monitoreo:**
  - Alertas del chequeo local: configurar `ALERT_NTFY_TOPIC` y `HEALTHCHECKS_PING_URL` (hoy vacíos: el chequeo no avisa a nadie).
  - Chequeo externo cada minuto de `https://app.atentina.com.ar/health` y del webhook.
  - Llamada de prueba diaria por Anura.
  - Alertas al celular.
  - El sampler de `scripts/capacity/` como métricas, con retención.
- **G. Seguridad:**
  - Firewall que acepte SIP solo desde las IP de Anura.
  - SSH solo con llave.
  - Actualizaciones.
  - CSP en modo estricto: hoy está `CSP_REPORT_ONLY=true`.
  - `AUTH_COOKIE_SECURE=true` (hoy `false`).
  - Confirmar en el router qué puertos se reenvían (el 8100 solo para el modo remoto). `app` ya escucha solo en 127.0.0.1 desde el próximo despliegue.
- **H. Operación:**
  - Despliegues con ventana: `app` se corta segundos; la inferencia, minutos más el calentamiento.
  - Una persona responsable de las alertas.
  - Anotar cada incidente.

## 5. Redundancia: dos servers iguales con UPS

**Qué cubre:** la falla de un server (GPU, fuente o disco) y el mantenimiento sin cortar el servicio.

**Qué no cubre si están en el mismo lugar:** cortes de luz largos, la caída de internet, incendio o robo.
Para el primer cliente alcanza un solo sitio con UPS y dos conexiones de internet. Un segundo sitio, cuando un
contrato lo exija.

| Pieza | Cómo se reparte |
|---|---|
| Llamadas | Activo-activo: cada server con su inferencia, su agente y su LiveKit. Anura enruta a los dos (a confirmar: prioridad o reparto). |
| Web y WhatsApp | El túnel de Cloudflare admite varios conectores del mismo túnel: alta disponibilidad sin cambios. Los loops de fondo ya corren en un solo líder (lock consultivo, 8-oct-2026), pero `app` sigue con **un solo worker** porque el debounce y el lock por contacto de WhatsApp están en memoria: `app` va **activo-pasivo**. |
| Base | Postgres primario en A y réplica *streaming* en B. Al principio, el failover es manual. |
| Capacidad que se vende | **N+1:** se sigue vendiendo la capacidad de **un** server (~22 llamadas, o ~32 con 2 × 3090). Si cae uno, el otro atiende todo. |

Conviene que el segundo server sea igual al primero: mismo override, mismos números de capacidad y mismos
repuestos. Hoy eso es 3090 + 5060 Ti (ARS ~2,9 M en GPUs) o 2 × 3090 (ARS ~4 M), calculadora tipos A y B.

## 6. Disponibilidad: medir antes de prometer

No hay datos de cortes de luz ni de internet de este sitio. Ofrecer un SLA en porcentaje hoy sería inventarlo.
El borrador [`SLA/SLA-Atentina.md`](SLA/SLA-Atentina.md) (99,8 %) queda como **objetivo**: no se muestra a
clientes hasta cumplir la lista que tiene al inicio.

1. **Desde el día uno, monitoreo externo** (4, F): registra cada minuto caído.
2. **Con 3 meses de datos**, recién ahí se puede ofrecer un SLA, con créditos si no se cumple.
3. **Con los pilotos:** "horario comercial con soporte" y reprogramar automáticamente las campañas cortadas. Para salientes, que es el foco comercial, una caída corta se recupera reintentando.

## 7. Orden propuesto

| Cuándo | Qué | Costo aproximado |
|---|---|---|
| Antes del primer piloto | Hardware real y topes persistentes (2, D); backups (E); monitoreo (F); equipo de desarrollo aparte | Horas de trabajo, más ~USD 5 por mes de backups |
| Antes del primer piloto | UPS (A) | Una UPS de 2 kVA (a cotizar) |
| Con el primer cliente pago | Segunda conexión de internet (B); segundo server igual con UPS; réplica de la base | GPUs ARS 2,9–4 M, más el resto del equipo |
| Con un contrato que exija SLA | Segundo sitio; failover automático de la base | A evaluar |

## 8. Decisiones abiertas

- **Resuelto (2-oct-2026):** producción con **2 × 3090**; la 5060 Ti fue una prueba. Rige CAP-001 (~32 llamadas con p95 ≤ 3 s) con el reparto del compose principal. El segundo server, igual: 2 × 3090.
- El plan de internet: residencial o empresa, SLA, y si la segunda conexión puede tener IP fija.
- Anura: ¿la troncal admite dos destinos o failover?
- Quién atiende las alertas fuera de horario, y qué SLA se ofrece a los pilotos.
- Dónde se desarrolla y se valida una vez que este server sea producción.
