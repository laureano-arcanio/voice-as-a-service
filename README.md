# AIVA Ventas (Browix) — Demo MVP

Mini producto demo: un agente de IA (asesora comercial virtual de [Browix](https://browix.com),
plataforma de gestion de personal) **atiende las llamadas de personas interesadas**, responde
sus consultas sobre el producto, califica el lead con el cuestionario configurado y cierra con
una demo con un asesor. Al cortar, un LLM evalua el transcript y asigna score + temperatura del
lead (caliente / tibio / frio). Tambien puede llamar (saliente) a un lead que dejo sus datos.
Contexto del negocio, base de conocimiento y links relevados: `docs/Browix_Contexto_Agente.md`.

## Stack

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy (MySQL) + Jinja2, servido con uvicorn.
- **Frontend:** HTML + Vanilla JS (sin frameworks).
- **Voz:** LiveKit Agents (STT + LLM + TTS, los 3 servidos localmente con vLLM/vLLM-Omni
  sobre GPU propia — ver "Inferencia local" abajo) sobre una troncal SIP (Anura via un
  Asterisk propio, ver "Telefonia" abajo; o Twilio), corriendo como un worker propio
  (`app/livekit_agent.py`, proceso/contenedor
  separado). La app (`app/main.py`) solo despacha el agente a una room nueva
  (`app/livekit_dispatch.py`); el worker marca al cliente y escribe el resultado
  (transcript, status, score) directo en la base de datos — no hay webhook.
- **Scoring:** el mismo LLM local evalua el transcript contra el cuestionario de calificacion
  (criterio de cada pregunta + ponderacion + flag de requerida) y aplica las bandas de score.

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
TTS sola en una GPU, LLM+STT compartiendo la otra -- la mejor de las configuraciones
medidas (ver `docs/experiments/` y `AGENTS.md`).

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

### Probar otros STT (perfil `stt-eval`, opcional)

Dos candidatos para comparar contra Qwen3-ASR, con el mismo
`/v1/audio/transcriptions` y el mismo `VLLM_API_KEY` (el agente los usa sin tocar codigo):

| Servicio | Modelo | Como corre | Puerto host |
| --- | --- | --- | --- |
| `stt-parakeet` | `nvidia/parakeet-tdt-0.6b-v3` | `stt/server.py` + transformers, GPU 0 (~1.6GB) | `:8105` |
| `stt-whisper` | `openai/whisper-large-v3-turbo` | vLLM nativo, GPU 0 (~4GB) | `:8106` |

```bash
make stt-eval-up STT=stt-parakeet   # build + levanta UNO (baja el otro) y espera healthy
make stt-eval                        # WER + latencia de vllm-stt vs ese candidato
make stt-eval ARGS="--telephone"     # idem con el audio degradado a 8kHz mu-law (llamada real)
make stt-eval-down                   # lo baja y libera la VRAM
```

Se levantan de a uno, nunca los dos juntos.

Para probar uno en llamadas reales: `VLLM_STT_BASE_URL` + `AGENT_STT_MODEL` en `.env`
(ver `.env.example`) y `docker compose up -d agent`.

**Loadtest de los candidatos** (loadtest en otra PC, como en `docs/experiments/`):
`make servers-whisper`, `make servers-parakeet` o `make servers-qwen` (la vigente) dejan
este host como server de inferencia con ese STT. Para los candidatos usan el override
`docker-compose.stt-candidates.yml`, que apaga `vllm-stt` y pone el candidato en su
lugar, la GPU 1 junto a la LLM, porque TTS no comparte GPU (ver `AGENTS.md`). Se mide uno
por vez; la PC del loadtest le pega con `VLLM_STT_BASE_URL=https://$NGROK_DOMAIN/stt-<nombre>/v1`
y `VLLM_STT_MODEL=<modelo>` en su `.env` (alla no corre `vllm-stt`, asi que ahi si se
cambia `VLLM_STT_MODEL`). Runbook en `docs/experiments/README.md`, seccion "STT candidatos". Parakeet expone
`/metrics` con los nombres de vLLM, asi que `sampler.py`/`analyze.py` lo miden
igual que al resto.

Primera medicion (sep-2026, 9 audios del corpus del load test, requests de a uno, audio
limpio / telefonico):

| STT | WER | Latencia p50 |
| --- | --- | --- |
| Qwen3-ASR-1.7B (actual) | 5.6% / 7.4% | 71 / 83 ms |
| Parakeet TDT 0.6B v3 | 5.6% / 5.6% | 53 / 50 ms |
| Whisper Large v3 Turbo | 5.6% / 5.6% | 73 / 71 ms |

Ojo con el corpus: es voz sintetica del propio `vllm-tts`, frases cortas, 9 audios -- sirve
para descartar, no para decidir.

**Corpus con voces argentinas reales:** `make stt-corpus` arma 300 frases leidas de OpenSLR 61
(Google es-AR, CC BY-SA 4.0): 150 de mujeres (31 hablantes) y 150 de hombres (13 hablantes).
Salen en `scripts/stt_corpus/data/openslr61/`, sin versionar, en 4 variantes:

| Variante | Audio |
| --- | --- |
| `clean16k` | 16 kHz, sin degradar |
| `tel8k` | banda telefonica 300-3400 Hz, 8 kHz, G.711 mu-law |
| `tel8k_noise` | `tel8k` + ruido blanco a 10 dB SNR |
| `tel8k_cuts` | `tel8k` + micro cortes: 5% de paquetes de 20 ms perdidos, en rafagas de ~2 |

Los parametros se cambian con `ARGS` (`--snr`, `--loss`, `--burst`, `--per-gender`); detalle en
`scripts/stt_corpus/openslr61.py`. Para evaluar una variante:
`make stt-eval ARGS="--audio-dir scripts/stt_corpus/data/openslr61/tel8k --runs 1"`.
Son frases leidas: no cubren habla espontanea, respuestas cortas, numeros dictados ni ruido real
de linea.

Resultado (2026-09-22, 300 frases / 2.512 palabras, requests de a uno, sin carga). WER con numeros
normalizados (`stt_eval.py` pasa digitos y romanos a palabras), entre corchetes el intervalo de 95%
por bootstrap:

| STT | `clean16k` | `tel8k` | `tel8k_noise` | `tel8k_cuts` | Frases con error (`tel8k`) | Voseo (22 frases, `tel8k`) | Latencia p50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3-ASR-1.7B | 1.6% | 2.0% [1.4-2.6] | 6.8% | 2.3% | 14.7% | 8.0% | 115 ms |
| Whisper Large v3 Turbo | **0.9%** | 1.5% [0.9-2.3] | 7.4% | 2.3% | 9.3% | 3.7% | 78 ms |
| Parakeet TDT 0.6B v3 | 1.6% | **1.1%** [0.6-1.5] | **6.0%** | **1.8%** | **7.7%** | **2.7%** | **59 ms** |

- En `tel8k` (bootstrap pareado 95%), Parakeet es mejor que Qwen3-ASR: -0.9 puntos [-1.4, -0.4].
  Parakeet contra Whisper da -0.4 [-1.3, +0.2] y Whisper contra Qwen -0.4 [-1.1, +0.4]: con este
  corpus, ninguna de esas dos diferencias es significativa.
- Qwen3-ASR pasa el voseo a tuteo ("podes" -> "Puedes", "queres" -> "Quieres"). El LLM lo entiende
  igual, pero el transcript pierde fidelidad.
- Ninguno alucino: no hubo salidas vacias ni con el doble de palabras.
- Diferencias por genero dentro del ruido. Las referencias de OpenSLR tienen algun typo ("xilofon",
  "las mas dura"), que pone un piso de ~0.5% a todos.
- El corpus no tiene direcciones de email dictadas: 31 de las 5.739 frases de OpenSLR 61 nombran
  "mail" o "correo", pero ninguna dicta una direccion.
- Salidas crudas: `scripts/stt_corpus/data/results/<motor>_<variante>.txt`.

**Corpus de datos dictados:** `make stt-corpus-entities` (requiere `vllm-tts` arriba, ~11 min) arma
400 textos: 100 emails, 100 direcciones (~64% de Cordoba), 100 telefonos argentinos (sin +549) y
100 DNI de 8 digitos. Cada texto se sintetiza con una voz de mujer y una de hombre: son 800 audios,
1,2 h, en las mismas 4 variantes. Las voces son 20 hablantes de OpenSLR 61 clonadas por request
(`ref_audio`), sin registrar nada en `vllm-tts`. Los textos varian el estilo de dictado:
- email con punto, junto, con numeros, con guion o deletreado;
- telefono digito a digito, de a pares o por grupos, con o sin 0 y 15;
- DNI completo, por grupos, de a pares o digito a digito;
- altura de la direccion como "mil doscientos treinta y cuatro" o "doce treinta y cuatro".

`stt_eval.py` suma el acierto del dato completo (`scripts/stt_corpus/entity_match.py`), escriba
como lo escriba el STT: "larcanio arroba gmail punto com" y "larcanio@gmail.com" cuentan igual. Cada
texto se valida contra si mismo antes de sintetizarlo. Es voz sintetica: sirve para comparar motores
y encontrar fallas sistematicas, no para estimar el acierto real en produccion.

**El TTS del corpus es CosyVoice3 (`make tts-cosyvoice-up`), no `vllm-tts`:** Qwen3-TTS tartamudea
("punto co com") y corta frases en los dictados largos, y ese defecto queda en el audio, no en el STT
que se quiere medir. Peor todavia, es un defecto que sesga la comparacion: un STT con decoder LLM lo
reescribe y uno literal lo transcribe, asi que castiga al segundo. Cada audio se controla despues con
un STT literal (Parakeet, `--qa-url`): repeticiones, contenido faltante y duracion fuera de lo que
predice la velocidad de esa voz; los defectuosos se rehacen con otra semilla, hasta `--qa-rounds`
veces. Con CosyVoice3 quedaron 22 audios de 800 (2,8%) marcados, casi todos de telefono y DNI.

Resultado (2026-09-22, 800 audios = 400 textos x 2 voces, sin los 22 marcados, requests de a uno).
Acierto del dato completo; en direccion, completa / calle + altura:

| STT | Variante | Email | Telefono | DNI | Direccion |
| --- | --- | --- | --- | --- | --- |
| Qwen3-ASR | `clean16k` | 29% | 75% | **81%** | 66% / 73% |
| | `tel8k` | 30% | **76%** | **80%** | 58% / 65% |
| | `tel8k_noise` | 21% | **63%** | **72%** | 34% / 49% |
| | `tel8k_cuts` | 31% | **75%** | **79%** | 59% / 67% |
| Parakeet | `clean16k` | 23% | 59% | 68% | 59% / 70% |
| | `tel8k` | **40%** | 74% | 79% | 64% / **77%** |
| | `tel8k_noise` | 23% | 59% | **72%** | 38% / 56% |
| | `tel8k_cuts` | **34%** | 73% | 76% | **61% / 76%** |
| Whisper Turbo | `clean16k` | **41%** | 74% | 76% | **66% / 80%** |
| | `tel8k` | 20% | 70% | 70% | **65%** / **77%** |
| | `tel8k_noise` | 10% | **63%** | 64% | **40% / 62%** |
| | `tel8k_cuts` | 20% | 69% | 71% | **61%** / 75% |

- **Los emails dictados son el punto debil de los tres** (20-40% en telefonico). Es el unico dato
  personal que hoy pide el cuestionario del agente (`app/db.py`), asi que es lo que mas conviene
  atacar: repetir el dato al cliente para confirmarlo, o pedirlo deletreado.
- Con audio telefonico, Parakeet y Qwen3-ASR van parejos y arriba de Whisper en email y DNI.
- Whisper es el mejor con audio limpio (email 41%) y el que mas cae al pasar a telefonico (20%).
- El ruido blanco a 10 dB rompe todo: los emails caen al 10-23% y las direcciones completas al 34-40%.
- Los micro cortes casi no afectan: quedan dentro de un par de puntos de `tel8k`.
- **Dos numeros en direccion:** la primera cifra es la direccion completa (calle, altura, piso,
  depto, barrio y localidad); la segunda es el nucleo, calle + altura. La brecha es lo que se pierde
  en lo accesorio: Whisper en `tel8k` deja 65% completas contra 77% con calle y altura bien (dice
  "cava" por "CABA", "Alverdi" por "Alberdi"). En email, telefono y DNI no hay nucleo: el dato no se
  puede partir.

WER del mismo corpus, para comparar con el de OpenSLR (aca mas bajo es mejor):

| STT | `clean16k` | `tel8k` | `tel8k_noise` | `tel8k_cuts` |
| --- | --- | --- | --- | --- |
| Qwen3-ASR | 15.0% | 16.3% | 22.0% | 16.7% |
| Parakeet | 21.9% | **11.8%** | **17.6%** | **12.1%** |
| Whisper Turbo | 22.6% | 37.9% | 40.9% | 40.8% |

- **Por que las dos metricas:** el WER no decide sobre un dato que se copia a un sistema. Si el STT
  escribe "larcaño@gmail.com" por "larcanio@gmail.com", el WER da ~10% (parece muy bueno) pero el
  mail no sirve. Al reves, Whisper tiene 37.9% de WER en `tel8k` y aun asi acierta el 70% de los
  telefonos: su WER se infla porque escribe distinto (`@` por "arroba", digitos por palabras), y el
  acierto por entidad normaliza eso antes de comparar.
- **No comparar estos WER con los de OpenSLR** (1-2%): alla son frases leidas normales, aca es
  dictado de letras, digitos y dominios, y el audio es sintetico.
- Salidas crudas: `scripts/stt_corpus/data/results/ent2_<motor>_<variante>.txt`.

**Reproducir estas tablas** (los audios marcados con defecto de TTS se saltean solos; con
`--include-defects` se cuentan):

```bash
make stt-corpus                     # corpus de OpenSLR 61 (voces reales); no necesita GPU
docker compose stop vllm-tts        # CosyVoice3 necesita la GPU 0 para el solo
make tts-cosyvoice-up
make stt-corpus-entities            # ~45 min: sintesis + control del audio + variantes
make tts-cosyvoice-down && docker compose start vllm-tts

# los 3 STT a la vez: Whisper en la GPU 0 (con TTS), Parakeet y Qwen3-ASR en la GPU 1
STT_EVAL_GPU=1 docker compose --profile stt-eval up -d --no-deps --wait stt-parakeet
STT_EVAL_GPU=0 docker compose --profile stt-eval up -d --no-deps --wait stt-whisper
for e in qwen3-asr parakeet whisper-turbo; do
  for v in clean16k tel8k tel8k_noise tel8k_cuts; do
    make stt-eval ARGS="--engines $e --audio-dir scripts/stt_corpus/data/entities/$v --runs 1"
  done
done
make stt-eval-down                  # libera la VRAM de los candidatos
```

Cada corrida imprime su WER y su tabla de acierto por dato; las tablas de arriba son esas 12
corridas juntas. Para el corpus de OpenSLR es lo mismo cambiando `entities` por `openslr61`.

Para decidir, grabar recortes de llamadas reales (`X.wav` +
`X.txt` con el transcript correcto) y correr `make stt-eval ARGS="--audio-dir scripts/<dir>"`.
Se probo tambien Moonshine Spanish y se descarto: solo corre en CPU (su runtime trae ONNX
Runtime sin CUDA y los modelos en espanol son int8 para CPU), dio 33.3% de WER y su licencia
es no comercial para empresas de mas de USD 1M/anio.

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

### Exponer los vLLM por ngrok (opcional)

Para consumir LLM/STT/TTS desde afuera del host. Usa el perfil `ngrok` de compose:
`make up` no arranca estos contenedores, solo `make tunnel`.

1. Completar en `.env`:
   - `VLLM_API_KEY` con una clave real y larga (`openssl rand -hex 24`): los 3
     servidores vLLM la exigen como `Authorization: Bearer` en `/v1/*` (ngrok no
     agrega auth propia, esta es la unica).
   - `NGROK_AUTHTOKEN`: Dashboard de ngrok → Getting Started → Your Authtoken.
   - `NGROK_DOMAIN`: Dashboard de ngrok → Domains, sin `https://` ni path.
2. `make tunnel` (arranca un unico agente `ngrok` + el proxy `proxy`, esperando a
   que los `vllm-*` esten healthy).
3. URLs publicas — los agent endpoints de ngrok no aceptan paths (ERR_NGROK_9038)
   y el plan free da un unico endpoint, asi que hay un solo tunel al root del
   dominio y el proxy nginx (`ngrok/proxy.conf`) rutea por path a cada vLLM,
   sacando el prefijo para que llegue `/v1/...`:

   | Servicio | Base URL OpenAI-compatible      |
   | -------- | ------------------------------- |
   | LLM      | `https://$NGROK_DOMAIN/llm/v1`  |
   | STT      | `https://$NGROK_DOMAIN/stt/v1`  |
   | TTS      | `https://$NGROK_DOMAIN/tts/v1`  |
   | STT candidatos (perfil `stt-eval`) | `https://$NGROK_DOMAIN/stt-parakeet/v1`, `/stt-whisper/v1` |

   ```bash
   curl https://$NGROK_DOMAIN/llm/v1/models -H "Authorization: Bearer $VLLM_API_KEY"
   ```

Notas: en el plan free ngrok intercala una pagina de aviso solo en requests de
navegador (los clientes API no la ven; tambien se evita mandando
`ngrok-skip-browser-warning: 1`), y aplican los limites de 20k requests/mes y
1 GB/mes. Logs del tunel y del proxy: `make logs-tunnel`. Para apagarlos alcanza
con `make down` (o `docker compose stop ngrok proxy`).

### Inferencia remota: app/agent en otra PC (via ngrok)

El host GPU corre solo la inferencia (`make tunnel`); una PC sin GPU puede correr
el resto del stack (`db` + `app` + `agent`) apuntando los vLLM a las URLs de
ngrok. No hace falta tocar codigo: los plugins de LiveKit ya usan
`base_url`/`api_key` de `.env`.

1. Mismo `make setup` en la otra PC. En su `.env`:
   - `LIVEKIT_*`: los mismos del host GPU (mismo proyecto/agente).
   - `VLLM_LLM_BASE_URL=https://$NGROK_DOMAIN/llm/v1`
   - `VLLM_STT_BASE_URL=https://$NGROK_DOMAIN/stt/v1`
   - `VLLM_TTS_BASE_URL=https://$NGROK_DOMAIN/tts/v1`
   - `VLLM_API_KEY`: la misma clave real configurada en el host GPU.
   - `VLLM_LLM_MODEL` / `VLLM_STT_MODEL` / `VLLM_TTS_MODEL` / `VLLM_TTS_VOICE`:
     iguales a lo que sirve el host GPU (la voz clonada, ej. `sofia_ar`, vive en
     el volumen del `vllm-tts` del host GPU; la PC remota solo la referencia).
   - `MYSQL_*`: propios de esa PC (su `db` local).
2. `make up-remote` -> levanta `db`, espera a que este healthy, y recien ahi
   `app` + `agent` con `--no-deps` (no intenta arrancar los `vllm-*`, que en esa
   PC no existen). No correr `make up` en la PC remota.

Ojo con la latencia: cada turno de la llamada cruza por ngrok (ida y vuelta), y
el audio de STT/TTS consume el ancho de banda del plan (1 GB/mes en free).

## Deploy (servidor smartcron)

- Codigo: `/var/www/html/aiva-validate/` (venv propio, `.env` con credenciales).
- Servicio: `systemd` `aiva-validate.service` → uvicorn en `127.0.0.1:8011`.
- nginx: vhost `validate.smartcron.ai` (falta DNS) + acceso directo `http://IP:8090`.
  Basic auth en todo excepto `/health`.
- MySQL: base `aiva_validate`, usuario `aiva_validate` (password en `.env` del servidor).

## Claves necesarias (completar en `.env`)

1. `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` — proyecto de LiveKit Cloud
   (Project Settings → Keys).
2. `LIVEKIT_SIP_TRUNK_ID` — troncal SIP saliente de LiveKit (Anura: `make livekit-sip`, ver
   "Telefonia: Anura via Asterisk" abajo; Twilio: ver su runbook).
3. Nada mas: LLM/STT/TTS corren localmente (ver "Inferencia local (vLLM)" arriba), no
   hace falta ninguna API key de proveedor externo. `HF_TOKEN` es opcional, solo si
   algun modelo llegara a requerir aceptar licencia en HuggingFace.
4. Solo si se exponen los vLLM por ngrok (ver "Exponer los vLLM por ngrok" arriba):
   `VLLM_API_KEY` (clave real), `NGROK_AUTHTOKEN` y `NGROK_DOMAIN`.

### Telefonia: Anura via Asterisk

Troncal SIP argentina de [Anura](https://kb.anura.com.ar/es/) con un Asterisk en Docker
(servicio `asterisk`, perfil `pbx`) de puente: registra la troncal, pasa las entrantes a
LiveKit y las salientes del agente a Anura, traduciendo los formatos de numero. Runbook
completo (port forwarding del router, troubleshooting): `docs/TELEFONIA_ANURA.md`.

1. Completar el bloque "Telefonia" de `.env` (`ANURA_*`, `LIVEKIT_SIP_HOST`,
   `LIVEKIT_SIP_PASSWORD`).
2. Router: redirigir `5080/udp` y `10000-10199/udp` a este host y apagar el SIP ALG.
3. `make pbx` y `make pbx-status` -> el registro con Anura tiene que decir `Registered`.
4. `make livekit-sip` -> crea los trunks entrante/saliente y la dispatch rule en LiveKit;
   poner el `ST_...` que imprime en `LIVEKIT_SIP_TRUNK_ID` y `make up` (recrea el agente con el
   `.env` nuevo).

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
