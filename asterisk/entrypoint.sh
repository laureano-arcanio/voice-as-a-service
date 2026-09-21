#!/bin/sh
# Renderiza /etc/asterisk/templates/*.conf -> /etc/asterisk/ con los valores de
# .env (pasados por docker-compose.yml) y arranca Asterisk en foreground.
#
# envsubst recibe una lista EXPLICITA de variables: sin eso reemplazaria
# tambien las variables propias del dialplan (${EXTEN}, ${CALLERID(num)}, ...)
# por strings vacios.
set -eu

require() {
	eval "val=\${$1:-}"
	if [ -z "$val" ]; then
		echo "FATAL: falta $1 en .env (ver docs/TELEFONIA_ANURA.md)" >&2
		exit 1
	fi
}

for v in ANURA_DOMAIN ANURA_USER ANURA_PASSWORD ANURA_DID LIVEKIT_SIP_HOST LIVEKIT_SIP_PASSWORD; do
	require "$v"
done

# ANURA_DID va en formato nacional de 10 digitos (ej. 1152630861): es el que
# usa Anura en el string de registro y el que muestra como caller ID.
case "$ANURA_DID" in
	[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]) ;;
	*) echo "FATAL: ANURA_DID tiene que ser el numero nacional de 10 digitos, sin 0 ni 15 ni +54 (ej. 1152630861)" >&2; exit 1 ;;
esac

# Se acepta pegado tal cual lo muestra el dashboard de LiveKit (sip:xxx...).
export LIVEKIT_SIP_HOST="${LIVEKIT_SIP_HOST#sip:}"

export ANURA_PORT="${ANURA_PORT:-55090}"
export ASTERISK_SIP_PORT="${ASTERISK_SIP_PORT:-5080}"
export ASTERISK_ANURA_SIP_PORT="${ASTERISK_ANURA_SIP_PORT:-5081}"
export ASTERISK_RTP_START="${ASTERISK_RTP_START:-10000}"
export ASTERISK_RTP_END="${ASTERISK_RTP_END:-10199}"

# Direccion publica que Asterisk anuncia en Contact/SDP (esta detras del NAT
# del router). Vacia = autodetectar al arrancar; si la IP del ISP cambia hay
# que reiniciar el contenedor (y actualizar el trunk saliente de LiveKit, ver
# docs) -- con un hostname de DDNS en ASTERISK_PUBLIC_ADDRESS no hace falta.
if [ -z "${ASTERISK_PUBLIC_ADDRESS:-}" ]; then
	ASTERISK_PUBLIC_ADDRESS="$(wget -qO- -T 5 https://api.ipify.org 2>/dev/null || wget -qO- -T 5 https://ifconfig.me 2>/dev/null || true)"
	if [ -z "$ASTERISK_PUBLIC_ADDRESS" ]; then
		echo "FATAL: no se pudo detectar la IP publica; definir ASTERISK_PUBLIC_ADDRESS en .env" >&2
		exit 1
	fi
	echo "IP publica autodetectada: $ASTERISK_PUBLIC_ADDRESS"
fi
export ASTERISK_PUBLIC_ADDRESS

VARS='${ANURA_DOMAIN} ${ANURA_PORT} ${ANURA_USER} ${ANURA_PASSWORD} ${ANURA_DID}
${LIVEKIT_SIP_HOST} ${LIVEKIT_SIP_PASSWORD}
${ASTERISK_PUBLIC_ADDRESS} ${ASTERISK_SIP_PORT} ${ASTERISK_ANURA_SIP_PORT} ${ASTERISK_RTP_START} ${ASTERISK_RTP_END}'

for tpl in /etc/asterisk/templates/*.conf; do
	out="/etc/asterisk/$(basename "$tpl")"
	envsubst "$VARS" <"$tpl" >"$out"
	# pjsip.conf lleva las passwords de Anura y LiveKit.
	chown root:asterisk "$out"
	chmod 640 "$out"
done

echo "Asterisk: SIP udp/${ASTERISK_SIP_PORT} (LiveKit) y udp/${ASTERISK_ANURA_SIP_PORT} (Anura), RTP ${ASTERISK_RTP_START}-${ASTERISK_RTP_END}, publico ${ASTERISK_PUBLIC_ADDRESS}"
exec asterisk -f -U asterisk -G asterisk
