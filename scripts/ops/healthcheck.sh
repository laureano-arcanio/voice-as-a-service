#!/usr/bin/env bash
# Chequeo del servicio (cron cada 2 min, docs/PRODUCCION.md 3.F). Avisa cuando cambia el estado
# (cae o vuelve) y, mientras siga en falla, una vez por hora, por ntfy (ALERT_NTFY_TOPIC en .env:
# tema secreto de https://ntfy.sh, se sigue con la app ntfy en el celular). Si
# HEALTHCHECKS_PING_URL está en .env, le avisa a un vigilante externo (ej. healthchecks.io) que
# este host está vivo: si el host o internet se caen, el aviso lo da él, porque este script ya no
# corre. Sin ninguno de los dos, las fallas solo quedan en health.log (lo anota una vez por día).
#
# Estado en OPS_STATE_DIR (default ~/atentina-ops): health.state (ok/falla), health.alerted (hora
# del último aviso enviado; antes era el mtime de health.state, que se reescribe cada 2 min y el
# recordatorio horario nunca salía), notice.* (avisos diarios) y trunks.* (chequeo de LiveKit).
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1

env_get() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- || true; }
STATE_DIR="${OPS_STATE_DIR:-$HOME/atentina-ops}"
LOG="$STATE_DIR/health.log"
mkdir -p "$STATE_DIR"
problems=()

log() { echo "$(date '+%F %T') $*" >> "$LOG"; }
# Aviso informativo (no es falla ni dispara ntfy), a lo sumo una vez por día por clave.
notice_daily() {
    local f="$STATE_DIR/notice.$1"
    [[ -n "$(find "$f" -mmin -1440 2>/dev/null)" ]] && return 0
    touch "$f"; log "aviso $2"
}
fresh() { [[ -n "$(find "$1" -mmin "-$2" 2>/dev/null)" ]]; }   # archivo $1 con menos de $2 min

# Contenedores del stack (incluye el túnel, que va en otro compose): corriendo y, si tienen
# healthcheck, no unhealthy ("starting" no es falla: es el arranque).
services="$(docker compose config --services 2>/dev/null)"
for svc in $services tunnel; do
    [[ "$svc" == "migrate" ]] && continue          # corre una vez y termina
    read -r state health < <(docker inspect -f '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}' \
        "voice-as-a-service-$svc-1" 2>/dev/null || echo "ausente -")
    if [[ "$state" != "running" ]]; then problems+=("$svc: $state")
    elif [[ "$health" == "unhealthy" ]]; then problems+=("$svc: unhealthy")
    fi
done

# App local y, por el túnel, el dashboard y el webhook de WhatsApp (403 = llega y rechaza el token).
code() { curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$1"; }
[[ "$(code http://127.0.0.1:8011/health)" == 200 ]] || problems+=("app local sin /health")
[[ "$(code https://app.atentina.com.ar/health)" == 200 ]] || problems+=("dashboard público sin /health")
[[ "$(code 'https://wa.atentina.com.ar/wa/webhook?hub.mode=subscribe&hub.verify_token=x&hub.challenge=1')" == 403 ]] \
    || problems+=("webhook de WhatsApp no responde")

# /health/ready: la app con sus dependencias (base, inferencia), en JSON. Una versión sin el
# endpoint da 404 o el index.html de la UI (la SPA responde 200 a cualquier ruta).
ready="$(curl -s --max-time 15 -w '\n%{http_code} %{content_type}' http://127.0.0.1:8011/health/ready)"
ready_code="${ready##*$'\n'}"
[[ "$ready_code" == 404* || "$ready_code" == *text/html* ]] && ready_code="sin-endpoint"
case "${ready_code%% *}" in
    200) ;;
    sin-endpoint) notice_daily ready "app sin /health/ready (todavía no desplegado): solo se mira /health" ;;
    *)   body="$(head -c 150 <<<"${ready%$'\n'*}" | tr -s '\n\t' '  ')"
         problems+=("app no lista (/health/ready ${ready_code%% *}: ${body:-sin respuesta})") ;;
esac

# Topes de las 3090 (sin ellos, dos 3090 apagaron el server): potencia siempre; relojes de núcleo
# y memoria (-lgc/-lmc de deploy/gpu-limits.sh), que nvidia-smi no informa: se mira el reloj
# actual, así que un tope perdido solo se ve con la GPU trabajando (en reposo, 210/405 MHz).
power_max="${GPU_POWER_W:-280}"
core_max="${GPU_CORE_MHZ:-210,1800}"; core_max="${core_max##*,}"
mem_max="${GPU_MEM_MHZ:-405,9501}"; mem_max="${mem_max##*,}"
n3090=0
while IFS=, read -r idx name limit sm mem; do
    [[ "$name" == *3090* ]] || continue
    n3090=$((n3090 + 1)); idx="${idx// /}"
    w="${limit%%.*}"; w="${w// /}"; sm="${sm// /}"; mem="${mem// /}"
    (( w <= power_max )) || problems+=("GPU$idx sin tope de potencia (${w} W)")
    [[ "$sm" =~ ^[0-9]+$ ]] && (( sm > core_max + 15 )) && problems+=("GPU$idx sin tope de núcleo (${sm} MHz)")
    [[ "$mem" =~ ^[0-9]+$ ]] && (( mem > mem_max + 15 )) && problems+=("GPU$idx sin tope de memoria (${mem} MHz)")
done < <(nvidia-smi --query-gpu=index,name,power.limit,clocks.sm,clocks.mem --format=csv,noheader,nounits 2>/dev/null)
(( n3090 > 0 )) || problems+=("nvidia-smi no ve las 3090")

# Certificado que sirve Asterisk a Meta (llamadas de WhatsApp): renovarlo es sip-cert-renew.sh.
# Del 6-oct 10:28 al 8-oct 08:12 falló porque Asterisk servía solo TLS 1.0 (arrancó antes de
# method=sslv23; el handshake 1.2 daba "unsupported protocol") y no por el certificado: por eso
# se separan los dos casos. SNI y un reintento para no confundir un corte de un segundo.
if [[ -n "$(env_get WA_SIP_PASSWORD)" ]]; then
    sip_host="$(env_get WA_SIP_HOST)"; sip_host="${sip_host:-sip.atentina.com.ar}"
    sip_port="$(env_get WA_SIP_PORT)"; sip_port="${sip_port:-5061}"
    pem=""
    for try in 1 2; do
        pem="$(echo | timeout 5 openssl s_client -tls1_2 -servername "$sip_host" -connect "127.0.0.1:$sip_port" 2>/dev/null \
            | openssl x509 2>/dev/null)" && [[ -n "$pem" ]] && break
        (( try == 1 )) && sleep 3
    done
    if [[ -z "$pem" ]]; then
        problems+=("SIP de WhatsApp sin TLS 1.2 en el $sip_port (Asterisk caído o con config vieja: make up-pbx)")
    elif ! openssl x509 -noout -checkend $((14 * 86400)) <<<"$pem" >/dev/null 2>&1; then
        problems+=("certificado SIP de WhatsApp vencido o por vencer (<14 días): scripts/ops/sip-cert-renew.sh")
    fi
fi

# Trunks SIP y dispatch rule del LiveKit propio: sin ellos las entrantes dan 486 "flood". Cada
# 10 min (levanta un contenedor efímero de app, como make livekit-sip). --check sale con 0 si
# está todo, o con 1 y un renglón "SIP de LiveKit: ..." por problema (falta un objeto, números o
# max_call_duration desactualizados): entonces corre make livekit-sip y avisa. Otra salida
# (traceback, LiveKit caído) es falla del chequeo, sin reparar.
# Ojo: los dos montan scripts/ del árbol sobre la imagen de app desplegada. Si el script es más
# nuevo que esa imagen, puede pedir código que la imagen no tiene (8-oct-2026: make livekit-sip
# falló por un setting nuevo): el chequeo queda en pausa hasta el próximo build.
if grep -qx livekit <<<"$services"; then
    app_image="$(docker inspect -f '{{.Image}}' voice-as-a-service-app-1 2>/dev/null)"
    image_ts="$(date -d "$(docker image inspect -f '{{.Created}}' "$app_image" 2>/dev/null)" +%s 2>/dev/null || echo 0)"
    if ! grep -q -- '--check' scripts/livekit_sip_setup.py 2>/dev/null; then
        notice_daily trunks "scripts/livekit_sip_setup.py sin --check: no se miran los trunks SIP de LiveKit"
    elif (( $(date -r scripts/livekit_sip_setup.py +%s) > image_ts )); then
        notice_daily trunks "scripts/livekit_sip_setup.py es más nuevo que la imagen de app: chequeo de trunks SIP en pausa hasta el próximo build"
        : > "$STATE_DIR/trunks.problem"
    else
        if ! fresh "$STATE_DIR/trunks.checked" 10; then
            touch "$STATE_DIR/trunks.checked"
            out="$(timeout 120 docker compose run --rm --no-deps -T -v "$PWD/scripts:/app/scripts" app \
                python -m scripts.livekit_sip_setup --check 2>&1)"; rc=$?
            found="$(grep '^SIP de LiveKit: ' <<<"$out" | grep -v ': ok' | sed 's/^SIP de LiveKit: //; s/ (correr .*//' | paste -sd ',' -)"
            if (( rc == 0 )); then
                : > "$STATE_DIR/trunks.problem"
            elif (( rc == 1 )) && [[ -n "$found" ]]; then
                if timeout 300 make --no-print-directory livekit-sip >> "$STATE_DIR/livekit-sip.log" 2>&1; then
                    problems+=("trunks SIP de LiveKit ($found): reparados con make livekit-sip")
                    : > "$STATE_DIR/trunks.problem"
                else
                    echo "trunks SIP de LiveKit ($found) y make livekit-sip falló (livekit-sip.log)" > "$STATE_DIR/trunks.problem"
                fi
            else
                echo "chequeo de trunks SIP falló ($rc): $(tail -c 120 <<<"$out" | tr -s '\n\t' '  ')" \
                    > "$STATE_DIR/trunks.problem"
            fi
        fi
        # Entre chequeos vale el último resultado, para que el estado no oscile cada 2 min.
        trunks="$(cat "$STATE_DIR/trunks.problem" 2>/dev/null)"
        [[ -n "$trunks" ]] && problems+=("$trunks")
    fi
fi

# Backup diario de las 03:30 (backup.sh deja backup.ok al terminar bien): menos de 26 h. Sin
# backup.ok todavía, vale el último dump de la base.
bdir="${BACKUP_DIR:-$HOME/atentina-backups}"
last_backup="$STATE_DIR/backup.ok"
[[ -f "$last_backup" ]] || last_backup="$(find "$bdir/db" -name 'db-*.sql.gz' -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)"
if [[ -z "$last_backup" ]]; then problems+=("sin backups en $bdir")
elif ! fresh "$last_backup" 1560; then problems+=("último backup de hace más de 26 h (backup.log)")
fi
if [[ -n "$(env_get RCLONE_REMOTE)" ]] && ! fresh "$STATE_DIR/backup-remote.ok" 1560; then
    problems+=("copia externa del backup de hace más de 26 h o nunca hecha (backup.log)")
fi

status="ok"; detail="todo bien"
if ((${#problems[@]})); then status="falla"; detail="$(IFS='; '; echo "${problems[*]}")"; fi

last="$(cat "$STATE_DIR/health.state" 2>/dev/null || echo ok)"
echo "$status" > "$STATE_DIR/health.state"
log "$status $detail"

topic="$(env_get ALERT_NTFY_TOPIC)"
ping_url="$(env_get HEALTHCHECKS_PING_URL)"
[[ -z "$topic" && -z "$ping_url" ]] \
    && notice_daily sin-alertas "sin ALERT_NTFY_TOPIC ni HEALTHCHECKS_PING_URL en .env: las fallas no le avisan a nadie"

# Avisa al cambiar de estado y, en falla, cada hora (health.alerted se toca solo al enviar).
if [[ -n "$topic" ]] && { [[ "$status" != "$last" ]] || { [[ "$status" == falla ]] && ! fresh "$STATE_DIR/health.alerted" 60; }; }; then
    title="Atentina: $([[ $status == ok ]] && echo 'servicio normal' || echo 'FALLA')"
    curl -sf -o /dev/null --max-time 10 -H "Title: $title" -H "Priority: $([[ $status == ok ]] && echo default || echo high)" \
        -d "$detail" "https://ntfy.sh/$topic" && touch "$STATE_DIR/health.alerted"
fi

if [[ -n "$ping_url" ]]; then
    curl -s -o /dev/null --max-time 10 "$ping_url$([[ $status == ok ]] || echo /fail)" --data-raw "$detail"
fi
[[ "$status" == ok ]]
