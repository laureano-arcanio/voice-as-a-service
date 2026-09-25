# Telefonía: troncal Anura vía Asterisk

Cómo conectar la troncal SIP de [Anura](https://kb.anura.com.ar/es/) con LiveKit
Cloud para que el agente reciba y haga llamadas a la red telefónica, usando un
Asterisk en Docker como puente.

## 1. Arquitectura

```
                  ENTRANTE: cliente llama al número de la troncal
  Teléfono ── PSTN ── Anura ─────────────► Asterisk ─────────────► LiveKit Cloud ──► room anura-*
  del cliente         (grancentral)  SIP   (contenedor, SIP     SIP   (inbound trunk +     + agente
                      :55090/udp           :5080/udp)                 dispatch rule)
                                     ◄─────────────     ◄─────────────
                  SALIENTE: el agente marca (create_sip_participant)
```

**Por qué hace falta Asterisk.** La troncal de Anura funciona por *registro*:
un equipo propio se registra con usuario y contraseña, y Anura le manda las
llamadas entrantes a la dirección registrada. LiveKit no se registra contra
proveedores: solo recibe INVITEs en su SIP URI. Asterisk hace el registro,
traduce los formatos de número (Anura usa formato nacional, LiveKit E.164) y
controla quién puede usar la troncal.

**Entrante:**

1. Asterisk se registra en `ANURA_DOMAIN:55090` con `ANURA_USER`/`ANURA_PASSWORD`.
2. Alguien llama al número de la troncal. Anura manda el INVITE a Asterisk, que
   lo reconoce porque viene de las redes de Anura.
3. Asterisk lo reenvía a `LIVEKIT_SIP_HOST` con destino `+54<ANURA_DID>` y se
   autentica con usuario `livekit` y `LIVEKIT_SIP_PASSWORD`.
4. El inbound trunk de LiveKit acepta la llamada. La dispatch rule crea una room
   `anura-...` y despacha el agente (`LIVEKIT_AGENT_NAME`).
5. El agente la trata como entrante porque no trae `local_call_id`, y crea el
   registro de la llamada en la base (`app/livekit_agent.py`).

**Saliente:**

1. Dashboard → **Llamar** → el agente llama a `create_sip_participant` con el
   trunk `LIVEKIT_SIP_TRUNK_ID` y el número en E.164.
2. LiveKit manda el INVITE desde São Paulo a `<IP pública>:5080`.
3. Asterisk responde 401, y LiveKit reintenta con usuario `livekit` y la clave.
4. Asterisk pasa el número a formato Anura y marca con el caller ID `ANURA_DID`.

**Formatos de número.** Anura marca en formato nacional de 10 dígitos
(característica + abonado), sin 0, sin 15 y sin 54. Los celulares también van
sin 15 ([KB de Anura](https://kb.anura.com.ar/es/articles/4723117-llamadas-salientes-desde-twilio-usando-anura)).
Asterisk (`asterisk/conf/extensions.conf`, contexto `from-livekit`) convierte así:

| Lo que manda el agente | Qué es | A Anura |
|---|---|---|
| `+5491155551234` | celular en E.164 | `1155551234` |
| `+541152630000` | fijo en E.164 | `1152630000` |
| `5491155551234` / `541152630000` | E.164 sin `+` | 10 dígitos |
| `01152630000` / `1152630000` | nacional | 10 dígitos |
| cualquier otro (internacional, cortos) | — | rechazada (SIP 403) |

En las entrantes, el caller ID se pasa a E.164 (`+54...`) antes de llegar a
LiveKit. Es lo que el agente guarda como teléfono de la llamada.

**Audio.** Las dos patas negocian solo G.711 A-law (PCMA). Es el único códec que
acepta Anura, y LiveKit lo soporta, así que Asterisk reenvía el RTP sin
transcodificar.

**NAT: un transporte SIP por lado.** El router (el Huawei de Telecom) cambia el
puerto de origen de todo lo que sale. Si Asterisk le manda audio a LiveKit
antes de que llegue el primer paquete de LiveKit, el router descarta el audio
de LiveKit y el cliente no escucha al agente, aunque el agente sí lo escuche a
él. Pasa en la mayoría de las llamadas. LiveKit Cloud le contesta a la dirección
desde la que recibe (RTP simétrico) solo si el SDP trae una IP privada. Por eso
`pjsip.conf` tiene dos transportes:

| Transporte | Puerto | Audio anunciado | ¿Se redirige en el router? |
|---|---|---|---|
| `transport-livekit` | `ASTERISK_SIP_PORT` (5080) | IP de la LAN, para que LiveKit aprenda la dirección real | Sí, junto con el rango RTP |
| `transport-anura` | `ASTERISK_ANURA_SIP_PORT` (5081) | IP pública | No: Anura entra por el agujero que abre el registro |

## 2. Qué hace falta antes de empezar

### Datos de Anura

Pedile a Anura los datos de la **troncal SIP para PBX propia**. En su KB aparecen
como un string de registro
(`USUARIO@DOMINIO.grancentral.com.ar:CLAVE@iptrunk.grancentral.com.ar:55090/NUMERO`):

| Dato | Variable | Ejemplo |
|---|---|---|
| Dominio de la cuenta | `ANURA_DOMAIN` | `miempresa.grancentral.com.ar` |
| Usuario de la terminal | `ANURA_USER` | `100` |
| Contraseña de la terminal | `ANURA_PASSWORD` | |
| Número (10 dígitos) | `ANURA_DID` | `1152630861` |

**Asterisk se registra como una terminal de la cuenta dueña del número, no como
una "Troncal".** En el panel de Anura (`panel.anura.com.ar`) las entrantes a un
número siguen el plan de llamada de la cuenta que lo tiene asignado
(*Configuración → Cuentas → la cuenta → Núm Externos*), y ese plan hace sonar sus
terminales (pestaña *Terminales*). Los datos de registro están en *Terminales →
lápiz → Obtener credenciales*: usuario (ej. `100`) y contraseña. Las cuentas de
*Configuración → Troncales* son otra cosa: la conexión con *otro* proveedor. No
aceptan números de Anura, y registrarse con una de ellas no hace llegar las
entrantes (probado).

Si Anura pide la IP pública para habilitar la troncal, pasales la de
`curl ifconfig.me` (o el hostname de DDNS, ver abajo).

### Red: port forwarding en el router

Asterisk corre en este host (`network_mode: host`) detrás del NAT del router.
LiveKit y Anura tienen que poder mandarle tráfico, así que en el router:

1. **Reservar una IP fija de LAN** para este host (reserva DHCP), por ejemplo
   `192.168.1.99`.
2. **Redirigir a esa IP, en UDP:**
   - `5080` (SIP, `ASTERISK_SIP_PORT`)
   - `10000-10199` (RTP, `ASTERISK_RTP_START`-`ASTERISK_RTP_END`)
3. **Desactivar el SIP ALG** del router (a veces aparece como "SIP Helper" o
   "SIP Passthrough"). Reescribe los paquetes SIP y es la causa más común de
   llamadas sin audio o que se cortan a los 30 segundos.
4. Si el host tiene firewall propio (ufw, firewalld), abrir los mismos puertos.

Si el ISP da IP dinámica, conviene un hostname de DDNS en
`ASTERISK_PUBLIC_ADDRESS`. Si queda vacío, Asterisk detecta la IP al arrancar,
pero si la IP cambia hay que reiniciar Asterisk y volver a correr
`make livekit-sip` (el trunk saliente de LiveKit apunta a esa IP).

### SIP URI de LiveKit

Está en el dashboard de LiveKit Cloud, en **Settings → Project → SIP URI**.
Tiene la forma `sip:xxxxxxxx.sip.livekit.cloud`. Va en `LIVEKIT_SIP_HOST` sin el
`sip:`. No es el mismo subdominio que `LIVEKIT_URL`.

## 3. Paso a paso

**1. Completar `.env`** (bloque "Telefonía" de `.env.example`):

```bash
ANURA_DOMAIN=miempresa.grancentral.com.ar
ANURA_USER=99905
ANURA_PASSWORD=...
ANURA_DID=1152630861
LIVEKIT_SIP_HOST=xxxxxxxx.sip.livekit.cloud
LIVEKIT_SIP_PASSWORD=$(openssl rand -hex 24)   # pegar el valor, no el comando
ASTERISK_PUBLIC_ADDRESS=                        # vacío = autodetectar
```

**2. Levantar Asterisk y confirmar el registro con Anura:**

```bash
make pbx
make pbx-status
```

En `pjsip show registrations` tiene que figurar `anura/sip:...  Registered`.
Si dice `Rejected` o `Unregistered`, ver la sección 4.

**3. Crear los objetos SIP en LiveKit:**

```bash
make livekit-sip
```

Crea (o actualiza, si ya existen) tres objetos en el proyecto de LiveKit de
`.env`:

| Objeto | Nombre | Qué hace |
|---|---|---|
| Inbound trunk | `anura-asterisk-inbound` | Acepta llamadas a `+54<ANURA_DID>` que llegan con usuario `livekit` y la clave |
| Dispatch rule | `anura-asterisk-dispatch` | Crea una room `anura-*` por llamada y despacha el agente |
| Outbound trunk | `anura-asterisk-outbound` | Manda las salientes a `<IP pública>:5080/udp`, originadas desde Brasil |

Al final imprime el ID del outbound trunk. Ponelo en `.env` como
`LIVEKIT_SIP_TRUNK_ID=ST_...` y corré `make up`, que recrea el agente con el `.env` nuevo (`make restart-agent` no alcanza: `docker compose restart` no vuelve a leer `.env`).

No toca otros trunks o reglas del proyecto (por ejemplo, las de pruebas
anteriores): busca solo por estos nombres.

**4. Probar una entrante.** Con el agente corriendo (`make up` o
`make up-remote`), llamá al número de la troncal desde un celular. Tiene que
atender el agente. Para seguir la llamada:

```bash
make logs-pbx     # "Entrante de Anura: ... -> +54..."
make logs-agent
```

**5. Probar una saliente.** `curl -X POST localhost:8011/calls -H 'Content-Type: application/json'
-d '{"phone": "+5491155551234"}'`. En `make logs-pbx` tiene que
aparecer `Saliente a Anura: 1155551234`.

## 4. Si algo falla

Para ver los mensajes SIP completos: `make pbx-cli` y después
`pjsip set logger on` (`pjsip set logger off` para cortar).

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Registro `Rejected` | Usuario, clave o dominio incorrectos | Revisar `ANURA_*` contra lo que dio Anura y correr `make restart-pbx` |
| Registro `Unregistered` o "No response received" | No llega a `ANURA_DOMAIN:55090` | `getent hosts $ANURA_DOMAIN`. Revisar que la red deje salir UDP 55090 |
| Registrado, pero al llamar suena y en `make logs-pbx` no aparece "Entrante de Anura" | Anura no le manda la llamada a la terminal registrada | En el panel, el plan de llamada de la cuenta dueña del número tiene que llamar a la terminal con la que se registra Asterisk (ver "Datos de Anura"). Registrarse con una cuenta de *Troncales* no sirve |
| Registrado, pero las entrantes no llegan a Asterisk | Anura no puede entrar por el NAT | Port forwarding de 5080/udp, SIP ALG apagado, IP pública correcta |
| Llega a Asterisk y LiveKit responde 404 | El número no coincide con el inbound trunk | `ANURA_DID` tiene que ser el mismo en Asterisk y en LiveKit. Correr de nuevo `make livekit-sip` |
| Llega a Asterisk y LiveKit sigue respondiendo 401/407 | Clave distinta entre Asterisk y LiveKit | Correr de nuevo `make livekit-sip` y `make restart-pbx` con el mismo `LIVEKIT_SIP_PASSWORD` |
| Saliente: el agente marca la llamada como fallida por timeout (408) | LiveKit no llega a `<IP pública>:5080` | Port forwarding, o cambió la IP pública: `make restart-pbx` y `make livekit-sip` |
| Saliente: SIP 403 y en los logs "Saliente RECHAZADA" | El número no es argentino o tiene un formato desconocido | Cargarlo en E.164 (`+549...` o `+54...`) |
| Saliente: Anura responde 403/404 | Formato de número o caller ID que Anura no acepta | Consultar a Anura. Si piden que el `From` sea el usuario de la cuenta, agregar `from_user=${ANURA_USER}` al endpoint `anura` en `pjsip.conf` |
| La llamada conecta pero no hay audio, o se escucha en un solo sentido | El RTP no pasa por el NAT | Port forwarding de 10000-10199/udp, SIP ALG apagado, `ASTERISK_PUBLIC_ADDRESS` correcta. Si el agente escucha al cliente pero no al revés, revisar que el endpoint `livekit` siga en `transport-livekit` (sin `external_media_address`, ver "NAT" arriba). Diagnóstico: `pjsip show channelstats` durante la llamada (paquetes recibidos por canal) |
| Se corta a los ~30 segundos | El ACK no llega (SIP ALG o NAT) | SIP ALG apagado |

Es normal ver en los logs `No matching endpoint found` con un 401 antes de cada
saliente: es el primer INVITE de LiveKit, que todavía no trae credenciales.
Pasa lo mismo con los escaneos de internet, que no van más allá del 401.

## 5. Seguridad

- Solo hay dos endpoints SIP. A **Anura** se lo reconoce por IP (sus cuatro redes
  de AS52275, sacadas de su KB). A **LiveKit** se lo reconoce por usuario y clave
  (48 caracteres hex), porque desde Sudamérica LiveKit Cloud no sale con IPs
  fijas. Cualquier otro request recibe 401 y no llega al dialplan.
- Las salientes solo aceptan números argentinos. Aunque se filtre la clave de
  LiveKit, no se pueden hacer llamadas internacionales por la troncal.
- AMI, ARI y HTTP de Asterisk están apagados, y solo se cargan los módulos que
  usa el puente (`asterisk/conf/modules.conf`).
- El puerto SIP es 5080 y no 5060, para esquivar la mayoría de los escaneos
  automáticos.
- El contenedor recibe solo las variables que usa, no todo `.env`.

## 6. Archivos

| Archivo | Qué tiene |
|---|---|
| `asterisk/Dockerfile` | Alpine 3.24 + Asterisk 22 (LTS) |
| `asterisk/entrypoint.sh` | Valida `.env`, detecta la IP pública y renderiza `asterisk/conf/*.conf` en `/etc/asterisk` |
| `asterisk/conf/pjsip.conf` | Transporte con NAT, registro y endpoint de Anura, endpoint de LiveKit |
| `asterisk/conf/extensions.conf` | Ruteo entrante/saliente y formatos de número |
| `asterisk/conf/rtp.conf` | Rango RTP (tiene que coincidir con el port forwarding) |
| `asterisk/conf/modules.conf` | Lista mínima de módulos |
| `scripts/livekit_sip_setup.py` | Crea o actualiza trunks y dispatch rule en LiveKit (`make livekit-sip`) |

Los cambios en `asterisk/conf/` se aplican con `make restart-pbx`, sin rebuild.

## 7. LiveKit propio (desarrollo)

En lugar de LiveKit Cloud, `docker-compose.livekit.yml` levanta LiveKit en este
host. Motivo: en el plan gratuito de Cloud, el despacho del agente deja jobs en
`JS_PENDING` con ~20–24 llamadas simultáneas ([EXP-011](archive/experiments/EXP-011-agente-en-server-despacho-livekit/)).

```
  Teléfono ── Anura ──► Asterisk ──► livekit-sip ──► livekit ──► room anura-* + agente
                        :5080/udp    127.0.0.1:5060   :7880
```

| Servicio | Imagen | Puertos (host) |
|---|---|---|
| `livekit` | `livekit/livekit-server:v1.13.7` | 7880/tcp señalización, 7881/tcp y 7882/udp WebRTC |
| `livekit-sip` | `livekit/sip:v1.17.0` | 5060/udp+tcp SIP, RTP 20000–20199/udp |
| `livekit-redis` | `redis:7-alpine` | 127.0.0.1:6380, canal entre `livekit` y `livekit-sip` |

**Activar** (el `.env` dice lo que se usa; el override no pisa variables):
1. Guardar las de Cloud como `LIVEKIT_CLOUD_URL`, `_API_KEY`, `_API_SECRET`, `_SIP_TRUNK_ID` y `_SIP_HOST`, para volver.
2. En `.env`:
   - `COMPOSE_FILE=docker-compose.yml:docker-compose.livekit.yml`: todos los targets de `make` incluyen el override;
   - `LIVEKIT_URL=ws://<IP de la LAN>:7880` y `LIVEKIT_LOCAL_NODE_IP=<IP de la LAN>`;
   - `LIVEKIT_API_KEY` y `LIVEKIT_API_SECRET` nuevas (`API` + `openssl rand -hex 6`, `openssl rand -hex 32`): con ellas arranca el server;
   - `LIVEKIT_SIP_HOST=127.0.0.1:5060`.
3. `make up`, y `make livekit-sip`: crea los trunks y la dispatch rule en el LiveKit local. El trunk saliente apunta a `127.0.0.1:5080`. Poner el ID que imprime en `LIVEKIT_SIP_TRUNK_ID` y `make up`.

**Volver a Cloud:** pasar los `LIVEKIT_CLOUD_*` a `LIVEKIT_URL`, `_API_KEY`, `_API_SECRET`, `_SIP_TRUNK_ID` y `_SIP_HOST`, comentar `COMPOSE_FILE` y `make up`.

**Qué cambia:**
- **El tramo Asterisk ↔ LiveKit queda dentro del host.** No pasa por el router, así que no tiene el problema de NAT de la sección 1. Solo el tramo de Anura cruza el router.
- **Turn detector local:** `turn-detector-v1-mini` de `livekit-local-inference`, fijado en `app/livekit_agent.py`. Los pesos vienen en el wheel y predice en ~27 ms por CPU. No usa el gateway de Cloud.
- **Sin dashboard de Cloud** (sesiones, observabilidad).
- **El link de prueba en el navegador no anda:** `meet.livekit.io` necesita `wss://`. Hace falta TLS con un dominio delante de 7880.
- **Loadtest desde otra PC:** copiar `LIVEKIT_URL`, `LIVEKIT_API_KEY` y `LIVEKIT_API_SECRET` de este `.env` al suyo (firma los tokens de los callers) y correr con `--base-url http://<NODE_IP>:8011`. No levantar su `agent`: se registraría en este LiveKit y recibiría llamadas. Todo va por la LAN, sin port forwarding.

**Probado (2026-09-25):**
- Llamada de loadtest de 2 turnos: e2e 1,1 s.
- Entrante simulada desde Asterisk (`channel originate`, con `res_clioriginate` cargado a mano): autenticación, dispatch rule, agente y audio de vuelta a Asterisk.
- Pendiente: una entrante y una saliente reales por Anura.
