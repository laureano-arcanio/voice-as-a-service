# Réplica de inferencia y balanceo

server2 (`192.168.1.98`, `atentina-region-2`) corre todo el stack. El otro server (`192.168.1.99`) corre solo LLM, STT y
TTS. Un HAProxy (`llm-lb`) en server2 reparte entre los dos los pedidos de `app` y `agent`. Estado: en producción desde
el 2-nov-2026. Capacidad del reparto: sin medir (pendiente, `docs/capacity/`).

## Piezas

| Pieza | Dónde | Qué hace |
|---|---|---|
| `docker-compose.replica.yml` | réplica, en `COMPOSE_FILE` | Publica `vllm-llm`, `stt-parakeet` y `vllm-tts` en `REPLICA_BIND_IP` (`:8101`, `:8102`, `:8103`) y deja el resto del stack fuera con un perfil. `STACK_ROLE=replica` hace que `make up*` se niegue. |
| `docker-compose.llm-lb.yml` | server2, en `COMPOSE_FILE` | Servicio `llm-lb` (HAProxy 3.2), réplicas en `LLM_REPLICA_2`, `STT_REPLICA_2` y `TTS_REPLICA_2`; en el host `127.0.0.1:8104` (LLM), `:8105` (STT), `:8106` (TTS) y `:8404` (estado). |
| `deploy/llm-lb/haproxy.cfg` | server2 | Reglas del reparto, con el porqué de cada una. |
| `VLLM_{LLM,STT,TTS}_BASE_URL=http://llm-lb:{8000,8001,8002}/v1` | `.env` de server2 | `app` y `agent` pasan por el balanceador. |
| `X-Atentina-Conversation-Id` | `app/llm/client.py`, `app/voice/worker.py` | Header en cada pedido al LLM propio con el id de la conversación. Es el mismo header que ya recibe "tu propio agente" ([`LLM_CONEXIONES`](LLM_CONEXIONES.md)). |
| `INFERENCE_REPLICA_HOST` | `.env` de server2 | Prometheus sondea los tres modelos de la réplica y avisa si caen. |

La misma `VLLM_API_KEY` en los dos: HAProxy no toca la autenticación. En la réplica no van el token del túnel, la clave de
Anura ni `LIVEKIT_URL`: nunca dos Asterisk, dos `cloudflared` ni dos `agent`. Arranca sola con `atentina-stack`, solo los modelos.

## Cómo reparte

- **Menos conexiones** (`leastconn`): un pedido nuevo va a la réplica con menos pedidos en curso.
- **Afinidad por conversación**: la primera vez que HAProxy ve un `X-Atentina-Conversation-Id` elige por
  `leastconn` y lo anota (stick-table, vence a las 2 h sin uso); los turnos siguientes van a la misma réplica.
  Importa porque la API es sin estado (cada turno manda toda la conversación) y lo que vLLM reutiliza es el
  prefix cache, local a cada server (49.000 tokens de KV por 3090). La definición del agente se cachea en los dos
  tras la primera llamada; el historial de la conversación solo donde se atendió el turno anterior.
- **Sin header** (API de inferencia de clientes, pruebas con `curl`): solo `leastconn`.
- **STT y TTS:** solo `leastconn`, sin afinidad: no guardan nada entre pedidos. Tres 5xx seguidos sacan una réplica del TTS
  aunque `/health` responda, porque el talker se cae con el contenedor sano ([`INFRA`](../INFRA.md)); el chequeo la vuelve a meter.
- Mover la KV entre servers no conviene con esta red: 83 KB por token, 330 MB para 4.000 tokens, ~3 s por LAN
  gigabit, contra menos de 1 s de recalcular ese prefill en la otra 3090.

## Si una réplica cae

- HAProxy pide `GET /health` a cada réplica cada 5 s; 2 fallos la sacan, 2 aciertos la vuelven a meter. Un
  modelo que arranca no recibe nada hasta estar sano (recargar los tres en la réplica: 251 s).
- Si la conexión falla antes de la respuesta, reintenta en la otra réplica. Si falla con el stream empezado,
  el cliente (`LLMClient`, `max_retries=2`) repite el pedido: un par de segundos de silencio en la llamada.
- Las conversaciones que iban a la réplica caída pasan a la otra y recalculan su prefijo una vez.
- Si cae la réplica, server2 sigue solo. Si cae server2, cae el servicio (`app`, `agent`, base, LiveKit, Asterisk): la
  réplica no lo reemplaza, solo aporta capacidad. El balanceador vive en server2 a propósito: no agrega un punto de falla.

## Operación

```
# En server2:
make up-llm-lb        # levanta/recrea solo HAProxy y muestra el estado
make llm-lb-status    # UP/DOWN, pedidos en curso y totales por réplica y motor
make health           # incluye llm-lb (:8104, :8105, :8106)
# En la réplica:
make up-inference     # recarga los tres modelos (~4 min); server2 sigue atendiendo
```

Cambios en `haproxy.cfg`: `make up-llm-lb` (no corta llamadas: `app` y `agent` reconectan). Cambios en el `.env`
que toquen `VLLM_LLM_BASE_URL`: `make calls-active && make up-agent`.

## Pendientes

- Medir el reparto con el test de capacidad y registrarlo en `docs/capacity/`.
- El proxy (`proxy/nginx.conf`) sigue apuntando a los modelos locales de server2, sin pasar por `llm-lb`.
- GPU y temperatura de la réplica no llegan a Prometheus: solo se sondea que respondan sus modelos.
