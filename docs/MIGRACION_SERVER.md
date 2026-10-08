# Migración a un server nuevo

Runbook para montar este entorno en un server nuevo (mismo tipo de hardware, disco vacío) y pasarle
el tráfico. Está escrito para que lo siga un agente paso a paso; lo que solo puede hacer el usuario
(paneles externos, router) está marcado **(usuario)**. Relevado el 6-oct-2026 en el server actual.

Reglas del corte, que valen en todo el runbook:
- **Nunca dos Asterisk registrados con la misma terminal de Anura** (las entrantes se reparten o se
  pierden) **ni dos `cloudflared` con el mismo token** (Cloudflare reparte dashboard, demo y webhook
  de WhatsApp entre los dos hosts, con bases distintas).
- **Nunca dos `agent` contra el mismo LiveKit.** El `.env` copiado del viejo trae
  `LIVEKIT_URL=ws://192.168.1.99:7880`: si el nuevo está en otra IP de la LAN y se levanta con ese
  `.env`, su agente atiende llamadas del LiveKit del viejo. Ajustar el `.env` (paso 3.2) antes del
  primer arranque.

| Fase | Qué | Servicio cortado |
|---|---|---|
| 1 | Inventario de lo que hay que llevar | no |
| 2 | Preparar el host | no |
| 3 | Clonar y configurar `.env` | no |
| 4 | Restaurar datos (checkpoint del TTS, base de prueba, certificado) | no |
| 5 | Levantar por partes y verificar, **sin Asterisk ni túnel** | no |
| 6–7 | Red, router y servicios externos | durante el corte |
| 8 | systemd, cron y topes de GPU | no |
| 9–10 | Corte, pruebas de punta a punta y vuelta atrás | 15–30 min |
| 11 | Checklist final | — |

## 1. Inventario: qué hay que llevar

Clonar el repo no alcanza. Lo que está fuera de git:

| Dato | Dónde (server viejo) | Tamaño | En `backup.sh` | Cómo se recupera en el nuevo |
|---|---|---|---|---|
| `.env` (todos los secretos; `WA_TOKEN_KEY`) | `~/voice-as-a-service/.env` | — | sí: `~/atentina-backups/env/env-AAAAMMDD-HHMM` | copiar (paso 3.2) |
| Base PostgreSQL (clientes, tiers, agentes y sus versiones, números y su ruteo, cuentas de WhatsApp, usuarios, conversaciones) | volumen `voice-as-a-service_postgres_data` | MB | sí: `~/atentina-backups/db/db-AAAAMMDD-HHMM.sql.gz` | paso 4.2 |
| Checkpoint del TTS servido (41 voces; **perderlo es reentrenar**) | `tts/finetune/work/runs/multi41/lr2e-6/checkpoint-epoch-2` (`TTS_FT_CKPT`) | 4,3 GB | sí, pero como `~/atentina-backups/tts/lr2e-6-checkpoint-epoch-2` (**pierde el nivel `multi41`**) | paso 4.1 |
| Datos y runs de fine-tuning | `tts/finetune/work/` | 41 GB | no | solo para reentrenar: `rsync` del viejo, o regenerar ([`TTS_FINETUNE.md`](TTS_FINETUNE.md)) |
| Certificado de `sip.atentina.com.ar` (llamadas de WhatsApp) | `asterisk/letsencrypt/` (de root) | KB | no | se regenera: `make sip-cert` (paso 4.3) |
| Trunks SIP y dispatch rule de LiveKit | Redis de LiveKit, sin persistencia | — | no | se regeneran: `make livekit-sip` (lo corre `make up`) |
| Pesos del LLM vigente (Gemma 4 26B, desde el 6-oct-2026) | `/home/laureano/Models/gemma-4-26B-A4B-it-qat-AWQ-INT4`, **fuera del repo y del volumen de HF**: el override `docker-compose.gemma4-26b.yml` lo monta con esa ruta fija | 17 GB | no | **no se bajan solos:** descargarlos con la revisión fijada o copiarlos del viejo (paso 4.4) |
| Pesos de Hugging Face | volumen `voice-as-a-service_hf_cache` (80 GB, casi todo de modelos descartados) | Parakeet ~1,2 GB; el Qwen3.5-9B (~12 GB) solo para volver a él | no | se bajan solos en el primer arranque (ningún modelo es *gated*: `HF_TOKEN` no hace falta). Opcional: copiarlos (paso 4.4) |
| Imágenes de Docker | `/var/lib/docker` | ~62 GB | no | `docker pull` y `make build` (paso 5.1) |
| `storage/` | `./storage` montado en `app` | vacío | no | no se usa: el audio no se graba (las transcripciones están en la base; grabar está planeado, sin implementar). No hace falta copiarlo |
| Crontab del usuario | `crontab -l` | — | no | paso 8.2 (líneas literales) |
| Unidades de systemd | `/etc/systemd/system/atentina-*.service` | — | — | `sudo deploy/install.sh` (paso 8.1), desde la plantilla `deploy/systemd/` |

**Antes de migrar, todo lo que usa el host tiene que estar commiteado y pusheado.** El 6-oct-2026 faltaban
`scripts/ops/sip-cert-renew.sh` y `asterisk/conf/whatsapp/` (llamadas de WhatsApp y renovación del
certificado); se versionaron ese día (`6a3f57a`). Repetir el chequeo antes del corte:

```bash
git -C ~/voice-as-a-service status --short   # en el viejo: tiene que salir vacío (o copiar los cambios)
git -C ~/voice-as-a-service log origin/main..HEAD --oneline   # vacío: todo pusheado
```

**Copia externa:** hoy (6-oct-2026) los backups están solo en `~/atentina-backups`, en el mismo
equipo (`/home`, el mismo disco que el repo). `RCLONE_REMOTE` y `BACKUP_GPG_RECIPIENT` no están en
`.env`. Si el server viejo se perdió, no hay de dónde restaurar base, `.env` ni checkpoint: quedaría
volver a sembrar (sección 4.2, "Sin backup") y reentrenar las voces. Además, cron no recupera la
corrida de las 03:30 si el host estaba apagado (no hay dumps del 4 ni del 5 de octubre).

## 2. Preparar el host

Versiones probadas (server actual, 6-oct-2026):

| Pieza | Versión |
|---|---|
| SO | Ubuntu 24.04.3 LTS, kernel 7.0.0-34-generic, escritorio GNOME (`graphical.target`) |
| Driver NVIDIA | `nvidia-driver-580-open` 580.178.04 (CUDA 13.0). Mínimo rama 580: las imágenes de vLLM traen torch 2.13.0+cu130 |
| Docker | docker-ce 29.5.2, containerd.io 2.2.4, Compose v5.1.4 (plugin); data-root `/var/lib/docker` |
| NVIDIA Container Toolkit | 1.20.0; `/etc/docker/daemon.json` solo con el runtime `nvidia` |
| vLLM (LLM y base del STT) | `vllm/vllm-openai:latest` = vLLM 0.29.0, digest `sha256:c2914767605584b6d8f45686b82de173ecc99e781897aa3d0a66dacd72c51ae1` (9-sep-2026) |
| vLLM-Omni (TTS) | `vllm/vllm-omni:v0.28.0`, digest `sha256:6f8be103eaf0055448cf7578cfd621405fd669079d4361bd58896326b2bf722a` |
| Asterisk | 22.9.0-r0 + asterisk-srtp 22.9.0-r0 sobre `alpine:3.24` (`apk` sin versión fija en el Dockerfile) |
| LiveKit | `livekit-server:v1.13.7`, `livekit/sip:v1.17.0`, `redis:7-alpine`; CLI `lk` 2.18.6 |
| cloudflared | `cloudflare/cloudflared:2026.9.0` |

Pasos (como el usuario dueño del repo, con sudo):

1. **SO:** Ubuntu 24.04 LTS. Zona horaria (las horas del cron son locales):
   `sudo timedatectl set-timezone America/Argentina/Cordoba`. Verificar: `timedatectl show -p Timezone`.
2. **Discos.** Server actual: NVMe de 465 GB en `/` (Docker en `/var/lib/docker`, 59 % usado) y NVMe
   de 1,8 TB en `/home` (ext4; repo, `tts/finetune/work`, `~/atentina-backups`). Necesidades:
   - disco de Docker: ~62 GB de imágenes de inferencia (vllm-openai 30,5 + vllm-omni 30,3 + capa del
     STT 0,3) + ~1 GB de `app` + ~13,4 GB de pesos + build cache: **dejar ≥ 150 GB libres**. Con el
     entorno de fine-tuning, +25 GB de imagen (`voice-tts-ft`) y ~9 GB de modelos;
   - `/home`: checkpoint (4,3 GB), `tts/finetune/work` si se lleva (41 GB) y backups (≥ 10 GB).
   - Mantener la base (volumen de Docker) y los backups **en discos distintos**.
3. **Driver:** `sudo apt install nvidia-driver-580-open` y reiniciar. Verificar
   `nvidia-smi --query-gpu=index,name,pci.bus_id --format=csv`: las dos RTX 3090.
4. **Docker CE** desde el repo oficial (download.docker.com, `noble stable`): `docker-ce`,
   `docker-ce-cli`, `containerd.io`, `docker-compose-plugin`. Después
   `sudo usermod -aG docker $USER` y volver a entrar: `atentina-stack.service` y el cron corren
   como el usuario y llaman a `docker` sin sudo. Verificar: `docker compose version` y `id | grep docker`.
5. **Container Toolkit:** `sudo bash scripts/install-nvidia-toolkit.sh` (se corre después de
   clonar, paso 3.1; instala, configura el runtime, reinicia Docker y prueba `nvidia-smi` en un
   contenedor).
6. **Paquetes del host:** `sudo apt install git make curl jq rsync gnupg openssl python3-yaml dnsutils`.
   - Copia externa del backup: `rclone` (`sudo apt install rclone` + `rclone config`) y la llave
     pública de `BACKUP_GPG_RECIPIENT` importada.
   - Test de capacidad: python3 + `python3-yaml` (y `python3-psutil`); `make gpubench`:
     `nvidia-cuda-toolkit` (nvcc).
   - Desarrollo de `web/` y `landing/`: Node 22+ (hoy 24.15.0 por nvm). En producción no hace falta:
     la imagen de `app` compila la UI.
   - CLI de LiveKit (pruebas, paso 9): `curl -sSL https://get.livekit.io/cli | bash`.
7. **Orden de las GPUs.** `docker-compose.yml` fija `device_ids` por índice: `0` = LLM solo
   (0.90, ~21–22,7 GB), `1` = TTS + STT (~16 GB) **+ escritorio**. El índice sigue el bus PCI. Hoy:
   índice 0 = `04:00.0` (slot del chipset, gen3 x4), índice 1 = `07:00.0` (slot de la CPU, gen4 x16,
   dibuja el escritorio). En otra placa, verificar con `nvidia-smi` en qué índice aparecen Xorg o
   gnome-shell: tiene que ser el 1. Si el escritorio queda en la 0, el LLM no entra: invertir con
   un override `docker-compose.<nombre>.yml`, o mover el monitor. `GPU_LLM_ID`/`GPU_TTS_ID` del
   `.env` solo los usa el override de la 5060 Ti: no afectan al compose principal.
8. **Red de la LAN:** IP por DHCP de NetworkManager (`enp6s0`, `192.168.1.99/24`). Mantenerla con
   una **reserva DHCP por MAC en el router (usuario)**, o IP estática en NetworkManager.
   Estado del host viejo: `ufw` instalado y apagado (`ENABLED=no`), sin servidor SSH.

## 3. Clonar y configurar

### 3.1 Clonar

```bash
git clone git@github.com:laureano-arcanio/voice-as-a-service.git ~/voice-as-a-service
```

**El directorio se tiene que llamar exactamente `voice-as-a-service`.** Compose no define `name:`,
así que el nombre del proyecto sale del directorio, y de él salen los volúmenes
(`voice-as-a-service_postgres_data`, `_hf_cache`) y los contenedores
(`voice-as-a-service-<servicio>-1`) que usan `scripts/ops/backup.sh`, `healthcheck.sh`,
`sip-cert-renew.sh`, `make db-reset` y `TTS_FINETUNE.md`. Clonado con otro nombre, el backup y el
chequeo fallan. La clave SSH del host nuevo tiene que estar en GitHub (deploy key o cuenta
**(usuario)**).

### 3.2 `.env`

Con backup: `cp ~/atentina-backups/env/env-<último> ~/voice-as-a-service/.env && chmod 600 .env`
(del viejo o de la copia externa). Revisar estas variables, que dependen del host:

| Variable | Valor actual | Cambia si… |
|---|---|---|
| `COMPOSE_FILE` | `docker-compose.yml:docker-compose.livekit.yml:docker-compose.gemma4-26b.yml` (LiveKit propio y LLM Gemma, vigentes) | no cambia. Si el usuario o la ruta de `~/Models` cambian, ajustar el volumen del override (ruta fija `/home/laureano/Models`) |
| `LIVEKIT_URL` | `ws://192.168.1.99:7880` | cambia la IP de la LAN. **Si el nuevo convive con el viejo en otra IP, poner la del nuevo antes del primer arranque** |
| `LIVEKIT_LOCAL_NODE_IP` | `192.168.1.99` | cambia la IP de la LAN |
| `LIVEKIT_NODE_IP`, `PUBLIC_HOST` | `181.104.113.28` | cambia la IP pública |
| `ASTERISK_PUBLIC_ADDRESS` | vacío (se autodetecta con api.ipify.org al arrancar) | — |
| `TTS_FT_CKPT` | `./tts/finetune/work/runs/multi41/lr2e-6/checkpoint-epoch-2` | se restaura en otra ruta |
| `UID`, `GID` | default 1000 | el usuario del host no es 1000:1000 |
| `LIVEKIT_SIP_TRUNK_ID` | vacío | no cambia (con LiveKit propio va vacío) |

Además, si la LAN no es `192.168.1.0/24`: ajustar `permit=` del endpoint `livekit` en
`asterisk/conf/pjsip.conf` (con LiveKit propio alcanza con loopback).

Al editar, diff enmascarado contra el original antes de levantar nada:
`diff <(sed -E 's/=(.{4}).*/=\1…/' env-viejo) <(sed -E 's/=(.{4}).*/=\1…/' .env)`.

Sin backup (`.env` desde cero, `make setup`): completar cada secreto según esta tabla. Ojo: el
`.env.example` trae LiveKit Cloud como default; para producción, el bloque de LiveKit propio
([`TELEFONIA_ANURA.md`](TELEFONIA_ANURA.md), 7).

| Variable | De dónde sale | En una mudanza |
|---|---|---|
| `AUTH_SECRET` | `openssl rand -hex 32` | se puede regenerar: solo cierra las sesiones |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | inventadas | solo para el primer admin; con base restaurada, ya existe |
| `POSTGRES_DB/USER/PASSWORD` | inventadas, alfanuméricas | con restore por dump pueden ser nuevas; con copia del volumen, iguales |
| `VLLM_API_KEY` | `openssl rand -hex 24` | regenerable; poner siempre una real (el proxy escucha en `0.0.0.0:8100`, la LAN la ve) |
| `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` | `API` + `openssl rand -hex 6`, `openssl rand -hex 32` | regenerables |
| `LIVEKIT_SIP_PASSWORD` | `openssl rand -hex 24` | regenerable (Asterisk y trunks la toman del `.env`) |
| `ANURA_DOMAIN/USER/PASSWORD/DID` | panel de Anura → Cuentas → la cuenta → Terminales → Obtener credenciales **(usuario)** | conservar |
| `CLOUDFLARE_TUNNEL_TOKEN` | Zero Trust → Networks → Tunnels → `atentina-demo` **(usuario)** | **conservar**: las rutas api./rtc./wa./app. viven en el túnel |
| `CLOUDFLARE_DNS_API_TOKEN` | Cloudflare → API tokens, Zone > DNS > Edit sobre atentina.com.ar **(usuario)** | conservar o crear otro |
| `TURNSTILE_SECRET_KEY` | Cloudflare → Turnstile, sitio atentina.com.ar **(usuario)** | conservar |
| `RESEND_API_KEY`, `CONTACT_TO` | panel de Resend (dominio en sa-east-1) **(usuario)** | conservar |
| `WA_APP_ID`, `WA_APP_SECRET` | developers.facebook.com → app Atentina → Configuración → Básica **(usuario)** | conservar |
| `WA_ACCESS_TOKEN` | token del system user del portafolio **(usuario)** | conservar (las 2 cuentas de WhatsApp lo usan: `access_token` NULL) |
| `WA_VERIFY_TOKEN` | inventado; el mismo que en el panel de Meta | si cambia, cambiarlo en Meta |
| `WA_TOKEN_KEY` | Fernet | **NO regenerar**: sin ella no se descifran `access_token` y `pin_enc` de `wa_accounts` |
| `WA_CONFIG_ID`, `WA_PHONE_NUMBER_ID`, `WA_REGISTRATION_PIN` | [`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md) | conservar |
| `WA_SIP_PASSWORD` | `make wa-sip-password` (la trae de Meta) | regenerable |
| `HF_TOKEN` | opcional | — |
| `RCLONE_REMOTE`, `BACKUP_GPG_RECIPIENT`, `ALERT_NTFY_TOPIC`, `HEALTHCHECKS_PING_URL` | pendientes (bloque "Operación" de `.env.example`) | — |

Variables del `.env` actual que el código no usa: `AGENT_NAME`, `COMPANY_NAME`, `VLLM_TTS_SPEED`. Se
pueden omitir.

## 4. Restaurar datos

### 4.1 Checkpoint del TTS (obligatorio: sin él `vllm-tts` no arranca, y `app`/`agent` lo esperan)

```bash
cd ~/voice-as-a-service
mkdir -p tts/finetune/work/runs/multi41/lr2e-6
rsync -a <origen>/lr2e-6-checkpoint-epoch-2/ tts/finetune/work/runs/multi41/lr2e-6/checkpoint-epoch-2/
sha256sum tts/finetune/work/runs/multi41/lr2e-6/checkpoint-epoch-2/model.safetensors
```

`<origen>`: `viejo:~/atentina-backups/tts` o `viejo:~/voice-as-a-service/tts/finetune/work/runs/multi41/lr2e-6`
(con el `checkpoint-epoch-2` al final). El sha256 de `model.safetensors` (3.833.402.520 bytes) tiene
que ser `9cf9298d1809519ab5e9b9c809ca8d7f89a14124f7278798634621e705fab247`. El directorio es
autosuficiente: `vllm-tts` sirve de `/models/ft` sin bajar el modelo base de Hugging Face. Para
reentrenar en el nuevo, llevar también el resto de `tts/finetune/work/` (41 GB).

Último recurso sin checkpoint: reentrenar ([`TTS_FINETUNE.md`](TTS_FINETUNE.md); OpenSLR 61 y
`Qwen/Qwen3-TTS-12Hz-1.7B-Base`, horas de GPU).

### 4.2 Base

El dump es SQL plano de PostgreSQL 16 (`pg_dump --no-owner`, sin GRANT): usuario y clave de
Postgres pueden ser nuevos. **Orden obligatorio: restaurar antes del primer `make up`/`make up-agent`/`make migrate`**,
porque esos corren el seed sobre la base vacía y el dump choca con las filas que ya existen. Y
`make livekit-sip` lee `phone_numbers`: sin la base restaurada crea el trunk entrante sin los números.

```bash
cd ~/voice-as-a-service
make build                                       # imágenes propias (también lo hace make up)
docker compose up -d --wait --no-deps db         # volumen vacío: crea POSTGRES_DB del .env
zcat <dump>.sql.gz | docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
make migrate                                     # Alembic sigue desde la versión del dump; seed idempotente
make psql   # verificar: select version_num from alembic_version;  (0008 al 8-oct-2026; la última de migrations/versions/)
```

Referencia (6-oct-2026): 4 tiers, 2 clientes, 7 agentes, 3 números, 2 `wa_accounts`, 2 usuarios.
Ruteo: `+543517002592` y `+548002201233` → `atentina_comercial`; `+543517003976` →
`traductor_ingles_realtime`.

Si el volumen ya se había inicializado (por ejemplo, se corrió `make up` antes): parar `app` y
`agent`, `docker compose rm -sf db`, `docker volume rm voice-as-a-service_postgres_data` y repetir.
Alternativa al dump: copiar el volumen entero con el viejo parado, conservando las mismas `POSTGRES_*`.

**Sin backup:** el seed (`make migrate`) solo crea el tier Interno, el cliente `atentina`, los
agentes de referencia y el número `ANURA_DID` ruteado a `WORKFLOW_ID` (`demo_booking_classic`, no
`atentina_comercial` como hoy). Lo demás (tiers comerciales Mostrador/Sucursal/Central, cliente
`browix`, agentes editados, los otros números, cuentas de WhatsApp, usuarios) se recrea a mano por
la UI o la API, y las ediciones de agentes posteriores a `app/agents/reference/*.json` se pierden.

### 4.3 Certificado SIP de WhatsApp

Con el registro A `sip` ya apuntando a la IP pública (sección 7): `make sip-cert` (corre certbot por
DNS-01 de Cloudflare con `CLOUDFLARE_DNS_API_TOKEN`; deja `asterisk/letsencrypt/`). Sin certificado,
Asterisk arranca con "WhatsApp apagado". Alternativa: `sudo rsync -a viejo:~/voice-as-a-service/asterisk/letsencrypt/ asterisk/letsencrypt/`.

### 4.4 Pesos de los modelos

**LLM Gemma (obligatorio).** No está en el volumen de HF: va a `~/Models` y el override lo monta. Descarga
con la revisión que sirve el viejo (anotada el 8-oct-2026 de `.cache/huggingface/` del directorio):

```bash
mkdir -p ~/Models
docker run --rm -v ~/Models:/m python:3.12-slim sh -c 'pip -q install "huggingface_hub[cli]" && \
  hf download cyankiwi/gemma-4-26B-A4B-it-qat-AWQ-INT4 --revision 18a3c7285c33ee39d3e5e16ee6fb2c18f4955ef9 \
  --local-dir /m/gemma-4-26B-A4B-it-qat-AWQ-INT4'
sha256sum ~/Models/gemma-4-26B-A4B-it-qat-AWQ-INT4/model.safetensors
# c0b6bbe9bacded55f45cd600c703ca299ebfb79efb2ec25023bc6bb563deb201
```

Alternativa sin internet: `rsync -a viejo:~/Models/gemma-4-26B-A4B-it-qat-AWQ-INT4 ~/Models/` y el mismo
`sha256sum`. Que el dueño sea el usuario del repo (el contenedor lo lee como `ro`).

**Volumen de HF (opcional, ahorra la descarga).** En el viejo, Parakeet (y el Qwen, solo si se quiere poder
volver a él):

```bash
docker run --rm -v voice-as-a-service_hf_cache:/v -v $PWD/scratch:/o alpine \
  tar czf /o/hf.tgz -C /v hub/models--RedHatAI--Qwen3.5-9B-quantized.w4a16 hub/models--nvidia--parakeet-tdt-0.6b-v3
```

En el nuevo, `docker volume create voice-as-a-service_hf_cache` y extraer con el mismo `docker run`
(`tar xzf /o/hf.tgz -C /v`). No copiar el volumen entero (80 GB, mayormente modelos descartados).

## 5. Levantar por partes (sin Asterisk ni túnel)

### 5.1 Imágenes

`vllm/vllm-openai:latest` no está fijada (ni en `docker-compose.yml` ni en `stt/Dockerfile`): en un
server nuevo bajaría otra versión que la medida en CAP-001. Bajar la misma:

```bash
docker pull vllm/vllm-openai@sha256:c2914767605584b6d8f45686b82de173ecc99e781897aa3d0a66dacd72c51ae1
docker tag vllm/vllm-openai@sha256:c2914767605584b6d8f45686b82de173ecc99e781897aa3d0a66dacd72c51ae1 vllm/vllm-openai:latest
make build
```

Cambiar de versión de vLLM es un cambio de config: se mide con el test de capacidad.

### 5.2 Topes de GPU antes de la inferencia

`sudo deploy/install.sh` aplica los topes ya (280 W, núcleo ≤ 1800 MHz, memoria 9501 MHz,
*persistence mode*) y habilita las unidades (ver 8.1 por las precondiciones del arranque).
**Mientras el viejo siga en servicio, `sudo systemctl disable atentina-stack` enseguida:** si el
nuevo se reinicia, `deploy/boot.sh` levanta todo, Asterisk y túnel incluidos, y choca con el viejo.
Los topes (`atentina-gpu-limits`) quedan activos. Se vuelve a habilitar en el corte (sección 9).
Verificar `nvidia-smi --query-gpu=index,power.limit --format=csv`: 280 W en las dos. **Sin tope, dos
3090 ya apagaron el server por un pico.**

### 5.3 Inferencia

`make up-inference` (espera healthy; con pesos en disco: LLM ~1 min, TTS ~1,5 min; la primera vez
suma la descarga). Verificar (`K` = `VLLM_API_KEY`, sin imprimirla):

```bash
K=$(grep ^VLLM_API_KEY= .env | cut -d= -f2-)
make health
for p in 8101 8102 8103; do
  echo "$p sin auth: $(curl -s -o /dev/null -w '%{http_code}' localhost:$p/v1/models)" \
       "con auth: $(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $K" localhost:$p/v1/models)"
done                                                         # 401 y 200
curl -s -H "Authorization: Bearer $K" localhost:8103/v1/audio/voices   # 41 voces + "default" (nunca usarla)
curl -s -o scratch/hola.wav -H "Authorization: Bearer $K" -H 'Content-Type: application/json' \
  localhost:8103/v1/audio/speech \
  -d "{\"model\":\"$(grep ^VLLM_TTS_MODEL= .env | cut -d= -f2-)\",\"voice\":\"sofia\",\"input\":\"Hola, te habla el agente.\",\"response_format\":\"wav\"}"
curl -s -H "Authorization: Bearer $K" -F file=@scratch/hola.wav -F response_format=json \
  localhost:8102/v1/audio/transcriptions                    # el texto de arriba
nvidia-smi --query-gpu=index,memory.used --format=csv       # GPU 0 ~21–22,7 GB; GPU 1 ~15,7–16 GB
```

**Nunca pedir TTS sin `voice` o con `voice="default"`:** mata el engine de `vllm-tts`. En
`make logs S=vllm-tts` tiene que aparecer `Loaded 41 supported speakers`.

### 5.4 Base, app, agente y LiveKit

```bash
docker compose up -d --wait livekit-redis livekit livekit-sip
make up-agent          # db + migrate + app + agent (con la base ya restaurada, 4.2)
make livekit-sip       # trunks y dispatch rule con los números de la base
docker compose up -d proxy
make ps                # todo healthy salvo asterisk y tunnel, que no se levantan todavía
curl -s localhost:8011/health
```

Login en `http://<IP LAN>:8011` con un admin existente. No usar `make up` en esta fase: levanta
también Asterisk.

## 6. Red y router (usuario)

Todo hacia la IP de la LAN del server (hoy `192.168.1.99`, reserva DHCP). Esta es la lista completa
y vigente; README, `.env.example` y otros docs remiten acá.

| Puerto | Para qué | ¿Reenviar? |
|---|---|---|
| UDP 10000–10199 | RTP de Asterisk: audio de Anura y de WhatsApp (`ASTERISK_RTP_START/END`) | **sí** |
| TCP 5061 | SIP/TLS de Meta, llamadas de WhatsApp (`WA_SIP_PORT`, desde el 6-oct-2026) | **sí** |
| UDP 7882 | WebRTC de LiveKit: demo de la landing | **sí** |
| TCP 7881 | WebRTC de LiveKit por TCP (respaldo) | **sí** |
| UDP 5080 | SIP LiveKit ↔ Asterisk. Solo con LiveKit Cloud; abierto, permite fraude telefónico | no |
| UDP 5081 | SIP de Anura: entra por el agujero que abre el REGISTER | no |
| UDP/TCP 5060, UDP 20000–20199 | `livekit-sip`, tramo local | no |
| TCP 7880, TCP 8011 | LiveKit y app: salen por el túnel de Cloudflare | no |
| TCP 8100 | Proxy de inferencia: solo para el modo remoto o el loadtest, abrir temporalmente | no |
| 5432, 6380, 8101–8103 | solo localhost | no |

- **SIP ALG apagado** en el router.
- Salida que tiene que estar permitida: UDP 55090 a `ANURA_DOMAIN` (registro), RTP hacia las redes
  de Anura (`asterisk/conf/pjsip.conf`, `identify`), 443 para cloudflared, Let's Encrypt y api.ipify.org.
- Si se prende `ufw` en el host, abrir lo mismo.
- PENDIENTE (usuario): modelo del router (hoy "Huawei de Telecom"), URL del panel, dónde están la
  reserva DHCP y los reenvíos, si el SIP ALG está apagado, y si la IP fija es de plan residencial o
  de empresa.

## 7. Servicios externos

| Servicio | ¿Cambia al mudar con la misma IP pública? | ¿Y si cambia la IP pública? | Quién |
|---|---|---|---|
| Túnel `atentina-demo` (ID `16331de8-fb8c-4287-9563-5abd44d6ab3d`, ingress remoto: `api.` `^/api/v1/demo/` → `localhost:8011`, `rtc.` → `localhost:7880`, `wa.` `^/wa/webhook` → `localhost:8011`, `app.` → `localhost:8011`) | no: el mismo `CLOUDFLARE_TUNNEL_TOKEN` registra el conector nuevo. **Parar el del viejo antes** | no | agente |
| DNS `atentina.com.ar`: registro A `sip` (DNS only) | no | sí: A `sip` → IP nueva. Verificar `dig +short sip.atentina.com.ar @1.1.1.1` | usuario |
| DNS: CNAME del túnel, Render, Resend, Email Routing, DMARC, Search Console | no | no | — |
| Meta: webhook (`https://wa.atentina.com.ar/wa/webhook`) y Calling (`sip.atentina.com.ar:5061`) | no: van por hostname | no, mientras el hostname no cambie | — |
| Anura: terminal con la que se registra Asterisk | no: el registro es saliente. **Parar el Asterisk viejo antes** | confirmar si Anura tiene la IP habilitada o filtrada | usuario |
| Render (landing), Turnstile, Resend, GA, Search Console | no dependen del server | no | — |
| GitHub | clave SSH del host nuevo | — | usuario |
| ntfy, healthchecks.io, R2/B2 (backup externo) | pendientes de alta | — | usuario |

Si cambia la IP pública, además: `LIVEKIT_NODE_IP` y `PUBLIC_HOST` en `.env` (Asterisk la detecta
solo si `ASTERISK_PUBLIC_ADDRESS` está vacío).

Detalle de cada alta: [`LANDING.md`](LANDING.md) (Cloudflare, Render, Turnstile, Resend, túnel),
[`WHATSAPP_PLAN.md`](WHATSAPP_PLAN.md) 5.3–5.4 (Meta, SIP), [`TELEFONIA_ANURA.md`](TELEFONIA_ANURA.md) 2 (Anura).

## 8. systemd, cron y topes de GPU

### 8.1 systemd

Precondiciones de `sudo deploy/install.sh` (graba en las unidades la ruta y el dueño del repo):
repo en su ruta final, `.env` completo con `COMPOSE_FILE`, checkpoint en `TTS_FT_CKPT`, imágenes
construidas (`deploy/boot.sh` no hace build) y usuario en el grupo `docker`. Instala
`atentina-gpu-limits` (topes en cada arranque) y `atentina-stack` (compose, túnel, trunks SIP y
calentamiento del TTS en el arranque). Verificar: `systemctl is-enabled atentina-gpu-limits atentina-stack`.

### 8.2 Cron del usuario

Instalarlo después del corte (antes, el chequeo marca falta de Asterisk y túnel, y el backup
respalda una base que todavía se va a reemplazar).

```bash
mkdir -p ~/atentina-ops ~/atentina-backups
crontab -e
```

Con estas líneas (ajustar la ruta si el home no es `/home/laureano`):

```
# Atentina (docs/PRODUCCION.md): backup diario, chequeo cada 2 min y certificado SIP
30 3 * * * /home/laureano/voice-as-a-service/scripts/ops/backup.sh >> $HOME/atentina-ops/backup.log 2>&1
*/2 * * * * /home/laureano/voice-as-a-service/scripts/ops/healthcheck.sh >/dev/null 2>&1
15 4 * * * /home/laureano/voice-as-a-service/scripts/ops/sip-cert-renew.sh >> $HOME/atentina-ops/sip-cert.log 2>&1
```

`sip-cert-renew.sh` necesita `CLOUDFLARE_DNS_API_TOKEN` y `WA_SIP_PASSWORD` en `.env`. Sin esa línea,
el certificado de `sip.atentina.com.ar` vence (el actual, el 4-ene-2027; renovarlo sin el cron:
`scripts/ops/sip-cert-renew.sh`) y Meta deja de entregar las
llamadas de WhatsApp. Verificar a mano una vez: `scripts/ops/backup.sh` (dice "backup ok") y
`scripts/ops/healthcheck.sh; echo $?` (0, después del corte).

## 9. Corte y pruebas de punta a punta

Ventana: avisar, elegir un horario sin campañas; 15–30 min sin servicio.

1. **En el viejo:** `docker compose stop asterisk app agent` y
   `docker compose -f docker-compose.tunnel.yml stop tunnel`. Asterisk se desregistra de Anura y
   cloudflared deja el túnel. `sudo systemctl disable atentina-stack` para que no vuelvan si se reinicia.
2. **Dump final en el viejo:** `scripts/ops/backup.sh`; copiar el `.sql.gz` nuevo al nuevo.
3. **En el nuevo:** volver a restaurar la base con ese dump (4.2, con el volumen recreado) y
   `make livekit-sip`.
4. **Router (usuario):** reserva DHCP y reenvíos de la sección 6 hacia el nuevo. Si el nuevo toma
   `192.168.1.99`, revisar `LIVEKIT_URL` y `LIVEKIT_LOCAL_NODE_IP` del `.env` y `make up`.
5. **DNS (usuario), solo si cambió la IP pública:** A `sip` → IP nueva; `make sip-cert`.
6. **En el nuevo:** `make up` (levanta todo, incluido Asterisk, y recrea los trunks), `make up-tunnel`
   y `sudo systemctl enable atentina-stack`.
7. **Cron** (8.2) y en el viejo comentar las 3 líneas de Atentina (`crontab -e`), para que no corra el chequeo ni
   la renovación del certificado contra un stack parado.

Pruebas (todas tienen que dar lo esperado antes de dar el corte por bueno):

| # | Prueba | Esperado |
|---|---|---|
| 1 | `nvidia-smi --query-gpu=index,power.limit,memory.used --format=csv` | 280 W en las dos; GPU 0 ~21–22,7 GB, GPU 1 ~15,7–16 GB |
| 2 | `make ps` y `make health` | todo `healthy`/OK |
| 3 | `make pbx-status` | `anura/sip:...:55090 Registered` |
| 4 | `docker compose exec asterisk asterisk -rx 'pjsip show transports'` | `transport-anura` udp 5081, `transport-livekit` udp 5080, `transport-whatsapp` tls 5061 |
| 5 | `make logs S=asterisk \| grep 'Asterisk: SIP'` | la IP pública correcta y `tls/5061 (WhatsApp, sip.atentina.com.ar)` |
| 6 | `lk sip inbound list`, `lk sip dispatch list`, `lk sip outbound list` con `--url http://127.0.0.1:7880 --api-key … --api-secret …` (de `.env`) | `anura-asterisk-inbound` con los 3 números, `anura-asterisk-dispatch`, `anura-asterisk-outbound` → `127.0.0.1:5080` |
| 7 | Entrante: llamar al 351 700-2592, al 0800-220-1233 y al 351 700-3976 desde un celular | `make logs S=asterisk`: "Entrante de Anura: … -> +54…"; atiende el agente de cada número |
| 8 | Saliente desde la UI a un celular propio | "Saliente a Anura: <10 dígitos> (caller ID …)" y audio en los dos sentidos |
| 9 | Durante una llamada: `make pbx-cli` → `pjsip show channelstats` | paquetes recibidos > 0 en las dos patas |
| 10 | `curl -sI https://app.atentina.com.ar/health` | 200, con `strict-transport-security` y `content-security-policy` |
| 11 | `curl -s -o /dev/null -w '%{http_code}' 'https://wa.atentina.com.ar/wa/webhook?hub.mode=subscribe&hub.verify_token=x&hub.challenge=1'` | 403 (llega y rechaza el token) |
| 12 | Desde fuera de la LAN: `openssl s_client -connect sip.atentina.com.ar:5061 -tls1_2` | certificado válido de `sip.atentina.com.ar` |
| 13 | Llamada de WhatsApp al +54 9 351 700-2592 desde un WhatsApp personal | "Entrante de WhatsApp" en el log de Asterisk; atiende `atentina_comercial` |
| 14 | Mensaje de WhatsApp al mismo número | responde el agente |
| 15 | Demo de la landing desde un celular con datos móviles | conecta y se escucha (UDP 7882 y la IP pública) |
| 16 | `scripts/ops/healthcheck.sh; echo $?` y `tail ~/atentina-ops/health.log` | 0 / ok |
| 17 | Reiniciar el host una vez y repetir 1–7 | `atentina-stack` deja todo arriba (`journalctl -u atentina-stack`) |
| 18 | Test de capacidad `base` ([`capacity/README.md`](capacity/README.md)) | cambio de hardware → registrar `CAP-NNN` |

### Vuelta atrás

Mientras el viejo no se borre:
1. En el nuevo: `docker compose stop asterisk app agent` y `docker compose -f docker-compose.tunnel.yml stop tunnel`.
2. Router: reserva y reenvíos de vuelta al viejo (usuario). DNS `sip`, si se había cambiado.
3. En el viejo: `docker compose start asterisk app agent`,
   `docker compose -f docker-compose.tunnel.yml start tunnel` y `sudo systemctl enable atentina-stack`.
4. Las conversaciones creadas en el nuevo se pierden, salvo que se haga un dump y se restaure en el viejo.

Dejar el viejo apagado (no borrado) al menos 30 días, con `atentina-stack` deshabilitado.

## 10. Trampas conocidas

- **Backup del checkpoint con otro nombre:** `backup.sh` lo guarda como
  `tts/lr2e-6-checkpoint-epoch-2`, sin `multi41`. Restaurarlo en la ruta de `TTS_FT_CKPT` (4.1).
- **`vllm/vllm-openai:latest` sin fijar** (5.1). Con vllm-omni ya pasó que `latest` no arrancaba.
- **Redis de LiveKit sin persistencia:** después de cada reinicio, `make livekit-sip` (lo hacen
  `make up` y `deploy/boot.sh`); si no, las entrantes dan 486 `flood`.
- **El seed no pisa el ruteo** de un número existente, pero en una base vacía rutea `ANURA_DID` a
  `WORKFLOW_ID` (4.2).
- **`make db-reset`** borra `$(notdir $(CURDIR))_postgres_data`: depende del nombre del directorio.

## 11. Checklist final

- [ ] `git status` limpio en el viejo y todo pusheado (sección 1)
- [ ] Host: Ubuntu 24.04, zona horaria, driver 580, Docker + grupo, toolkit, paquetes (2)
- [ ] Repo en `~/voice-as-a-service`; `.env` revisado con diff enmascarado (3)
- [ ] Checkpoint y pesos de Gemma con sha256 correcto; base restaurada en 0008 o posterior; certificado SIP (4)
- [ ] Imagen de vLLM por digest; topes de GPU en 280 W; inferencia con smoke test (5)
- [ ] Router: reserva DHCP, 4 reenvíos, SIP ALG apagado (6)
- [ ] Viejo: Asterisk y túnel parados, `atentina-stack` deshabilitado (9)
- [ ] systemd instalado, `atentina-stack` habilitado después del corte y probado con un reinicio; cron con las 3 líneas (8)
- [ ] Pruebas 1–17 en verde; CAP-NNN registrado (9)
- [ ] Copia externa del backup configurada (pendiente desde el 2-oct-2026)

## 12. PENDIENTE (usuario)

- **Copia externa del backup:** proveedor y bucket (`RCLONE_REMOTE`, ej. `r2:atentina-backups`),
  ID de la clave GPG (`BACKUP_GPG_RECIPIENT`) y dónde se guarda la clave privada (fuera del server).
  Mientras no exista, perder el server es perder base, `.env` (con `WA_TOKEN_KEY`) y checkpoint.
- **Router:** modelo, URL del panel, dónde están reserva DHCP y reenvíos, estado del SIP ALG.
- **Anura:** cuenta dueña de los números y terminal que usa Asterisk; DIDs (3517002592, 3517003976,
  0800-220-1233) con su plan de llamada y cómo llega el 0800 en la Request-URI; si Anura tiene
  registrada o filtrada la IP 181.104.113.28; canales contratados (10, según `rtp.conf`); qué pasa
  con dos registros de la misma terminal.
- **Meta:** nombre y rol del system user, activos asignados, permisos y vencimiento de
  `WA_ACCESS_TOKEN`; WABA de cada número (hoy 1106296902266123 para el 351 700-2592 y
  1763082738667089 para el de prueba).
- **Cloudflare:** email de la cuenta, modo SSL/TLS, lista de API tokens (nombre y permisos, sin el
  valor), registrador y vencimiento de los dos dominios.
- **Cuentas:** quién tiene acceso a cada panel (Cloudflare, Render y su rama, Meta, Resend, Anura,
  GA, LiveKit Cloud de respaldo) y dónde están las credenciales.
- **Decisión:** fijar `vllm/vllm-openai` por tag o digest en `docker-compose.yml` y `stt/Dockerfile`,
  y el `apk` de Asterisk, como ya está `vllm-omni`.
