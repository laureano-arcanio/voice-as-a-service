# Asterisk 22 (LTS) como puente SIP entre la troncal de Anura y LiveKit Cloud.
# Ver docs/TELEFONIA_ANURA.md para la arquitectura y el runbook completo.
#
# Alpine empaqueta Asterisk con chan_pjsip y todos los res_pjsip_* que hacen
# falta, y sin config de ejemplo en /etc/asterisk: toda la config sale de
# asterisk/conf/ (montado en /etc/asterisk/templates, ver docker-compose.yml),
# renderizada por entrypoint.sh al arrancar.
# Base fijada por digest (8-oct-2026, la del build vigente); los paquetes de apk siguen la 3.24.
FROM alpine:3.24@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6

# gettext-envsubst: envsubst para renderizar los templates con los datos de
# Anura/LiveKit de .env. tzdata: logs con hora local (TZ en docker-compose.yml).
# asterisk-srtp: audio cifrado (SDES) de las llamadas de WhatsApp (conf/whatsapp/).
# Asterisk fijado a la 22.9 (la probada, 22.9.0-r0 el 8-oct-2026) con ~: acepta parches
# (22.9.x y -rN), no otra menor. Alpine borra del repo las versiones viejas: fijar -r0 exacto
# rompe el build en cuanto sale un parche. Si falla por la menor, probar la nueva y subirla
# aca. gettext-envsubst y tzdata sin fijar: riesgo aceptado (tzdata tiene que actualizarse).
RUN apk add --no-cache asterisk~22.9 asterisk-srtp~22.9 gettext-envsubst tzdata

# Configs del core que Asterisk lee siempre y que aca no se usan: sin estos
# archivos cada arranque llena el log de "Unable to load config file". CDR y
# CEL van apagados (el registro de llamadas vive en la base de la app).
RUN : > /etc/asterisk/acl.conf \
 && for f in ccss features pjproject udptl; do echo '[general]' > /etc/asterisk/$f.conf; done \
 && printf '[general]\nenable=no\n' > /etc/asterisk/cdr.conf \
 && printf '[general]\nenable=no\n' > /etc/asterisk/cel.conf

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 755 /usr/local/bin/entrypoint.sh

# Asterisk arranca como root solo para renderizar la config (entrypoint.sh) y
# despues baja a asterisk:asterisk con -U/-G.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
