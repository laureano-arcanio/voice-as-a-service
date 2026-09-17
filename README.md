# AIVA Validate — Demo MVP

Mini producto demo de AIVA Validate: un agente de IA llama por telefono a un cliente
que compro un plan de ahorro, hace el cuestionario de validacion configurado, y asigna
score + resultado (aprobado / a definir / rechazado) evaluando el transcript con un LLM.

## Stack

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy (MySQL) + Jinja2, servido con uvicorn.
- **Frontend:** HTML + Vanilla JS (sin frameworks).
- **Voz:** LiveKit Agents (STT OpenAI `gpt-live-transcribe` en streaming + LLM OpenAI
  `gpt-5.4-nano` + TTS ElevenLabs) sobre una troncal SIP saliente de Twilio, corriendo como un worker
  propio (`app/livekit_agent.py`, proceso/contenedor separado). La app (`app/main.py`)
  solo despacha el agente a una room nueva (`app/livekit_dispatch.py`); el worker marca
  al cliente y escribe el resultado (transcript, status, score) directo en la base de
  datos — no hay webhook.
- **Scoring:** OpenAI (`gpt-5.4-mini`) evalua el transcript contra el cuestionario (respuesta
  correcta de referencia + ponderacion + flag de requerida) y aplica las bandas de score.

## Correr con Docker Compose

```bash
cp .env.example .env   # completar credenciales (ver "Claves necesarias" abajo)
docker compose up -d
```

Levanta tres servicios: `db` (MySQL 8), `app` (FastAPI en `:8011`) y `agent` (el
worker de LiveKit, sin puerto expuesto — conecta saliente a LiveKit Cloud).

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
3. `OPENAI_API_KEY` (STT en vivo + LLM conversacional + motor de scoring, misma cuenta
   para todo) y `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` (solo TTS: elegir una voz
   en espanol desde tu Voice Library de ElevenLabs) — proveedores que usa el agente
   en vivo.

### Modelos de OpenAI (elegidos por latencia)

| Rol | Variable | Default | Por que |
| --- | --- | --- | --- |
| STT en vivo | `OPENAI_STT_MODEL` | `gpt-live-transcribe` | Modelo de transcripcion en vivo de OpenAI (jul-2026), realtime-only por WebSocket, emite parciales mientras el cliente habla. `gpt-4o-transcribe` / `gpt-4o-mini-transcribe` solo devuelven texto al cerrar el turno. |
| LLM en vivo | `OPENAI_MODEL` | `gpt-5.4-nano` | El modelo mas chico y rapido de OpenAI (mar-2026). Se invoca con `reasoning_effort=none` y `verbosity=low`. |
| Scoring | `OPENAI_SCORING_MODEL` | `gpt-5.4-mini` | Corre al colgar, no afecta la latencia de la llamada; un escalon mas de calidad para juzgar respuestas. Se puede bajar a `gpt-5.4-nano`. |

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
