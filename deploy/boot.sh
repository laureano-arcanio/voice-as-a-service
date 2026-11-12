#!/usr/bin/env bash
# Levanta el stack en el arranque del host (atentina-stack.service, como el usuario dueño del repo).
# Sin build: usa las imágenes ya construidas. Un paso que falla no corta los siguientes (los trunks
# SIP corren siempre: sin ellos toda entrante da 486); al final sale con 1 si algo quedó mal.
set -uo pipefail
cd "$(dirname "$0")/.."

log() { echo "[boot $(date '+%F %T')] $*"; }
env_get() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- || true; }
failed=()
fail() { log "AVISO: $1"; failed+=("$1"); }
has_service() { docker compose config --services 2>/dev/null | grep -qx "$1"; }

log "esperando a Docker"
until docker info >/dev/null 2>&1; do sleep 2; done

# El disco de datos (fstab, antes de Docker): sin él, los audios caerían en el disco del sistema.
disk="$(env_get DATA_DISK)"
if [[ -n "$disk" ]] && ! mountpoint -q "$disk"; then
    log "disco de datos $disk sin montar: reintentando"
    sudo -n mount "$disk" || fail "no se pudo montar $disk"
fi

# Si un contenedor falla en su primer arranque, Docker lo reinicia y suele quedar healthy, pero el
# --wait ya falló y los que dependen de él quedaron sin crear: un segundo up los levanta.
log "stack (COMPOSE_FILE del .env), esperando healthy hasta 15 min"
if ! docker compose up -d --wait --wait-timeout 900; then
    log "AVISO: el stack no quedó healthy; segundo intento, hasta 5 min"
    docker compose up -d --wait --wait-timeout 300 || fail "el stack no quedó healthy (docker compose ps)"
fi

# La réplica de inferencia (docker-compose.replica.yml) no lleva túnel: su .env no tiene el token.
if [[ -n "$(env_get CLOUDFLARE_TUNNEL_TOKEN)" ]]; then
    log "túnel de Cloudflare"
    docker compose -f docker-compose.tunnel.yml up -d tunnel || fail "el túnel no arrancó"
fi

# Con LiveKit propio (su Redis no persiste); con Cloud o en la réplica, livekit-sip-si-local no hace
# nada. Cada intento espera hasta 90 s a que LiveKit responda; además, cron lo repone cada 5 min.
log "trunks SIP y dispatch rule de LiveKit"
for i in 1 2 3 4; do
    make --no-print-directory livekit-sip-si-local && break
    if (( i == 4 )); then fail "trunks SIP sin crear: entrantes con 486 (make livekit-sip)"; break; fi
    log "AVISO: trunks SIP, intento $i falló; reintento en 30 s"
    sleep 30
done

# El primer pedido al TTS tarda más de 20 s (compilación de kernels): sin calentarlo, la
# primera llamada no recibe el saludo. Nunca sin voz: un pedido sin voice mata vllm-tts.
voice="$(env_get VLLM_TTS_VOICE)"
model="$(env_get VLLM_TTS_MODEL)"
if ! has_service vllm-tts; then
    log "sin vllm-tts en este host, no se calienta el TTS"
elif [[ -z "$voice" || -z "$model" ]]; then
    log "AVISO: sin VLLM_TTS_VOICE o VLLM_TTS_MODEL en .env, no se calienta el TTS"
else
    log "esperando a que vllm-tts esté healthy (hasta 5 min)"
    health=""
    for _ in $(seq 60); do
        health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{end}}' \
            "$(docker compose ps -q vllm-tts 2>/dev/null)" 2>/dev/null || true)"
        [[ "$health" == healthy ]] && break
        sleep 5
    done
    if [[ "$health" != healthy ]]; then
        fail "vllm-tts no quedó healthy (${health:-sin contenedor}): TTS sin calentar"
    else
        log "calentando el TTS con la voz $voice"
        curl -sf -o /dev/null --max-time 120 http://127.0.0.1:8103/v1/audio/speech \
            -H "Authorization: Bearer $(env_get VLLM_API_KEY)" -H "Content-Type: application/json" \
            -d "{\"model\":\"$model\",\"voice\":\"$voice\",\"input\":\"Hola, te habla el agente.\",\"response_format\":\"wav\"}" \
            && log "TTS caliente" || fail "el calentamiento del TTS falló"
    fi
fi

# Registros (perfil de compose, fuera del up de arriba). La clave significa "activo en este host".
# Sin --wait y a lo último: su falla no le quita a este server llamadas ni WhatsApp (no cuenta como falla).
if [[ -n "$(env_get REGISTROS_HEALTH_URL)" ]]; then
    log "Registros"
    docker compose --profile registros up -d --no-deps registros || log "AVISO: Registros no arrancó"
fi

if (( ${#failed[@]} )); then
    log "terminó con fallas:"
    printf '  - %s\n' "${failed[@]}"
    exit 1
fi
log "listo"
