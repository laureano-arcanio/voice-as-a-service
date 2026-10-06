#!/usr/bin/env bash
# Chequeo del servicio (cron cada 2 min, docs/PRODUCCION.md 3.F). Avisa solo cuando cambia el
# estado (cae o vuelve), por ntfy (ALERT_NTFY_TOPIC en .env: tema secreto de https://ntfy.sh, se
# sigue con la app ntfy en el celular). Si HEALTHCHECKS_PING_URL está en .env, le avisa a un
# vigilante externo (ej. healthchecks.io) que este host está vivo: si el host o internet se caen,
# el aviso lo da él, porque este script ya no corre.
set -uo pipefail
cd "$(dirname "$0")/../.."

env_get() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- || true; }
STATE_DIR="${OPS_STATE_DIR:-$HOME/atentina-ops}"
mkdir -p "$STATE_DIR"
problems=()

# Contenedores del stack que no están corriendo (incluye el túnel, que va en otro compose).
expected="$(docker compose config --services 2>/dev/null) tunnel"
for svc in $expected; do
    [[ "$svc" == "migrate" ]] && continue          # corre una vez y termina
    state="$(docker inspect -f '{{.State.Status}}' "voice-as-a-service-$svc-1" 2>/dev/null || echo ausente)"
    [[ "$state" == "running" ]] || problems+=("$svc: $state")
done

# App local y, por el túnel, el dashboard y el webhook de WhatsApp (403 = llega y rechaza el token).
code() { curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$1"; }
[[ "$(code http://127.0.0.1:8011/health)" == 200 ]] || problems+=("app local sin /health")
[[ "$(code https://app.atentina.com.ar/health)" == 200 ]] || problems+=("dashboard público sin /health")
[[ "$(code 'https://wa.atentina.com.ar/wa/webhook?hub.mode=subscribe&hub.verify_token=x&hub.challenge=1')" == 403 ]] \
    || problems+=("webhook de WhatsApp no responde")

# Tope de potencia de las 3090 (sin él, dos 3090 apagaron el server).
while IFS=, read -r idx name limit; do
    [[ "$name" == *3090* ]] || continue
    w="${limit%%.*}"; w="${w// /}"
    (( w <= ${GPU_POWER_W:-280} )) || problems+=("GPU$idx sin tope de potencia (${w} W)")
done < <(nvidia-smi --query-gpu=index,name,power.limit --format=csv,noheader,nounits 2>/dev/null)

# Certificado que sirve Asterisk a Meta (llamadas de WhatsApp): renovarlo es sip-cert-renew.sh.
if [[ -n "$(env_get WA_SIP_PASSWORD)" ]]; then
    echo | timeout 5 openssl s_client -tls1_2 -connect 127.0.0.1:"$(env_get WA_SIP_PORT | grep . || echo 5061)" 2>/dev/null \
        | openssl x509 -noout -checkend $((14 * 86400)) >/dev/null 2>&1 \
        || problems+=("certificado SIP de WhatsApp vencido, por vencer (<14 días) o sin TLS en el 5061")
fi

status="ok"; detail="todo bien"
if ((${#problems[@]})); then status="falla"; detail="$(IFS='; '; echo "${problems[*]}")"; fi

last="$(cat "$STATE_DIR/health.state" 2>/dev/null || echo ok)"
echo "$status" > "$STATE_DIR/health.state"
echo "$(date '+%F %T') $status $detail" >> "$STATE_DIR/health.log"

topic="$(env_get ALERT_NTFY_TOPIC)"
if [[ -n "$topic" && ( "$status" != "$last" || ( "$status" == falla && -n "$(find "$STATE_DIR/health.state" -mmin +60 2>/dev/null)" ) ) ]]; then
    title="Atentina: $([[ $status == ok ]] && echo 'servicio normal' || echo 'FALLA')"
    curl -s -o /dev/null --max-time 10 -H "Title: $title" -H "Priority: $([[ $status == ok ]] && echo default || echo high)" \
        -d "$detail" "https://ntfy.sh/$topic"
fi

ping_url="$(env_get HEALTHCHECKS_PING_URL)"
if [[ -n "$ping_url" ]]; then
    curl -s -o /dev/null --max-time 10 "$ping_url$([[ $status == ok ]] || echo /fail)" --data-raw "$detail"
fi
[[ "$status" == ok ]]
