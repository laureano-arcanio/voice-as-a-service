# AIVA Validate — Demo MVP

Mini producto demo de AIVA Validate: un agente de IA llama por telefono a un cliente
que compro un plan de ahorro, hace el cuestionario de validacion configurado, y asigna
score + resultado (aprobado / a definir / rechazado) evaluando el transcript con un LLM.

## Stack

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy (MySQL) + Jinja2, servido con uvicorn.
- **Frontend:** HTML + Vanilla JS (sin frameworks).
- **Voz:** LiveKit Agents (STT + LLM + TTS, los 3 servidos localmente con vLLM/vLLM-Omni
  sobre GPU propia — ver "Inferencia local" abajo) sobre una troncal SIP saliente de
  Twilio, corriendo como un worker propio (`app/livekit_agent.py`, proceso/contenedor
  separado). La app (`app/main.py`) solo despacha el agente a una room nueva
  (`app/livekit_dispatch.py`); el worker marca al cliente y escribe el resultado
  (transcript, status, score) directo en la base de datos — no hay webhook.
- **Scoring:** el mismo LLM local evalua el transcript contra el cuestionario (respuesta
  correcta de referencia + ponderacion + flag de requerida) y aplica las bandas de score.

## Inferencia local (vLLM)

No se usan proveedores externos de inferencia (OpenAI, ElevenLabs, Anthropic): LLM, STT
y TTS corren en 3 contenedores propios (`vllm-llm`, `vllm-stt`, `vllm-tts` en
`docker-compose.yml`) contra la GPU del host, cada uno con API compatible con OpenAI. El
codigo le habla a los 3 con el mismo `openai` SDK (via los plugins `livekit.plugins.openai`),
apuntando `base_url` a cada contenedor en vez de a `api.openai.com`.

| Rol | Modelo | Variable | Endpoint | Por que |
| --- | --- | --- | --- | --- |
| LLM en vivo + scoring | `Qwen/Qwen3.5-4B` | `VLLM_LLM_MODEL` | `/v1/responses`, `/v1/chat/completions` | Dense, 262K ctx, soporte dia-0 de vLLM. Se invoca con `reasoning_effort=none` para no perder latencia en cadena de razonamiento. |
| STT | `Qwen/Qwen3-ASR-1.7B` | `VLLM_STT_MODEL` | `/v1/audio/transcriptions` | Soporte dia-0 de vLLM (imagen oficial `qwenllm/qwen3-asr`). Es REST por-turno, no una sesion realtime por WebSocket como `gpt-live-transcribe` (que se usaba antes) -- sin transcript parcial mientras el cliente habla. |
| TTS | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | `VLLM_TTS_MODEL` | `/v1/audio/speech` (streaming) | Servido con vLLM-Omni, voz clonada (`VLLM_TTS_VOICE`, default `sofia_ar`) en vez de un preset de fabrica -- ver "Voz clonada" abajo. Se probo tambien `MOSS-TTS-Realtime` (mejor soporte online oficial de vLLM-Omni en su momento) pero es estrictamente voice-cloning sin voces con nombre. |

**Requisitos de host:** 1+ GPU NVIDIA con el [NVIDIA Container
Toolkit](https://github.com/NVIDIA/nvidia-container-toolkit) instalado y configurado
(`nvidia-ctk runtime configure --runtime=docker` + reiniciar Docker) — sin esto los 3
contenedores `vllm-*` no arrancan (`docker compose up` falla al reservar el device). El
reparto de GPU/memoria entre los 3 esta documentado con detalle en los comentarios de
`docker-compose.yml` (fue bastante mas quisquilloso de lo esperado: los modelos de audio
reservan memoria fuera del budget normal de KV-cache, y vLLM sigue capturando CUDA graphs
nuevos con el trafico real, asi que el uso real de VRAM termina bien por encima de lo que
estima `--gpu-memory-utilization` en frio). Probado en vivo contra 2x RTX 3090 (24GB c/u):
LLM solo en una GPU (~17GB), STT+TTS compartiendo la otra (~23GB combinados, justo).

### Voz clonada (TTS)

El agente usa una voz clonada (espanol argentino) en vez de un preset de fabrica: mas
natural para este caso de uso y controlable en tono/acento. El checkpoint es
`Qwen/Qwen3-TTS-12Hz-1.7B-**Base**` (no `-CustomVoice`, que trae 9 presets pero tiene un bug
real -- su speaker encoder devuelve embeddings de 1024 dims contra los 2048 que espera el
talker de 1.7B, y cualquier intento de clonado con ese checkpoint tira 500 y mata el engine
entero; probado en vivo, hay que reiniciar el contenedor cada vez).

**La voz se sube UNA sola vez** (no en cada llamada -- eso seria mas lento, ver mas abajo) via:

```bash
curl -X POST http://localhost:8103/v1/audio/voices \
  -F "audio_sample=@/ruta/a/tu/muestra.wav;type=audio/wav" \
  -F "name=sofia_ar" \
  -F "consent=<referencia a la fuente/consentimiento de este audio>" \
  -F "ref_text=<transcripcion exacta de lo que dice el audio>" \
  -F "speaker_description=Voz femenina adulta con acento argentino, calida y profesional"
```

Despues de subirla, `VLLM_TTS_VOICE=sofia_ar` en `.env` la usa exactamente igual que un
preset (`openai.TTS(voice="sofia_ar", ...)`, sin cambios de codigo) -- el server infiere
que es una voz clonada por el nombre, sin hacer falta mandar `ref_audio` en cada sintesis.

La voz queda guardada en el volumen `vllm_tts_speakers` (sobrevive `docker compose down` /
recreates del contenedor). Si se pierde el volumen o se hace un deploy nuevo desde cero,
hay que volver a correr el `curl` de arriba antes de que el agente pueda hablar -- sin una
voz llamada como dice `VLLM_TTS_VOICE`, la sintesis falla.

**Latencia:** clonar agrega ~450ms de TTFB extra sobre un preset de fabrica (~500ms medido
en vivo vs ~50-60ms con un preset). Sigue siendo streaming, y el total por turno (STT+LLM+TTS)
quedo en ~1.5-1.6s en las pruebas -- aceptable para esta demo, pero es la primera palanca a
revisar si hace falta bajar mas la latencia percibida.

**Limitacion conocida:** el modo streaming (necesario para no matar la latencia de la
llamada) no soporta ajuste de velocidad -- `VLLM_TTS_SPEED` != 1.0 tira 400. Ver comentario
en `app/config.py`.

## Correr con Docker Compose

```bash
cp .env.example .env   # completar credenciales (ver "Claves necesarias" abajo)
docker compose up -d
```

Levanta seis servicios: `db` (MySQL 8), `app` (FastAPI en `:8011`), `agent` (el worker
de LiveKit, sin puerto expuesto — conecta saliente a LiveKit Cloud) y `vllm-llm` /
`vllm-stt` / `vllm-tts` (inferencia local sobre GPU, ver seccion de abajo). `app` y
`agent` esperan a que los `vllm-*` esten healthy antes de arrancar — la primera vez
tarda varios minutos (descarga de pesos + carga en GPU).

## Deploy (servidor smartcron)

- Codigo: `/var/www/html/aiva-validate/` (venv propio, `.env` con credenciales).
- Servicio: `systemd` `aiva-validate.service` → uvicorn en `127.0.0.1:8011`.
- nginx: vhost `validate.smartcron.ai` (falta DNS) + acceso directo `http://IP:8090`.
  Basic auth en todo excepto `/health`.
- MySQL: base `aiva_validate`, usuario `aiva_validate` (password en `.env` del servidor).

## Claves necesarias (completar en `.env`)

1. `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` — proyecto de LiveKit Cloud
   (Project Settings → Keys).
2. `LIVEKIT_SIP_TRUNK_ID` — troncal SIP saliente de LiveKit (ver runbook abajo).
3. Nada mas: LLM/STT/TTS corren localmente (ver "Inferencia local (vLLM)" arriba), no
   hace falta ninguna API key de proveedor externo. `HF_TOKEN` es opcional, solo si
   algun modelo llegara a requerir aceptar licencia en HuggingFace.

### Runbook: Twilio + LiveKit (configuracion manual, una sola vez)

**Twilio:**
1. Comprar/confirmar un numero de Twilio con capacidad de voz.
2. `twilio api trunking v1 trunks create --friendly-name "aiva-validate-outbound" --domain-name "aiva-validate.pstn.twilio.com"` → guardar el trunk SID.
3. Consola → Voice → Credential Lists → crear una (usuario + password SIP).
4. Consola → Elastic SIP Trunking → tu trunk → Termination → Authentication → asociar esa Credential List.
5. `twilio api trunking v1 trunks phone-numbers create --trunk-sid <TK...> --phone-number-sid <PN...>`.
6. Consola → Voice → Settings → Geo Permissions → confirmar que el pais de destino este habilitado (falla silenciosa comun en cuentas nuevas).

**LiveKit Cloud:**
1. Project → Settings → Keys: copiar `LIVEKIT_URL` (`wss://...livekit.cloud`), `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`.
2. Instalar/autenticar el CLI `lk` contra el proyecto.
3. `outbound-trunk.json`:
   ```json
   {
     "trunk": {
       "name": "aiva-validate-outbound",
       "address": "aiva-validate.pstn.twilio.com",
       "numbers": ["+1XXXXXXXXXX"],
       "authUsername": "<de Twilio paso 3>",
       "authPassword": "<de Twilio paso 3>"
     }
   }
   ```
4. `lk sip outbound create outbound-trunk.json` → guardar el `ST_...` impreso como `LIVEKIT_SIP_TRUNK_ID`.

Despues de editar `.env`: `docker compose up -d` (o `systemctl restart aiva-validate aiva-validate-agent` en el deploy bare-metal).

## Flujo

1. Dashboard → ingresar numero E.164 → **Llamar** → se crea el registro y la app
   despacha el worker de LiveKit a una room nueva (`call-<id>`).
2. El worker (`app/livekit_agent.py`) marca al cliente por la troncal SIP, corre la
   conversacion (STT/LLM/TTS), y al terminar escribe directo en la base: status,
   ended_reason, duration, transcript y dispara el scoring — todo en el mismo proceso,
   sin webhook.
3. El scoring evalua cada pregunta contra su respuesta de referencia: suma puntos de las
   correctas, aplica las bandas, y si una pregunta *requerida* fallo y el score aprobaba,
   el resultado baja a "a definir".
4. Detalle de llamada: transcript estilo chat, tabla de scoring con justificacion por
   pregunta y criterio aplicado. (La grabacion de audio no esta implementada en esta
   version — LiveKit Egress requeriria un bucket S3-compatible propio.)
