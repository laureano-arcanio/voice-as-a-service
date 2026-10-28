# Telefonía: Anura, Asterisk y LiveKit

Cómo llegan y salen las llamadas telefónicas: la troncal SIP de [Anura](https://kb.anura.com.ar/es/)
se conecta por un Asterisk en Docker con el LiveKit propio de este host, que despacha el agente.
Estado: en producción desde el 2-oct-2026. Infraestructura general en [`INFRA.md`](INFRA.md); puertos
del router en [`MIGRACION_SERVER.md`](MIGRACION_SERVER.md), 6.

## 1. Arquitectura

```
                 ENTRANTE: alguien llama a un número de la cuenta
 Teléfono ── PSTN ── Anura ──────────► Asterisk ──────────► livekit-sip ──► livekit ──► room anura-*
                    (grancentral) SIP  :5081 (Anura)   SIP  127.0.0.1:5060   :7880       + agent
                    :55090/udp         :5080 (LiveKit)
                                   ◄──────────────     ◄──────────────
                 SALIENTE: el agente marca (create_sip_participant)
```

Todo menos el tramo de Anura queda dentro del host: `asterisk`, `livekit` y `livekit-sip` corren con
`network_mode: host` y se hablan por `127.0.0.1`.

**Por qué Asterisk.** La troncal de Anura funciona por *registro*: un equipo se registra con usuario y
clave, y Anura le manda las entrantes a la dirección registrada. LiveKit no se registra contra
proveedores, solo recibe INVITEs. Asterisk hace el registro, traduce los formatos de número (Anura usa
nacional, LiveKit E.164) y controla quién usa la troncal.

**Entrante:**
1. Asterisk se registra en `ANURA_DOMAIN:55090` con `ANURA_USER`/`ANURA_PASSWORD` (`expiration=120`).
2. Anura manda el INVITE al 5081 por el agujero que abrió el registro; Asterisk lo reconoce por IP
   (las redes de Anura).
3. `from-anura` lo reenvía a `LIVEKIT_SIP_HOST` (`127.0.0.1:5060`) con destino `+54<número marcado>`
   (o `+54<ANURA_DID>` si no llega uno válido), autenticado con usuario `livekit` y `LIVEKIT_SIP_PASSWORD`.
   El caller ID va en E.164 (`+54...`): es el teléfono que guarda la llamada.
4. El inbound trunk de LiveKit la acepta; la dispatch rule crea una room `anura-*` y despacha el agente
   (`LIVEKIT_AGENT_NAME`).
5. El worker (`app/voice/worker.py`) busca el número marcado (`sip.trunkPhoneNumber`) en `phone_numbers`
   y atiende con su agente (o con el equipo, si el número está en `answer_mode=team`; ver
   [`features/EQUIPO_TELEFONIA.md`](features/EQUIPO_TELEFONIA.md)). Número libre o sin agente: corta. Sin
   lugar o sin minutos: avisa y corta (queda `rechazada`). Número bloqueado: corta sin atender.

**Número marcado:** con varios DIDs en la cuenta, Anura manda el número marcado en la Request-URI y en
`P-Asserted-Identity`, en formato nacional con 0 (`sip:03517003976@…`). `from-anura` lo pasa como `+54`
+ 10 dígitos. Un número que no está en el inbound trunk da 404.

**Saliente:**
1. UI, API (`POST /api/v1/calls`), campaña, derivación o llamada directa → `create_sip_participant` con el
   trunk `LIVEKIT_SIP_TRUNK_ID`, o, vacío (lo vigente), el que se llama `anura-asterisk-outbound`, y el
   número en E.164.
2. `livekit-sip` manda el INVITE a `127.0.0.1:5080`; Asterisk responde 401 y LiveKit reintenta con
   usuario `livekit` y la clave (el endpoint tiene que llamarse igual que el usuario).
3. `from-livekit` pasa el número a formato Anura y marca con el número del cliente como caller ID: el
   agente lo manda como `sip_number` y Asterisk lo pone en `P-Asserted-Identity` como `0` + 10 dígitos
   (Anura lo toma de ahí). Tiene que ser un número de la cuenta de Anura; sin uno válido sale con `ANURA_DID`.

**Números nuevos:** se cargan en la UI (Números > Cargar números), se asignan a un cliente y se rutean.
La API los agrega al inbound trunk en caliente (`app/services/livekit.py`), sin reiniciar nada. Si falla
(queda en el log de `app`), `make livekit-sip`.

## 2. Formatos de número

Anura marca en formato nacional de 10 dígitos (característica + abonado), sin 0, sin 15 y sin 54; los
celulares también sin 15 ([KB de Anura](https://kb.anura.com.ar/es/articles/4723117-llamadas-salientes-desde-twilio-usando-anura)).
`asterisk/conf/extensions.conf`, contexto `from-livekit`:

| Lo que manda el agente | Qué es | A Anura |
|---|---|---|
| `+5491155551234` | celular en E.164 | `1155551234` |
| `+541152630000` | fijo en E.164 | `1152630000` |
| `5491155551234` / `541152630000` | E.164 sin `+` | 10 dígitos |
| `01152630000` / `1152630000` | nacional | 10 dígitos |
| cualquier otro (internacional, cortos) | — | rechazada (SIP 403, "Saliente RECHAZADA") |

**Audio:** las dos patas negocian solo G.711 A-law (PCMA), el único códec de Anura; Asterisk reenvía el
RTP sin transcodificar.

## 3. LiveKit propio

`docker-compose.livekit.yml` (en `COMPOSE_FILE`, así todos los targets lo incluyen):

| Servicio | Imagen | Puertos (host) |
|---|---|---|
| `livekit` | `livekit/livekit-server:v1.13.7` | 7880/tcp señalización, 7881/tcp y 7882/udp WebRTC |
| `livekit-sip` | `livekit/sip:v1.17.0` | 5060/udp+tcp SIP, RTP 20000–20199/udp |
| `livekit-redis` | `redis:7-alpine` | 127.0.0.1:6380, canal entre `livekit` y `livekit-sip` |

Variables de `.env`:
- `LIVEKIT_URL=ws://<IP de la LAN>:7880` y `LIVEKIT_LOCAL_NODE_IP=<IP de la LAN>`; `LIVEKIT_NODE_IP` = IP
  pública (la anuncia para WebRTC).
- `LIVEKIT_API_KEY` y `LIVEKIT_API_SECRET` (`API` + `openssl rand -hex 6`, `openssl rand -hex 32`): con ellas
  arranca el server.
- `LIVEKIT_SIP_HOST=127.0.0.1:5060`, `LIVEKIT_SIP_PASSWORD` (48 hex, la misma en Asterisk y en los trunks).
- `LIVEKIT_SIP_TRUNK_ID=` **vacío**: el ID del trunk saliente cambia cada vez que se recrea y el agente lo
  busca por nombre (`livekit_sip_outbound_trunk_name` en `app/config.py`, default `anura-asterisk-outbound`).

**`make livekit-sip`** (`scripts/livekit_sip_setup.py`, idempotente) crea o actualiza tres objetos, y solo
toca los que tienen estos nombres:

| Objeto | Nombre | Qué hace |
|---|---|---|
| Inbound trunk | `anura-asterisk-inbound` | Acepta `+54<ANURA_DID>` y los números de `phone_numbers`, con usuario `livekit` y la clave. Mapea el header `X-WA-Meta-Wacid` al atributo `wa.wacid` (ruteo por contacto de WhatsApp) |
| Dispatch rule | `anura-asterisk-dispatch` | Una room `anura-*` por llamada y despacho del agente |
| Outbound trunk | `anura-asterisk-outbound` | Salientes a `127.0.0.1:5080/udp` |

Lee `phone_numbers`: con la base vacía crea el inbound trunk sin los números.

**Redis sin persistencia:** `livekit-redis` corre con `--save "" --appendonly no`, así que cada reinicio
del host (o de Redis) borra los tres objetos y las entrantes dan 486 `flood` en `livekit-sip` hasta
recrearlos. `make up` termina con `make livekit-sip` y `deploy/boot.sh` lo corre en el arranque; si se
levantó de otra forma, correrlo a mano.

**Otros datos:**
- Turn detector local: `turn-detector-v1-mini` de `livekit-local-inference`, fijado en `app/voice/worker.py`;
  ~27 ms por CPU, sin gateway externo.
- Navegadores (demo, link para llamar, teléfono del panel, `join_url` de la API): necesitan `wss://` y entran
  por `DEMO_LIVEKIT_URL` (`wss://rtc.atentina.com.ar`, túnel); el audio va por UDP 7882 / TCP 7881.
- Loadtest desde otra PC: copiar `LIVEKIT_URL`, `LIVEKIT_API_KEY` y `LIVEKIT_API_SECRET` a su `.env` y
  correr con `--base-url http://<IP>:8011`. **No levantar su `agent`:** se registraría en este LiveKit y
  atendería llamadas reales.
- Por qué no Cloud: en su plan gratuito el despacho dejaba jobs en `JS_PENDING` con ~20–24 llamadas
  simultáneas ([EXP-011](archive/experiments/EXP-011-agente-en-server-despacho-livekit/)).

## 4. Anura

### Datos de la cuenta

En la KB de Anura aparecen como string de registro
(`USUARIO@DOMINIO.grancentral.com.ar:CLAVE@iptrunk.grancentral.com.ar:55090/NUMERO`):

| Dato | Variable | Ejemplo |
|---|---|---|
| Dominio de la cuenta | `ANURA_DOMAIN` | `miempresa.grancentral.com.ar` |
| Usuario de la terminal | `ANURA_USER` | `100` |
| Contraseña de la terminal | `ANURA_PASSWORD` | |
| Número por defecto (10 dígitos) | `ANURA_DID` | `1152630861` |

**Asterisk se registra como una terminal de la cuenta dueña del número, no como una "Troncal".** En el
panel (`panel.anura.com.ar`) las entrantes siguen el plan de llamada de la cuenta que tiene el número
(*Configuración → Cuentas → la cuenta → Núm Externos*), y ese plan hace sonar sus terminales. Las
credenciales están en *Terminales → lápiz → Obtener credenciales*. Las cuentas de *Configuración →
Troncales* son la conexión con *otro* proveedor: no aceptan números de Anura y registrarse con una no
hace llegar las entrantes (probado).

### Canales

La cuenta tiene **10 canales** (`anura_channels` en `app/config.py`; el rango RTP de `rtp.conf` sobra).
Una llamada por Anura ocupa 1; una derivada a una persona, o una entrante que atiende alguien del equipo
en su celular, ocupa 2. Sin canal libre, la derivación no se intenta. La alerta de 9 de 10 canales está
en [`OBSERVABILIDAD.md`](OBSERVABILIDAD.md).

### DTMF

`dtmf_mode=rfc4733` en los endpoints. **Marcar `*` en una llamada hace que Anura corte la otra llamada
activa de la cuenta** (`*9`: ~0,3 s, 4 de 4), y a veces el `*` no llega. Los códigos de teclado que se le
piden a una persona van con `#` (`#9` probado).

## 5. Puesta en marcha

1. **`.env`**, bloque "Telefonía": `ANURA_DOMAIN`, `ANURA_USER`, `ANURA_PASSWORD`, `ANURA_DID`,
   `LIVEKIT_SIP_HOST=127.0.0.1:5060`, `LIVEKIT_SIP_PASSWORD` (pegar el valor de `openssl rand -hex 24`) y
   `ASTERISK_PUBLIC_ADDRESS=` (vacío: se autodetecta con api.ipify.org al arrancar). Más las `LIVEKIT_*`
   de la sección 3.
2. **Router:** reenvíos de [`MIGRACION_SERVER.md`](MIGRACION_SERVER.md), 6 (RTP 10000–10199/udp; el 5080
   y el 5081 no) y **SIP ALG apagado** ("SIP Helper", "SIP Passthrough"): reescribe los paquetes y es la
   causa más común de llamadas sin audio o que se cortan a los 30 s.
3. **Asterisk y registro:** `make up-pbx` y `make pbx-status` → `anura/sip:...  Registered`.
4. **LiveKit:** `make up` (o `make livekit-sip` si ya estaba arriba).
5. **Entrante:** llamar a un número de la cuenta desde un celular; seguir con `make logs S=asterisk`
   ("Entrante de Anura: … -> +54…") y `make logs S=agent`.
6. **Saliente:** desde la UI, o `POST /api/v1/calls` con `{"agent_id": "<id>", "phone": "+5491155551234"}`
   y una API key; en el log de Asterisk, `Saliente a Anura: 1155551234`.

Si cambia la IP pública: con `ASTERISK_PUBLIC_ADDRESS` vacío, `make up-pbx` la vuelve a detectar
(`LIVEKIT_NODE_IP` y `PUBLIC_HOST` se cambian a mano; ver [`MIGRACION_SERVER.md`](MIGRACION_SERVER.md), 7).

Cambios en `asterisk/conf/`: `make restart S=asterisk` (`entrypoint.sh` vuelve a renderizar, sin rebuild);
si cambió `.env`, `make up-pbx` (`docker compose restart` no relee `.env`). Las dos cortan llamadas en
curso: antes, `make calls-active`. Prueba aislada de la señalización, la transferencia y las llamadas
directas, sin puertos del host ni llamadas reales: `make e2e-sip`.

## 6. Si algo falla

SIP crudo: `make pbx-cli` y `pjsip set logger on` (`off` para cortar). Durante una llamada,
`pjsip show channelstats` muestra los paquetes recibidos por pata.

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Registro `Rejected` | Usuario, clave o dominio incorrectos | Revisar `ANURA_*` y `make up-pbx` |
| Registro `Unregistered` o "No response received" | No llega a `ANURA_DOMAIN:55090` | `getent hosts $ANURA_DOMAIN`; la red tiene que dejar salir UDP 55090 |
| Registrado, suena y no aparece "Entrante de Anura" | Anura no manda la llamada a la terminal | El plan de llamada de la cuenta dueña del número tiene que llamar a esa terminal (sección 4); una *Troncal* no sirve |
| Registrado, pero las entrantes no llegan | Anura no entra por el NAT | Entra por el 5081 gracias al registro: SIP ALG apagado, registro renovándose, IP pública correcta |
| Llega a Asterisk y LiveKit responde 404 | El número no está en el inbound trunk | Cargarlo en Números; si no entró, `make livekit-sip`. `ANURA_DID` igual en Asterisk y LiveKit |
| Llega, suena y corta; `make logs S=livekit-sip` dice `486, reason: flood` | LiveKit sin inbound trunk (se reinició y Redis no persiste); `lk sip inbound list` vacío | `make livekit-sip` |
| LiveKit sigue respondiendo 401/407 | Clave distinta entre Asterisk y LiveKit | `make livekit-sip` y `make up-pbx` con el mismo `LIVEKIT_SIP_PASSWORD` |
| Saliente fallida por timeout (408) | LiveKit no llega a Asterisk en `127.0.0.1:5080` | `make pbx-status`; Asterisk caído o transporte `transport-livekit` sin levantar |
| Saliente: SIP 403 y "Saliente RECHAZADA" | Número no argentino o formato desconocido | Cargarlo en E.164 (`+549...` o `+54...`) |
| Saliente: Anura responde 403/404 | Número o caller ID que Anura no acepta | Consultar a Anura. Si piden el `From` con el usuario de la cuenta: `from_user=${ANURA_USER}` en el endpoint `anura` |
| Conecta sin audio o en un solo sentido | El RTP de Anura no pasa por el NAT | Reenvío de 10000–10199/udp, SIP ALG apagado, IP pública correcta en el log de arranque de Asterisk |
| Se corta a los ~30 s | El ACK no llega (SIP ALG o NAT) | SIP ALG apagado |

Es normal ver `No matching endpoint found` con un 401 antes de cada saliente (el primer INVITE de
LiveKit, sin credenciales), antes de cada llamada de WhatsApp (el primero de Meta) y con los escaneos de
internet, que no pasan del 401.

## 7. Seguridad

- Tres endpoints SIP. **Anura**: por IP (sus cuatro redes de AS52275, sacadas de su KB). **LiveKit**: por
  usuario y clave (48 hex) y ACL que solo acepta loopback y la LAN (`deny=0.0.0.0/0`,
  `permit=127.0.0.0/8` y `192.168.1.0/24` en `pjsip.conf`). **Meta** (llamadas de WhatsApp): usuario y la
  clave de Meta, solo por TLS en el 5061; su contexto solo llega a LiveKit, nunca a Anura. Cualquier otro
  request recibe 401 y no llega al dialplan.
- El 5080 no se reenvía en el router: abierto, alguien podría probar claves del endpoint `livekit` y
  hacer salientes por Anura a nuestro cargo.
- Las salientes solo aceptan números argentinos: aunque se filtre la clave de LiveKit, no hay llamadas
  internacionales por la troncal.
- AMI, ARI y HTTP de Asterisk apagados; solo se cargan los módulos del puente (`modules.conf`).
- El contenedor recibe solo las variables que usa, no todo `.env`.

## 8. Archivos

| Archivo | Qué tiene |
|---|---|
| `asterisk/Dockerfile` | Alpine 3.24 + Asterisk 22 (LTS) y asterisk-srtp; el `apk add` no fija versión (probado con 22.9.0-r0) |
| `asterisk/entrypoint.sh` | Valida `.env`, detecta la IP pública y renderiza `asterisk/conf/*.conf` en `/etc/asterisk` |
| `asterisk/conf/pjsip.conf` | Transportes, registro y endpoint de Anura, endpoint de LiveKit |
| `asterisk/conf/whatsapp/pjsip_whatsapp.conf` | Transporte TLS y endpoint de Meta; se incluye solo con `WA_SIP_PASSWORD` y certificado |
| `asterisk/letsencrypt/` | Certificado de `sip.atentina.com.ar` (`make sip-cert`, renovado por cron; no versionado) |
| `asterisk/conf/extensions.conf` | Ruteo entrante y saliente, formatos de número, `whatsapp-predial` |
| `asterisk/conf/rtp.conf` | Rango RTP 10000–10199 (tiene que coincidir con el reenvío del router) |
| `asterisk/conf/modules.conf` | Lista mínima de módulos |
| `scripts/livekit_sip_setup.py` | Trunks y dispatch rule (`make livekit-sip`) |
| `app/services/livekit.py` | Alta y baja de números en el inbound trunk en caliente |

## Apéndice: LiveKit Cloud (respaldo, no se usa)

Para volver a Cloud: pasar `LIVEKIT_CLOUD_URL`, `_API_KEY`, `_API_SECRET`, `_SIP_TRUNK_ID` y `_SIP_HOST`
de `.env` a las `LIVEKIT_*`, sacar `docker-compose.livekit.yml` de `COMPOSE_FILE` y `make up`.
`LIVEKIT_SIP_HOST` es el SIP URI del proyecto (Settings → Project → SIP URI, `xxxxxxxx.sip.livekit.cloud`,
sin `sip:`).

Lo que cambia con Cloud:
- **Hay que reenviar el UDP 5080** en el router (el saliente de LiveKit apunta a `<IP pública>:5080`,
  desde São Paulo) y sacar el ACL del endpoint `livekit` en `pjsip.conf`, porque Cloud no sale con IPs fijas.
- **NAT, un transporte por lado:** el router cambia el puerto de origen de lo que sale. Si Asterisk le
  manda audio a LiveKit antes del primer paquete de LiveKit, el router descarta el audio de vuelta y el
  cliente no escucha al agente (0 paquetes recibidos contra ~300). Cloud contesta a la dirección de
  origen (RTP simétrico) solo si el SDP trae una IP privada; por eso `transport-livekit` anuncia la IP de
  la LAN (sin `external_media_address`) y `transport-anura` la pública.
- Con IP dinámica, un hostname de DDNS en `ASTERISK_PUBLIC_ADDRESS`; si la IP cambia, `make up-pbx` y
  `make livekit-sip`.
- El despacho del plan gratuito se traba con ~20–24 llamadas (EXP-011).
