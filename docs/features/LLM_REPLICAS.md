# Réplicas del LLM y balanceo

El LLM propio corre en dos servers: `vllm-llm` en el de producción (192.168.1.99, RTX 3090) y otro `vllm-llm`
igual en server2 (192.168.1.98, `atentina-region-2`, RTX 3090 sola). Un HAProxy (`llm-lb`) en el server de
producción reparte los pedidos de `app` y `agent` entre los dos. Estado: en producción desde el 1-nov-2026.
Capacidad del reparto: sin medir (pendiente, `docs/capacity/`).

## Piezas

| Pieza | Dónde | Qué hace |
|---|---|---|
| `docker-compose.server2.yml` | server2, en `COMPOSE_FILE` con `gemma4-26b` | Solo `vllm-llm`, misma imagen (por digest) y flags que producción; publica `192.168.1.98:8101`. |
| `docker-compose.llm-lb.yml` | producción, en `COMPOSE_FILE` | Servicio `llm-lb` (HAProxy 3.2), `LLM_REPLICA_2=192.168.1.98:8101`; `127.0.0.1:8104` (LLM balanceado) y `127.0.0.1:8404` (estado). |
| `deploy/llm-lb/haproxy.cfg` | producción | Reglas del reparto, con el porqué de cada una. |
| `VLLM_LLM_BASE_URL=http://llm-lb:8000/v1` | `.env` de producción | `app` y `agent` (motor, extracción, API de inferencia, worker de voz) pasan por el balanceador. |
| `X-Atentina-Conversation-Id` | `app/llm/client.py`, `app/voice/worker.py` | Header en cada pedido al servidor propio con el id de la conversación. Es el mismo header que ya recibe "tu propio agente" ([`LLM_CONEXIONES`](LLM_CONEXIONES.md)). |

El `.env` de server2 es mínimo: `COMPOSE_FILE`, la misma `VLLM_API_KEY` que producción (HAProxy no toca la
autenticación: la key viaja al vLLM que toque) y `VLLM_LLM_MODEL`. Pesos en `/home/laureano/Models`, la misma ruta
que producción, así el override `gemma4-26b` sirve sin cambios. Se opera con el agente `server2`
(`.claude/agents/server2.md`): `ssh server2 'cd voice-as-a-service && docker compose up -d --no-deps vllm-llm'`.

## Cómo reparte

- **Menos conexiones** (`leastconn`): un pedido nuevo va a la réplica con menos pedidos en curso.
- **Afinidad por conversación**: la primera vez que HAProxy ve un `X-Atentina-Conversation-Id` elige por
  `leastconn` y lo anota (stick-table, vence a las 2 h sin uso); los turnos siguientes van a la misma réplica.
  Importa porque la API es sin estado (cada turno manda toda la conversación) y lo que vLLM reutiliza es el
  prefix cache, local a cada server (49.000 tokens de KV por 3090). La definición del agente se cachea en los dos
  tras la primera llamada; el historial de la conversación solo donde se atendió el turno anterior.
- **Sin header** (API de inferencia de clientes, pruebas con `curl`): solo `leastconn`.
- Mover la KV entre servers no conviene con esta red: 83 KB por token, 330 MB para 4.000 tokens, ~3 s por LAN
  gigabit, contra menos de 1 s de recalcular ese prefill en la otra 3090.

## Si una réplica cae

- HAProxy pide `GET /health` a cada réplica cada 5 s; 2 fallos la sacan, 2 aciertos la vuelven a meter. Un
  `vllm-llm` que arranca (~140 s) no recibe nada hasta estar sano.
- Si la conexión falla antes de la respuesta, reintenta en la otra réplica. Si falla con el stream empezado,
  el cliente (`LLMClient`, `max_retries=2`) repite el pedido: un par de segundos de silencio en la llamada.
- Las conversaciones que iban a la réplica caída pasan a la otra y recalculan su prefijo una vez.
- Si cae el server de producción, cae todo lo demás (`app`, `agent`, TTS, STT): el balanceador vive acá a
  propósito, no agrega un punto de falla.

## Operación

```
make up-llm-lb        # levanta/recrea solo HAProxy y muestra el estado
make llm-lb-status    # UP/DOWN, pedidos en curso y totales por réplica
make health           # incluye llm-lb (:8104)
```

Cambios en `haproxy.cfg`: `make up-llm-lb` (no corta llamadas: `app` y `agent` reconectan). Cambios en el `.env`
que toquen `VLLM_LLM_BASE_URL`: `make calls-active && make up-agent`.

## Pendientes

- Medir el reparto con el test de capacidad y registrarlo en `docs/capacity/`.
- El proxy público (`proxy/nginx.conf`, ruta `/llm/`) y las sondas del monitoreo (`deploy/monitoring/render.py`)
  siguen apuntando a `vllm-llm` directo; pasarlos por `llm-lb` o sumar server2 a las sondas.
