# Observabilidad del hardware y del servicio

Cómo ver el estado del server en cada momento y hacia atrás, enterarse de un problema y explicar
un pico: qué subió, cuándo y con cuántas llamadas en curso.

## 1. Piezas

```
host ── atentina-hostmon (systemd) ──► textfile ──┐
host ── node-exporter ────────────────────────────┤
vLLM, STT (/metrics), app (/internal/metrics) ────┼──► Prometheus ──► Alertmanager ──► ntfy (celular)
blackbox (sondas internas y externas) ────────────┘        │
                                                           └──► app /api/v1/system/* ──► pantalla Sistema
                                                                                     └─► MCP (admin)
```

| Pieza | Dónde | Qué hace |
|---|---|---|
| `atentina-hostmon` | `deploy/monitoring/hostmon.py`, servicio de systemd `deploy/systemd/atentina-hostmon.service` | Colector propio, como root, cada 5 s. Lee lo que no trae node-exporter: cada GPU (uso, VRAM total y por servicio, potencia y tope, temperatura, ventilador, relojes, motivos de recorte, enlace PCIe, errores XID del driver), los contenedores de Atentina (arriba, healthcheck, reinicios de Docker, fin por OOM, CPU y RAM), SMART de los discos (cada 5 min), registro SIP de Asterisk (cada 30 s), energía de la CPU (RAPL), IP pública e internet (cada 5 min). Escribe `/var/lib/atentina-hostmon/atentina.prom`. |
| `node-exporter` | `docker-compose.monitoring.yml` | CPU, RAM, swap, presión (PSI), discos, red, UDP descartado, temperaturas de la placa, NTP, OOM del kernel y el archivo de `atentina-hostmon`. Va en la red del host y escucha solo en `10.250.250.1`, el gateway de la red `atentina-monitoring`, que no sale del host. |
| `blackbox` | `docker-compose.monitoring.yml`, `deploy/monitoring/blackbox.yml` | Sondas. Internas cada 15 s: app, LLM, STT, TTS, base, LiveKit y proxy. Externas cada 30 s: ping a 1.1.1.1 y 8.8.8.8, DNS, dashboard por el túnel, webhook de WhatsApp (espera 403), Meta, Resend y Mercado Pago. |
| `prometheus` | `docker-compose.monitoring.yml`, `127.0.0.1:9090` | Raspa cada 5 s y guarda `MONITORING_RETENTION_DAYS` días (20 por defecto, ≈ 2 GB, en el volumen `prometheus_data`). Evalúa las alertas. |
| `alertmanager` | `docker-compose.monitoring.yml`, `127.0.0.1:9093` | Manda las alertas a ntfy, agrupadas por alerta. |
| `/internal/metrics` | `app/api/internal_metrics.py`, `app/services/platform_metrics.py` | Lo de la plataforma: llamadas activas por modo, canales de Anura ocupados y totales, p95 por turno de las llamadas terminadas en los últimos 15 min (incluye loadtest: es carga real). Pide `Authorization: Bearer $MONITORING_TOKEN`; sin token configurado, o si el pedido llega por Cloudflare, responde 404. |
| API | `app/services/system_status.py`, `app/api/routers/system.py` | `GET /api/v1/system/now` (foto actual), `history?window=1h\|6h\|24h\|7d` (series), `events?window=` (alertas disparadas) y `peaks?days=` (máximo por día). Solo admin: ni un cliente ni un admin en "ver como cliente". Sin Prometheus, 503 `monitoring_off` o `monitoring_down`. |
| Pantalla | `web/src/features/system/`, menú **Sistema** del admin (`/admin/system`) | Ver la sección 3. |
| MCP | `app/mcp/catalog.py` | `get_system_status` y `get_system_events`, en el toolset `admin`. |
| Config generada | `deploy/monitoring/render.py` → `deploy/monitoring/generated/` (no versionado) | `prometheus.yml` (raspados y sondas, con la etiqueta `host`), `alertmanager.yml` (lleva el tema de ntfy) y `app_token`. |

`scripts/ops/healthcheck.sh` (cron, cada 2 min) sigue aparte, como vigía: si Prometheus se cae, el
chequeo sigue avisando por el mismo tema de ntfy.

## 2. Qué se mide y por qué

- **Uso:** CPU, RAM, cada GPU y su VRAM, disco libre, red.
- **Saturación,** que dice si algo espera (más útil que el %):
  - presión de CPU, memoria e IO: % del tiempo con tareas esperando; 100 % de CPU con presión 0 está bien;
  - LLM, TTS y STT: pedidos en curso y en cola; KV cache en uso y total, en tokens, por motor (con Gemma, 63.013 tokens para todas las llamadas desde el arranque del 28-oct-2026: el techo más probable). El total sale de la etiqueta `kv_cache_size_tokens` de `vllm:cache_config_info`; del TTS (talker) solo el %, porque vllm-omni no publica esa métrica; el STT (Parakeet) no tiene KV cache;
  - canales de Anura en uso de 10 y p95 por turno.
- **Potencia y temperatura:** potencia de cada GPU contra su tope (sin tope, dos 3090 apagaron el
  server el 25-sep-2026), motivo de recorte del reloj (un recorte térmico o por hardware es la señal
  más temprana de un problema), temperaturas, errores XID. El consumo total es una **estimación**
  (GPUs + paquete de la CPU): no hay UPS ni medidor de pared, y los picos eléctricos de milisegundos
  no los ve ningún muestreo por software.
- **Disco:** libre, días hasta llenarse al ritmo de las últimas 6 h (recién con 6 h de datos), SMART
  (desgaste, errores de medio, temperatura).
- **Conectividad:** sondas, registro SIP con Anura, IP pública igual a `PUBLIC_HOST`, reloj
  sincronizado (TLS y SIP fallan con la hora corrida), paquetes UDP descartados (audio perdido).
- **Servicios:** solo los contenedores de Atentina. Los de otros proyectos del host (Dify, sim-poc…)
  no se muestran: quedan dentro del total del host. En la VRAM por servicio, el escritorio y los
  procesos ajenos van juntos como "otros".
- **PCIe:** la GPU 0 va en gen3 x4 por el slot. En reposo los enlaces bajan solos por ahorro: solo
  cuenta un enlace más angosto que su máximo de la semana **con carga**.

Resolución: la del raspado, 5 s. Un pico más corto queda promediado; para más detalle en una prueba,
`scripts/capacity/monitor.py` (1 Hz). En los gráficos de ventanas largas, lo que tiene picos (GPU,
potencia, temperatura, llamadas, KV cache) muestra el máximo de cada punto, no el promedio.

## 3. La pantalla Sistema

Se actualiza cada 10 s. De arriba abajo:

1. **Alertas activas:** críticas primero; "(confirmando)" es una alerta que todavía no cumplió su tiempo.
2. **Por server** (agrupado por host si hay más de uno):
   - CPU, RAM, consumo estimado, llamadas activas, canales de Anura y p95 por turno;
   - una tarjeta por GPU, las que haya; la VRAM de la GPU del LLM no se marca en amarillo porque el LLM la reserva a propósito;
   - CPU y memoria (presión, carga, temperatura, swap, OOM) e inferencia (en curso, en cola, KV cache);
   - discos y SMART, servicios, conectividad y red.
3. **Historia** de 1 h, 6 h, 24 h o 7 días: CPU y RAM, uso, potencia, temperatura y VRAM de cada GPU,
   consumo estimado, llamadas activas con el KV cache, red.
4. **Eventos:** cuándo empezó y terminó cada alerta en la ventana, para explicar un pico o una caída.
5. **Picos por día** de los últimos 7.

Un aviso rojo "el colector del host no actualiza" significa que `atentina-hostmon` no corre: faltan
GPUs, servicios, SMART y SIP (`journalctl -u atentina-hostmon`).

## 4. Alertas

Las reglas están en `deploy/monitoring/rules.yml`, cada una con su umbral comentado. Llegan a la app
ntfy del celular, al tema `ALERT_NTFY_TOPIC` (el mismo de `healthcheck.sh`):

| Gravedad | En ntfy | Repite si sigue | Ejemplos |
|---|---|---|---|
| `critical` | "Atentina: crítica", prioridad alta (suena) | cada 1 h | GPU sin tope (> 280 W), recorte térmico o por hardware, GPU > 83 °C, error XID, GPU que desaparece, RAM < 10 %, OOM, disco < 5 %, SMART con fallas, servicio caído o unhealthy, Docker reinició un servicio, sonda que falla, registro SIP caído, IP pública distinta, colector caído |
| `warning` | "Atentina: aviso", prioridad baja (sin sonido) | cada 4 h | potencia de las GPUs > 520 W sostenida (CAP-001: pico de 559 W), VRAM > 97 % fuera del LLM, KV cache > 90 %, cola en la inferencia, p95 por turno > 3 s, 9 de 10 canales de Anura, presión de CPU o disco > 20 %, swap, disco < 15 % o lleno en < 7 días, NVMe gastado > 80 %, reloj sin NTP, host reiniciado, UDP descartado, métricas sin raspar |

Al resolverse llega "Atentina: resuelto". Los umbrales iniciales son los de arriba: al cambiar uno,
anotar en `rules.yml` el porqué medido y correr `make up-monitoring`.

Con el host muy cargado (carga 12 de 16 hilos, 28-oct-2026), las sondas de App y del dashboard por
el túnel fallaron un ciclo cada tanto por el timeout de 5 s; el `for` de 30 s y 1 min evita que eso
avise. Si en producción avisa seguido, mirar la causa antes de subir el umbral.

## 5. Operación

| Para | Comando |
|---|---|
| Instalar en el host (una vez, sudo): `smartmontools`, `lm-sensors` (con `sensors-detect --auto`) y `atentina-hostmon` | `make monitoring-host-install` |
| Crear el tema de ntfy (si falta en `.env`) y mandar un aviso de prueba; después suscribirse en la app ntfy al tema que imprime | `make alert-ntfy-setup` |
| Regenerar la config desde `.env` (crea `MONITORING_TOKEN` si falta: solo agrega una línea al final) | `make monitoring-config` |
| Levantar o actualizar el monitoreo (regenera la config; no toca el stack ni corta llamadas) | `make up-monitoring` |
| Ver qué no se está leyendo y qué alertas hay | `make monitoring-status` |
| Probar el aviso (`SEV=critical` suena) | `make monitoring-test-alert [SEV=critical]` |
| Bajarlo (conserva la historia) | `make monitoring-down` |

Variables de `.env`: `ALERT_NTFY_TOPIC` (tema secreto de ntfy), `MONITORING_TOKEN` (lo crea
`monitoring-config`; `app` lo toma al recrearse), `MONITORING_RETENTION_DAYS` (20),
`MONITORING_HOST` (nombre del server en la pantalla; por defecto, el hostname) y `PROMETHEUS_URL`
(`http://prometheus:9090`).

**Primera puesta en marcha:** `make monitoring-host-install`, `make alert-ntfy-setup`,
`make up-monitoring` (diff enmascarado del `.env` contra el backup antes de seguir),
`make calls-active && make up-app` (recrea solo `app`, para que tome `MONITORING_TOKEN`; hasta ahí
`monitoring-status` muestra `app` caído), `make monitoring-test-alert SEV=critical` y abrir
**Sistema** en el panel del admin. Para sacarlo: `make monitoring-down` y
`sudo systemctl disable --now atentina-hostmon`.

**Otro server:** cada métrica lleva la etiqueta `host`; uno nuevo levanta sus exporters y la
pantalla lo muestra aparte. En una migración, ver [`MIGRACION_SERVER.md`](MIGRACION_SERVER.md), 8.1.1.

## 6. Costo

Medido el 28-oct-2026 con el stack en vivo: 4.594 series y 830 muestras/s (≈ 2 GB en 20 días);
Prometheus 50 MB de RAM y 0,3 % de un núcleo (con tope de 1 GB y 1 núcleo en el compose),
node-exporter 10 MB, blackbox 17 MB; `atentina-hostmon`, 0,16 s por vuelta cada 5 s. La GPU no se
toca más allá de una consulta de `nvidia-smi` cada 5 s.

## 7. Seguridad

- Prometheus, Alertmanager y los exporters escuchan solo en `127.0.0.1` o en la red interna; nada
  por el túnel ni el router. node-exporter monta el host en solo lectura.
- `/internal/metrics` exige `MONITORING_TOKEN` y rechaza lo que llega por Cloudflare.
- `deploy/monitoring/generated/` lleva el tema de ntfy y el token: no se versiona.

## 8. Lo que no cubre

- Rooms de LiveKit, jitter hacia Anura y `/metrics` de `cloudflared`: el túnel se ve por la sonda
  del dashboard y LiveKit por su sonda HTTP.
- Consumo real de pared y picos eléctricos de milisegundos: hace falta un UPS o un medidor.
- Si el server se queda sin luz o sin internet, nadie avisa desde adentro: para eso está
  `HEALTHCHECKS_PING_URL` (healthchecks.io), hoy vacía.
- Trazas por llamada (están en `call_logs.latency` y en Reportes > Técnico) y logs centralizados.
