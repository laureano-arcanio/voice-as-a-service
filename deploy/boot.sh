#!/usr/bin/env bash
# Levanta el stack en el arranque del host (atentina-stack.service, como el usuario dueño del repo).
# Sin build: usa las imágenes ya construidas. Después del reinicio la inferencia quedaba en
# "Exited (128)" y los trunks SIP de LiveKit se borraban (AGENTS.md): esto lo resuelve.
set -euo pipefail
cd "$(dirname "$0")/.."

log() { echo "[boot $(date '+%F %T')] $*"; }
env_get() { grep -E "^$1=" .env | tail -1 | cut -d= -f2-; }

log "esperando a Docker"
until docker info >/dev/null 2>&1; do sleep 2; done

log "stack (COMPOSE_FILE del .env), esperando healthy hasta 15 min"
docker compose up -d --wait --wait-timeout 900

log "túnel de Cloudflare"
docker compose -f docker-compose.tunnel.yml up -d tunnel

log "trunks SIP y dispatch rule de LiveKit (su Redis no persiste)"
make --no-print-directory livekit-sip-si-local

# El primer pedido al TTS tarda más de 20 s (compilación de kernels): sin calentarlo, la
# primera llamada no recibe el saludo. Nunca sin voz: un pedido sin voice mata vllm-tts.
voice="$(env_get VLLM_TTS_VOICE)"
model="$(env_get VLLM_TTS_MODEL)"
if [[ -n "$voice" && -n "$model" ]]; then
    log "calentando el TTS con la voz $voice"
    curl -sf -o /dev/null --max-time 120 http://127.0.0.1:8103/v1/audio/speech \
        -H "Authorization: Bearer $(env_get VLLM_API_KEY)" -H "Content-Type: application/json" \
        -d "{\"model\":\"$model\",\"voice\":\"$voice\",\"input\":\"Hola, te habla el agente.\",\"response_format\":\"wav\"}" \
        && log "TTS caliente" || log "AVISO: el calentamiento del TTS falló"
else
    log "AVISO: sin VLLM_TTS_VOICE o VLLM_TTS_MODEL en .env, no se calienta el TTS"
fi
log "listo"
