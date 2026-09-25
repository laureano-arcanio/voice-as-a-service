# AIVA Ventas (Browix) — Demo MVP

POC: un agente de IA (asesora comercial virtual de [Browix](https://browix.com), plataforma de
gestion de personal) **atiende las llamadas de personas interesadas**, responde sus consultas y
junta los datos del lead hasta ofrecer una demo con un asesor. Tambien puede llamar (saliente).
Contexto del negocio: `docs/Browix_Contexto_Agente.md`.

La conversacion no es un guion: un **workflow YAML** define los datos a obtener (objetivos), el
estado guarda lo que ya se sabe, y en cada turno el LLM extrae datos, elige el siguiente objetivo
y redacta la respuesta. La app valida los datos y decide cuando termina. Detalle en "Motor
conversacional" abajo; el diseño original esta en `docs/REFACTOR.md`.

## Stack

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy (MySQL; SQLite en los tests), sin frontend.
- **Voz:** LiveKit Agents (STT + LLM + TTS, los 3 servidos localmente sobre GPU propia, ver
  "Inferencia local" abajo) sobre una troncal SIP (Anura via un Asterisk propio, ver "Telefonia"
  abajo), en un worker propio (`app/livekit_agent.py`, contenedor `agent`). La app
  (`app/main.py`) despacha el agente a una room nueva (`app/livekit_dispatch.py`). El worker
  reemplaza el `llm_node` de LiveKit por el motor conversacional, que guarda el estado en la base.

## Inferencia local

No se usan proveedores externos de inferencia (OpenAI, ElevenLabs, Anthropic): LLM, STT
y TTS corren en 3 contenedores propios (`vllm-llm`, `stt-parakeet`, `vllm-tts` en
`docker-compose.yml`) contra la GPU del host, cada uno con API compatible con OpenAI. El
codigo le habla a los 3 con el mismo `openai` SDK (via los plugins `livekit.plugins.openai`),
apuntando `base_url` a cada contenedor en vez de a `api.openai.com`.

| Rol | Modelo | Variable | Endpoint | Por que |
| --- | --- | --- | --- | --- |
| LLM del motor conversacional | `RedHatAI/Qwen3.5-9B-quantized.w4a16` (Qwen3.5-9B en 4 bits) | `VLLM_LLM_MODEL` | `/v1/chat/completions` | Structured output (JSON schema), sin pensamiento por latencia (`LLM_THINKING`) y muestreo recomendado por Qwen. Reemplazó al 4B en EXP-009: 8 de 8 demos con datos contra 4 de 8, y p50 0,90 s por turno contra 1,00 s. |
| STT | `nvidia/parakeet-tdt-0.6b-v3` | `VLLM_STT_MODEL` | `/v1/audio/transcriptions` | Servidor propio (`stt/server.py`, transformers + batching dinamico): 1,6 GB y mejor que Qwen3-ASR y Whisper Turbo en audio telefonico (ver "Eval de STT"). Es REST por turno, sin transcript parcial mientras el cliente habla. |
| TTS | Qwen3-TTS 1.7B-Base con fine-tuning (41 voces en un checkpoint) | `VLLM_TTS_MODEL`, `VLLM_TTS_VOICE` | `/v1/audio/speech` (streaming) | Servido con vLLM-Omni. Las voces estan dentro del checkpoint (ver "Voces del TTS" abajo). |

**Requisitos de host:** 1+ GPU NVIDIA con el [NVIDIA Container
Toolkit](https://github.com/NVIDIA/nvidia-container-toolkit) instalado y configurado
(`nvidia-ctk runtime configure --runtime=docker` + reiniciar Docker) — sin esto los 3
contenedores de inferencia no arrancan (`docker compose up` falla al reservar el device). El
reparto de GPU/memoria entre los 3 esta documentado con detalle en los comentarios de
`docker-compose.yml` (fue bastante mas quisquilloso de lo esperado: los modelos de audio
reservan memoria fuera del budget normal de KV-cache, y vLLM sigue capturando CUDA graphs
nuevos con el trafico real, asi que el uso real de VRAM termina bien por encima de lo que
estima `--gpu-memory-utilization` en frio). Probado en vivo contra 2x RTX 3090 (24GB c/u):
LLM solo en la GPU 0, TTS + STT en la GPU 1 (EXP-013), con las GPUs a 280 W: ~32 llamadas
simultaneas con p95 de 3 s (ver `docs/capacity/` y `AGENTS.md`; mediciones anteriores en
`docs/archive/`).

### Voces del TTS

Las voces (espanol argentino, de OpenSLR 61) estan entrenadas dentro de un solo checkpoint:
Qwen3-TTS-12Hz-1.7B-Base con fine-tuning de 41 voces (tipo `custom_voice`, `multi41`, epoca 2):
28 mujeres y 13 hombres, cada una con un nombre argentino (`sofia`, `martin`, ...).

El catalogo es [`tts/finetune/voces.tsv`](tts/finetune/voces.tsv): nombre, id de OpenSLR, genero
y dos metricas medidas sobre el checkpoint servido, para elegir voz:

- `wer`: WER de 24 frases de dominio, en % (Qwen3-ASR sobre el audio generado). Entre 1,1 y 5,8.
- `car_s`: caracteres por segundo, la velocidad del habla. Entre 14,8 y 19,5.

`vllm-tts` sirve el checkpoint de `TTS_FT_CKPT` (default
`tts/finetune/work/runs/multi41/lr2e-6/checkpoint-epoch-2`, no versionado) con el nombre
`VLLM_TTS_MODEL` (`qwen3-tts-ft`). La voz se elige en cada pedido, sin audio de referencia ni
reinicio:

```bash
curl -H "Authorization: Bearer $VLLM_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"qwen3-tts-ft","voice":"martin","input":"Hola, buen dia.","response_format":"wav"}' \
  http://$PUBLIC_HOST:$PROXY_PORT/tts/v1/audio/speech -o hola.wav
```

- `GET /v1/audio/voices` lista las voces.
- Una voz inexistente da 400.
- **Nunca mandar un pedido sin `voice` ni con `voice="default"`:** mata el engine de `vllm-tts`
  y todo da 500 hasta reiniciarlo (ver Trampas 8 en `docs/TTS_FINETUNE.md`).

Que voz usa cada llamada, en orden:

1. La elegida en el dashboard al lanzar la llamada (`voice` en `POST /calls`). El selector filtra
   por genero, WER maximo y rango de car/s (`GET /api/voices?genero=&wer_max=&car_min=&car_max=`).
2. La del workflow: `agent.voice` en el YAML (hoy `sofia` en los 3).
3. `VLLM_TTS_VOICE` del `.env`, si el workflow no define voz o si `vllm-tts` no sirve la voz
   pedida (el agente lo loguea como error, en vez de dar 400 en cada frase).

Entrenar, evaluar, agregar voces y cambiar de checkpoint: `docs/TTS_FINETUNE.md`. Primer audio
por oracion en llamada: 0,04-0,08 s.

Antes se usaba una voz clonada (`sofia_ar`) sobre el checkpoint Base, subida por
`POST /v1/audio/voices`; el volumen `vllm_tts_speakers` que la guardaba ya no se monta.

**Limitacion conocida:** el modo streaming (necesario para no matar la latencia de la
llamada) no soporta ajuste de velocidad -- `VLLM_TTS_SPEED` != 1.0 tira 400. Ver comentario
en `app/config.py`.

### Eval de STT

Parakeet se eligio contra Qwen3-ASR-1.7B (el STT anterior) y Whisper Large v3 Turbo con las
mediciones de abajo. Esos dos servicios ya no estan en el compose: para volver a compararlos
hay que recuperarlos del historial de git (commit `9456dcc`) como override.

```bash
make stt-eval                        # WER + latencia de stt-parakeet (corpus del load test)
make stt-eval ARGS="--telephone"     # idem con el audio degradado a 8kHz mu-law (llamada real)
```

Parakeet expone `/metrics` con los nombres de vLLM, asi que `sampler.py`/`analyze.py` lo miden
igual que al resto.

Primera medicion (sep-2026, 9 audios del corpus del load test, requests de a uno, audio
limpio / telefonico):

| STT | WER | Latencia p50 |
| --- | --- | --- |
| Qwen3-ASR-1.7B | 5.6% / 7.4% | 71 / 83 ms |
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

**Corpus de datos dictados:** `scripts/stt_corpus/entities.py` (~11 min) arma
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

**El TTS del corpus fue CosyVoice3, no `vllm-tts`:** Qwen3-TTS tartamudea
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
  personal que hoy pide el workflow del agente (`app/workflows/sales_discovery.yml`), asi que es lo que mas conviene
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

**Reproducir estas tablas:** `make stt-corpus` arma el corpus de OpenSLR (no necesita GPU) y
`make stt-eval ARGS="--audio-dir scripts/stt_corpus/data/<openslr61|entities>/<variante> --runs 1"`
mide Parakeet sobre cada variante (los audios marcados con defecto de TTS se saltean solos; con
`--include-defects` se cuentan). Regenerar el corpus de datos dictados necesita un TTS que clone
voces (CosyVoice 3, `--tts-url`), que ya no esta en el compose.

Para decidir, grabar recortes de llamadas reales (`X.wav` +
`X.txt` con el transcript correcto) y correr `make stt-eval ARGS="--audio-dir scripts/<dir>"`.
Se probo tambien Moonshine Spanish y se descarto: solo corre en CPU (su runtime trae ONNX
Runtime sin CUDA y los modelos en espanol son int8 para CPU), dio 33.3% de WER y su licencia
es no comercial para empresas de mas de USD 1M/anio.

Se descartaron tambien (2026-09-23, mismo eval, en `tel8k`: WER de OpenSLR / email / direccion completa):
- `marianbasti/whisper-large-v3-turbo-latam` (Turbo con fine-tune en Common Voice sin acentos de
  Espana): 2.7% / 17% / 51%, contra 1.5% / 20% / 64% de Turbo base. Pierde voseo ("Queres" ->
  "Crees", "Conseguime" -> "Conseguidme"), y con ruido cae mas que la base.
- `Qwen/Qwen3-ASR-0.6B`: 3.7% / 23% / 48%, contra 2.0% / 30% / 58% del 1.7B, en la mitad de tiempo
  (63 contra 119 ms). Con ruido, 11.8% contra 6.8%. Parakeet, del mismo tamanio, es mejor en todo
  lo telefonico.

TTS descartados (2026-09-23): `Qwen/Qwen3-TTS-12Hz-0.6B-Base`, medido contra el 1.7B-Base con la GPU 0
para cada uno, voz `sofia_ar`. Primer audio 94 contra 103 ms, pero ~1% de los pedidos no emite fin
de audio y genera ~47 s hasta el limite de tokens (siempre en frases cortas como "Dale, ya lo
registre."). Esas fallas ocupan la GPU y bajan el throughput a menos de la mitad con 8-16 pedidos en
paralelo. El 1.7B no tuvo ninguna en ~370 pedidos. CosyVoice 3 tambien se descarto como TTS de
llamadas: 0,6-1 s de primer audio con una llamada y 1-1,8 s con 4 (Qwen3-TTS: 0,11-0,2 s con 20).

## Correr con Docker Compose

```bash
make setup   # crea .env desde .env.example; completar credenciales (ver "Claves necesarias")
make up      # todo: agente + inferencia + proxy + asterisk
```

| Target | Servicios |
| --- | --- |
| `make up` | todos |
| `make up-agent` | `db` + `app` (`:8011`) + `agent` (worker de LiveKit), sin la inferencia |
| `make up-inference` | `vllm-llm` + `stt-parakeet` + `vllm-tts` (espera a que esten healthy) |
| `make up-nginx` | `proxy` (entrada publica a la inferencia) |
| `make up-pbx` | `asterisk` (lo recrea para releer `.env` y `asterisk/conf/`) |

`app` y `agent` esperan a que la inferencia este healthy antes de arrancar — la primera vez
tarda varios minutos (descarga de pesos + carga en GPU). `make logs S=<servicio>`,
`make restart S=<servicio>`, `make health` y `make help` para el resto.

### Inferencia por la IP fija

Para consumir LLM/STT/TTS desde afuera del host. El proxy nginx (`proxy/nginx.conf`) escucha
en `0.0.0.0:$PROXY_PORT` (8100) y rutea por path a cada servicio, sacando el prefijo para que
llegue `/v1/...`. Lo levanta `make up` (o solo el, `make up-nginx`).

1. Completar en `.env`:
   - `VLLM_API_KEY` con una clave real y larga (`openssl rand -hex 24`): los 3
     servidores vLLM la exigen como `Authorization: Bearer` en `/v1/*` (el proxy no
     agrega auth propia, esta es la unica).
   - `PUBLIC_HOST`: la IP fija del host (hoy `181.104.113.28`), sin esquema ni puerto.
   - `PROXY_PORT`: 8100 por defecto.
2. En el router: redirigir `PROXY_PORT` (TCP) a este host (`192.168.1.99`).
3. `make up-nginx` imprime las URLs. No depende de la inferencia: el servicio que este
   apagado da 502 en su path.

   | Servicio | Base URL OpenAI-compatible |
   | -------- | -------------------------- |
   | LLM      | `http://$PUBLIC_HOST:$PROXY_PORT/llm/v1` |
   | STT      | `http://$PUBLIC_HOST:$PROXY_PORT/stt/v1` |
   | TTS      | `http://$PUBLIC_HOST:$PROXY_PORT/tts/v1` |

   ```bash
   curl http://$PUBLIC_HOST:$PROXY_PORT/llm/v1/models -H "Authorization: Bearer $VLLM_API_KEY"
   ```

Es HTTP plano: la clave y el audio viajan sin cifrar. Logs: `make logs S=proxy`. Para
apagarlo: `docker compose stop proxy`.

### Inferencia remota: app/agent en otra PC

El host GPU corre la inferencia y el proxy (`make up-inference up-nginx`); una PC sin GPU puede correr
el resto del stack (`db` + `app` + `agent`) apuntando los vLLM a las URLs del
proxy. No hace falta tocar codigo: los plugins de LiveKit ya usan
`base_url`/`api_key` de `.env`.

1. Mismo `make setup` en la otra PC. En su `.env`:
   - `LIVEKIT_*`: los mismos del host GPU (mismo proyecto/agente).
   - `VLLM_LLM_BASE_URL=http://$PUBLIC_HOST:$PROXY_PORT/llm/v1`
   - `VLLM_STT_BASE_URL=http://$PUBLIC_HOST:$PROXY_PORT/stt/v1`
   - `VLLM_TTS_BASE_URL=http://$PUBLIC_HOST:$PROXY_PORT/tts/v1`
   - `VLLM_API_KEY`: la misma clave real configurada en el host GPU.
   - `VLLM_LLM_MODEL` / `VLLM_STT_MODEL` / `VLLM_TTS_MODEL` / `VLLM_TTS_VOICE`:
     iguales a lo que sirve el host GPU (la voz vive en el checkpoint del host GPU;
     la PC remota solo la referencia).
   - `MYSQL_*`: propios de esa PC (su `db` local).
2. `make up-agent` -> levanta `db`, espera a que este healthy, y recien ahi
   `app` + `agent` con `--no-deps` (no intenta arrancar la inferencia, que en esa
   PC no existe). No correr `make up` en la PC remota.

Ojo con la latencia: cada turno de la llamada cruza internet (ida y vuelta) hasta
el host GPU.

## Claves necesarias (completar en `.env`)

1. `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` — proyecto de LiveKit Cloud
   (Project Settings → Keys).
2. `LIVEKIT_SIP_TRUNK_ID` — troncal SIP saliente de LiveKit (Anura: `make livekit-sip`, ver
   "Telefonia: Anura via Asterisk" abajo).
3. Nada mas: LLM/STT/TTS corren localmente (ver "Inferencia local (vLLM)" arriba), no
   hace falta ninguna API key de proveedor externo. `HF_TOKEN` es opcional, solo si
   algun modelo llegara a requerir aceptar licencia en HuggingFace.
4. Solo si se exponen los vLLM por la IP fija (ver "Exponer los vLLM por la IP fija"
   arriba): `VLLM_API_KEY` (clave real) y `PUBLIC_HOST`.

### Telefonia: Anura via Asterisk

Troncal SIP argentina de [Anura](https://kb.anura.com.ar/es/) con un Asterisk en Docker
(servicio `asterisk`) de puente: registra la troncal, pasa las entrantes a
LiveKit y las salientes del agente a Anura, traduciendo los formatos de numero. Runbook
completo (port forwarding del router, troubleshooting): `docs/TELEFONIA_ANURA.md`.

1. Completar el bloque "Telefonia" de `.env` (`ANURA_*`, `LIVEKIT_SIP_HOST`,
   `LIVEKIT_SIP_PASSWORD`).
2. Router: redirigir `5080/udp` y `10000-10199/udp` a este host y apagar el SIP ALG.
3. `make up-pbx` y `make pbx-status` -> el registro con Anura tiene que decir `Registered`.
4. `make livekit-sip` -> crea los trunks entrante/saliente y la dispatch rule en LiveKit;
   poner el `ST_...` que imprime en `LIVEKIT_SIP_TRUNK_ID` y `make up-agent` (recrea el agente
   con el `.env` nuevo).

Despues de editar `.env`: `docker compose up -d`.

## Motor conversacional

```text
app/
  main.py                    API: /conversations, /conversations/{id}/turn, /calls; dashboard y /api/*
  livekit_agent.py           worker de voz: STT -> motor -> TTS
  calls.py                   CallLog: tabla `call_logs` (telefono, estado, duracion, latencia)
  latency.py                 latencia por turno: EOU + LLM + TTS
  workflows/sales_discovery.yml
  conversation/
    models.py                Workflow, ConversationState, AgentTurn (Pydantic)
    workflow.py              carga del YAML, validacion, required_if, is_workflow_complete
    engine.py                ConversationEngine: start_conversation, process_turn
    store.py                 ConversationStore: tabla `conversations` (get, save)
  llm/
    client.py                LLMClient: chat completions con JSON schema del workflow
    prompt.py                system prompt unico + WORKFLOW / CURRENT STATE / NEW USER MESSAGE
tests/                       motor con LLM falso + escenarios contra el LLM real
```

**Un turno:** llega el mensaje (por la API o transcripto por el STT en una llamada) →
`ConversationEngine.process_turn` espera la extracción del turno anterior (hasta 1,5 s) → el LLM de
conversación recibe workflow, conversación completa, estado (datos conocidos, objetivos pendientes,
lo último que preguntó) y el mensaje nuevo, y devuelve `assistant_message`, `answered` (si el cliente
respondió lo que le preguntó), `next_objective` y `status` → la app guarda la respuesta y lanza la
**extracción** en segundo plano. Si terminó, la respuesta es el mensaje de cierre del workflow y el
worker corta la llamada al terminar de decirlo.

**Extracción:** otra llamada al LLM, con prompt y esquema armados desde los `fields` del workflow
(tipo, opciones, descripción, pregunta) y la conversación completa. Corre mientras suena la
respuesta y el cliente contesta, así que no suma latencia (p50 ~0,9 s; el turno de conversación
bajó de 1,1 a 0,9 s al no generar los datos). Si `answered` es true y el dato no salió, reintenta
solo ese campo; si tampoco sale, lo marca respondido sin dato (`answered_without_data`) y no se
vuelve a preguntar. Al completar, el resultado se calcula con los datos extraídos; si el resultado
sería el objetivo (`goal`) pero faltan datos obligatorios, es `incompleta`.

**Motor clásico (`engine: classic`):** la alternativa sin estado por turno. El prompt de sistema se
arma del YAML (agente, objetivo, reglas, datos a obtener con su pregunta y condición, base de
conocimiento y mensajes de cierre); la conversación va como mensajes multiturno y el LLM responde
texto, que va directo al TTS. Al despedirse agrega `[FIN]` (no se dice) y ahí se hace la única
extracción, con el mismo extractor; si el cliente corta antes, se extrae al cortar
(`ConversationEngine.finish`). No hay `next_objective`, así que no se estira el endpointing al
dictar un email. `berlin_signup_classic.yml` es `berlin_signup` con `extends` y `engine: classic`;
el dashboard elige el agente por llamada. Con las 3 llamadas reales x5 (sep-2026): datos bien 88
contra 87 de 95 del estructurado, inventados 1 contra 6 (la extracción por turno inventaba la
actividad en 704b5d42), resultado correcto 13 contra 12 de 15; turno de conversación p50 0,58
contra 0,99 s y la mitad de llamadas al LLM (una sola extracción).

**Qué decide cada uno:** el LLM decide la respuesta, el objetivo siguiente y cuándo termina la
conversación; lo que dice se pasa al TTS tal cual. La app solo valida los datos que extrae
(campos inexistentes o con tipo inválido no se guardan, y se le informan en el turno siguiente
como `rejected_values`), normaliza el email dictado ("juan punto perez arroba gmail punto com" →
`juan.perez@gmail.com`, y solo si el cliente lo dijo) y guarda el estado. Al terminar clasifica la
llamada con `completion.outcomes` para el dashboard. En el agente de voz: si el cliente sigue
hablando y la respuesta no llegó a sonar o sonó menos de ~1 s (`CONTINUATION_WINDOW`), es la misma
frase: se deshace el turno (`retract_last_turn`, que cancela su extracción) y el siguiente recibe todo junto. Los turnos se
procesan de a uno, porque LiveKit genera la respuesta antes de confirmar el fin de turno
(preemptive generation). El endpointing espera 0,4 s si el turn detector cree que la frase terminó
y hasta 1 s si duda; mientras el LLM pide un dato dictado (email o teléfono), hasta 2,5 s.

**Medir:** `make eval-motor [N=3] [S=escenario]` corre `scripts/replay_calls.py`: escenarios
armados con llamadas reales (preguntas en medio del flujo, "sí, pero…", email cortado, rechazo,
buzón de voz) con un cliente que contesta lo que le preguntan. Imprime cada conversación, el
resultado y señales de loop (respuestas repetidas, mismo objetivo seguido).
`make eval-llamadas [N=5] [W=berlin_signup_classic]` (`scripts/replay_transcripts.py`) repite llamadas reales de
`berlin_signup` con lo que dijo el cliente tal cual, y compara datos finales y resultado con lo
esperado. Con N=5 (sep-2026), antes y después de separar la extracción: datos bien 85 → 91 de 95,
inventados o equivocados 6 → 2, resultado correcto 10 → 15 de 15.

**Workflows:** `demo_booking` presenta Browix en ~15 s si el interesado
acepta, pregunta a qué se dedica la empresa, conecta su necesidad con una función de Browix y
busca agendar una demo (todo como guía en el YAML; el LLM decide el orden) (nombre + mail o teléfono); si duda, ofrece llamarlo otro día.
`sales_discovery` es el anterior, de calificación con 11 datos (lo usan los tests del motor).
`demo_booking_classic` es el mismo con `engine: classic` y es el default (`WORKFLOW_ID`): en el loadtest
(EXP-013) baja la espera del cliente ~0,5 s con 32 llamadas y ~0,8 s con 48, con la mitad de pedidos al LLM.

**Nuevo workflow:** copiar uno de `app/workflows/` como `<id>.yml` (mismo `id` adentro) y usarlo
con `{"workflow_id": "<id>"}` o `WORKFLOW_ID=<id>`. `engine: structured` (default) o `classic` elige el
motor; `extends: <id>` hereda otro workflow y pisa las claves de primer nivel que define. Por campo:
- `type`: `string`, `integer`, `boolean`, `email`, `email_or_phone` o `choice` (con `options`).
  En YAML, los valores como `no` o `si` van entre comillas (`no` sin comillas es false).
- `required` o `required_if` (solo igualdades); los no obligatorios se guardan si el usuario los dice.
- `question` es una pregunta sugerida; las reglas y la base de conocimiento guían al LLM.

`completion.outcomes` clasifica la llamada al terminar (gana el primero cuyo `when` se cumple;
`goal: true` marca el objetivo, que cuenta el dashboard). Su `message` es un cierre sugerido al LLM.

**Probar por texto** (sin voz):

```bash
curl -s -X POST localhost:8011/conversations -H 'Content-Type: application/json' -d '{}'
curl -s -X POST localhost:8011/conversations/<id>/turn -H 'Content-Type: application/json' \
  -d '{"message": "Soy Juan de Acme, hacemos logística y somos unas 80 personas."}'
curl -s localhost:8011/conversations/<id>     # estado y transcript
```

**Probar por voz:** `POST /calls` con `{}` devuelve un `join_url` de LiveKit Meet (modo prueba);
con `{"phone": "+549..."}` marca por la troncal saliente. Las entrantes crean su conversacion solas.

**Dashboard** (`http://<host>:8011/`):
- `/`: lanza llamadas (telefono o modo prueba), metricas (workflow completo, piden demo, fallidas,
  minutos, latencia por turno), grafico por dia, tarjeta "En vivo" y la tabla de conversaciones.
- `/calls/<id>`: el estado del workflow (datos obtenidos y pendientes) al lado de la conversacion,
  actualizados cada 1 s mientras la llamada sigue; al final, la latencia por turno. Cada respuesta
  del agente despliega la salida exacta del LLM en ese turno, con su entrada y duracion; "Salida
  del LLM" las abre todas.
- `/workflow`: el YAML vigente, de solo lectura.

Cada conversacion vive en `conversations` (datos y mensajes, los escribe el motor en cada turno);
`call_logs` agrega lo telefonico. Las conversaciones creadas por `/conversations` (texto) aparecen
como origen "API". El mensaje del cliente se ve cuando el motor responde (se guardan juntos).

**Tests:** `make test` (los escenarios contra el LLM se saltean si `vllm-llm` no responde).

Medido (2026-09-23, Qwen3.5-4B sin carga): los 5 escenarios de extraccion pasan 25/25; una
conversacion completa de 7 turnos tarda 1,1-1,7 s por turno de LLM. La respuesta no se streamea
(sale entera del JSON), asi que esa latencia se suma entera antes del TTS.
