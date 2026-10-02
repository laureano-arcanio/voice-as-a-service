# Plan de producción

Versión del 2-oct-2026. **Decisión propuesta:**
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
| **Datos en Argentina** | Nada sale a OpenAI, Google ni ElevenLabs (Ley 25.326). Pesa en Estado, salud y cobranzas. |
| **Capacidad** | Un server: ~22 llamadas con p95 ≤ 2,8 s, ~163.000 minutos por mes en horario comercial. El objetivo a 6 meses son 50–100 mil minutos por mes: **alcanza un server** (30–60 %). |

| En contra (lo que hay que resolver) | Por qué importa |
|---|---|
| **Disponibilidad** | Hoy todo depende de una casa: energía, internet, una máquina y una persona. Un corte es una campaña de cobranza que no sale. |
| **Operación 24×7** | La inferencia no vuelve sola después de un reinicio, y el TTS sobrecargado se cae y no se recupera (sección 2). Alguien tiene que enterarse y actuar. |
| **Host compartido** | Hoy corren otros proyectos en la misma máquina, y el segundo cuello medido es la CPU del host. |

**Base de datos: local es lo correcto.** El worker de voz (`app/voice/worker.py`) usa la base dentro de cada
turno. Una base en la nube (Render no tiene región en Sudamérica, ~150 ms de ida y vuelta desde Córdoba)
sumaría varias idas y vueltas por turno de llamada. La nube sirve para los backups, no para la base en uso.

## 2. Estado real del server (relevado el 2-oct-2026)

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
| Stack en el arranque: compose sin build, túnel, trunks SIP y calentamiento del TTS | `deploy/boot.sh`, `deploy/systemd/atentina-stack.service` | **Habilitado**; se prueba en el próximo reinicio |
| Backup diario a las 03:30 de la base (`pg_dump`), `.env` y checkpoint del TTS, 30 días, a `~/atentina-backups` (otro disco que Docker) | `scripts/ops/backup.sh`, cron del usuario | **Activo.** Restauración probada en un Postgres limpio (961 conversaciones, migración 0005). Copia externa cifrada con `RCLONE_REMOTE` y `BACKUP_GPG_RECIPIENT` en `.env`: pendiente |
| Fraude telefónico: reenvío del 5080 (SIP de LiveKit Cloud) borrado del router y ACL en el endpoint `livekit` (loopback y LAN) | router; `asterisk/conf/pjsip.conf` | **Activo.** Quedan reenviados el RTP de Anura (10000–10199) y la demo web (7881, 7882). El 8100 ya no estaba |
| Reparto de GPU de CAP-001 (LLM solo en la GPU 0; TTS + STT en la GPU 1), sin el override de la 5060 Ti | `.env` (`COMPOSE_FILE`), `make up-inference` | **Activo.** ~4 min sin servicio al cambiarlo; TTS 0,8 s el primer pedido |
| Chequeo cada 2 min: contenedores, app local, dashboard y webhook por el túnel, tope de las GPUs | `scripts/ops/healthcheck.sh`, cron del usuario; log en `~/atentina-ops/health.log` | **Activo.** Alertas: `ALERT_NTFY_TOPIC` (app ntfy) y vigilante externo `HEALTHCHECKS_PING_URL`: pendientes |

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
  - Tope de concurrencia global por server, porque con ~110 llamadas el TTS se cae.
- **D. Arranque automático** (unidades de systemd, versionadas en el repo):
  - tope de potencia y relojes de cada GPU, más *persistence mode*;
  - `make up` al bootear;
  - Redis de LiveKit con persistencia, o `make livekit-sip` automático;
  - calentamiento del TTS (> 20 s el primer pedido).
- **E. Backups:**
  - `pg_dump` diario cifrado a almacenamiento externo (por ejemplo R2 o B2). Retención de 30 días y **restauración probada**.
  - `.env` en un gestor de secretos.
  - Copia externa de `tts/finetune/work/`.
- **F. Monitoreo:**
  - Chequeo externo cada minuto de `https://app.atentina.com.ar/health` y del webhook.
  - Llamada de prueba diaria por Anura.
  - Alertas al celular.
  - El sampler de `scripts/capacity/` como métricas, con retención.
- **G. Seguridad:**
  - Firewall que acepte SIP solo desde las IP de Anura.
  - SSH solo con llave.
  - Actualizaciones.
  - CSP en modo estricto: hoy está `CSP_REPORT_ONLY=true`.
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
| Web y WhatsApp | El túnel de Cloudflare admite varios conectores del mismo túnel: alta disponibilidad sin cambios. Pero `app` corre con **un solo worker** y el servicio de WhatsApp tiene locks en memoria, así que `app` va **activo-pasivo**. |
| Base | Postgres primario en A y réplica *streaming* en B. Al principio, el failover es manual. |
| Capacidad que se vende | **N+1:** se sigue vendiendo la capacidad de **un** server (~22 llamadas, o ~32 con 2 × 3090). Si cae uno, el otro atiende todo. |

Conviene que el segundo server sea igual al primero: mismo override, mismos números de capacidad y mismos
repuestos. Hoy eso es 3090 + 5060 Ti (ARS ~2,9 M en GPUs) o 2 × 3090 (ARS ~4 M), calculadora tipos A y B.

## 6. Disponibilidad: medir antes de prometer

No hay datos de cortes de luz ni de internet de este sitio. Ofrecer un SLA en porcentaje hoy sería inventarlo.

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
