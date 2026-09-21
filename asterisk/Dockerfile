# Asterisk 22 (LTS) como puente SIP entre la troncal de Anura y LiveKit Cloud.
# Ver docs/TELEFONIA_ANURA.md para la arquitectura y el runbook completo.
#
# Alpine empaqueta Asterisk con chan_pjsip y todos los res_pjsip_* que hacen
# falta, y sin config de ejemplo en /etc/asterisk: toda la config sale de
# asterisk/conf/ (montado en /etc/asterisk/templates, ver docker-compose.yml),
# renderizada por entrypoint.sh al arrancar.
FROM alpine:3.24

# gettext-envsubst: envsubst para renderizar los templates con los datos de
# Anura/LiveKit de .env. tzdata: logs con hora local (TZ en docker-compose.yml).
RUN apk add --no-cache asterisk gettext-envsubst tzdata

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
