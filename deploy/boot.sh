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

# Un servicio que no llega a healthy (ej. el agent en bucle porque el TTS no sirve
# VLLM_TTS_VOICE) no frena el resto: sin túnel se caen el dashboard público, el webhook de
# WhatsApp y la demo. Se sigue, y el servicio termina con error al final (systemctl status).
rc=0
log "stack (COMPOSE_FILE del .env), esperando healthy hasta 15 min"
docker compose up -d --wait --wait-timeout 900 || { rc=1; log "AVISO: el stack no quedó healthy; sigo con el resto"; }

log "túnel de Cloudflare"
docker compose -f docker-compose.tunnel.yml up -d tunnel || { rc=1; log "AVISO: el túnel no levantó"; }

# Desde el 8-oct-2026 el Redis de LiveKit persiste (AOF): esto queda por si se perdió el
# volumen o cambiaron los números. Idempotente; healthcheck.sh también lo repara.
log "trunks SIP y dispatch rule de LiveKit"
make --no-print-directory livekit-sip-si-local || { rc=1; log "AVISO: falló la carga de trunks SIP"; }

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
log "listo (rc=$rc)"
exit "$rc"
