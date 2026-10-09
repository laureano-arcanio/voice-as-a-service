#!/usr/bin/env bash
# Renovacion del certificado de las llamadas de WhatsApp (cron diario, docs/WHATSAPP_PLAN.md 5.4).
# `make sip-cert` no hace nada hasta que falten menos de 30 dias; cuando renueva, Asterisk sigue
# sirviendo el viejo (lo copia al arrancar), asi que se reinicia el contenedor, solo sin llamadas
# en curso: espera hasta 60 min y si no, reintenta al otro dia (quedan ~30 intentos).
# El chequeo (healthcheck.sh) avisa si el certificado servido vence en menos de 14 dias.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1

env_get() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- || true; }
log() { echo "$(date '+%F %T') $*"; }
C=voice-as-a-service-asterisk-1
host="$(env_get WA_SIP_HOST)"; host="${host:-sip.atentina.com.ar}"

[[ -n "$(env_get WA_SIP_PASSWORD)" ]] || { log "sin WA_SIP_PASSWORD: llamadas de WhatsApp apagadas, nada que renovar"; exit 0; }

make -s sip-cert || { log "ERROR: make sip-cert fallo"; exit 1; }

# Asterisk monta /etc/letsencrypt: si el de live/ es igual al que copio al arrancar, no hay nada que hacer.
same() { docker exec "$C" cmp -s "/etc/letsencrypt/live/$host/fullchain.pem" /etc/asterisk/keys/whatsapp-fullchain.pem; }
if same; then log "certificado al dia"; exit 0; fi

for _ in $(seq 60); do
    calls="$(docker exec "$C" asterisk -rx 'core show channels count' | awk '/active call/ {print $1}')"
    if [[ "$calls" == 0 ]]; then
        # restart y no up-pbx: no hace falta rebuild y entrypoint.sh vuelve a copiar el certificado.
        docker compose restart asterisk >/dev/null 2>&1 && sleep 10
        if same; then log "certificado renovado y cargado en Asterisk"; exit 0; fi
        log "ERROR: Asterisk reiniciado pero sigue con el certificado viejo"; exit 1
    fi
    sleep 60
done
log "postergado: $calls llamadas en curso durante 60 min; reintenta manana"
