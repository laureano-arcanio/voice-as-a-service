# API de inferencia: LLM, STT y TTS con una API key

Los tres motores propios (LLM, transcripción y síntesis de voz, sobre las GPUs de este server)
expuestos a los clientes por una API compatible con la de OpenAI. Cada cliente la usa con sus API
keys y está limitada por su tier. **Solo cuenta el uso por esta API:** los agentes integrados
(llamadas, WhatsApp) no la usan y siguen con los límites de minutos del tier.

- **URL base:** `https://app.atentina.com.ar/api/v1/inference` (la misma app y el mismo túnel que el dashboard).
- **Autenticación:** `Authorization: Bearer vaas_...` con una API key que tenga el alcance del motor.
  La cookie de sesión del dashboard no sirve.
- **Compatible con el SDK de OpenAI:** `OpenAI(base_url=<URL base>, api_key=<key>)`.
  `model` es obligatorio en los SDK pero **se ignora**: el modelo lo fija la plataforma (`GET /models`).
- Referencia exacta de pedidos y respuestas: OpenAPI en `/api/v1/docs` (solo admin), sección `inference`.

## 1. Crear una API key

Desde el dashboard: el cliente entra a **API > Nueva API key** (el admin, en la ficha del cliente,
pestaña **API keys**). Se elige el **acceso** de la key y se copia: se muestra una sola vez.

| Alcance | Sirve para |
|---|---|
| `llm` | `POST /chat/completions` |
| `stt` | `POST /audio/transcriptions` |
| `tts` | `POST /audio/speech` y `GET /voices` |
| `calls` | La API de llamadas, agentes y reportes (`/api/v1/calls`, `/agents`...). Es el de las keys anteriores |

- Una key puede tener varios alcances. **Las dos APIs no se cruzan:** una key `llm` no administra
  agentes ni llamadas (403 `scope_missing`), y una key `calls` no usa los motores.
- Conviene una key por sistema y con el mínimo alcance: se revoca sola (en el acto) si se filtra.
- Por API: `POST /api/v1/clients/{id}/api-keys` con `{"name": "CRM", "scopes": ["llm", "stt"]}` (sesión de usuario).

## 2. Endpoints

| Endpoint | Alcance | Qué hace |
|---|---|---|
| `POST /chat/completions` | `llm` | Chat con el LLM, con o sin `stream` |
| `POST /audio/transcriptions` | `stt` | Transcribe un archivo de audio |
| `POST /audio/speech` | `tts` | Sintetiza texto con una de las voces |
| `GET /voices` | `tts` | Voces disponibles (nombre, género, WER, caracteres por segundo) |
| `GET /models` | cualquiera | Los modelos que sirve la plataforma |
| `GET /usage` | cualquiera | Tu consumo del mes contra los límites del plan (`?month=YYYY-MM`). No gasta cupo |

### LLM: `POST /chat/completions`

```bash
curl $BASE/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Hola, ¿qué horarios tienen?"}],"max_tokens":200}'
```

- Acepta `messages`, `max_tokens` (o `max_completion_tokens`), `temperature`, `top_p`, `stop`, `seed`,
  `presence_penalty`, `frequency_penalty`, `response_format`, `tools`, `tool_choice` y `stream`.
  Lo demás se ignora. Solo `n=1`.
- **`max_tokens`:** sin él se usa `INFERENCE_LLM_MAX_TOKENS` (4096), y nunca más que eso. Además se achica
  a lo que le queda al cliente de tokens de salida del mes: el pedido no puede generar más que su saldo.
- **Stream:** `"stream": true` responde SSE (`data: {...}` y `data: [DONE]`) y agrega un último chunk
  con `usage` (la plataforma lo pide al motor para poder medir).
- La respuesta trae `usage` con `prompt_tokens` y `completion_tokens`, que es lo que se descuenta.
- El modo de pensamiento del modelo lo fija la plataforma (`LLM_THINKING`, hoy apagado).

### STT: `POST /audio/transcriptions`

```bash
curl $BASE/audio/transcriptions -H "Authorization: Bearer $KEY" -F file=@audio.wav -F language=es
```

- `multipart/form-data` con `file` (wav, mp3, flac, ogg...; mono o estéreo, cualquier frecuencia), y
  opcionales `language` y `response_format` (`json`, `text` o `verbose_json`, que trae `duration`).
- Respuesta `json`: `{"text": "...", "usage": {"type": "duration", "seconds": 12.5}}`. Lo que se descuenta
  son esos segundos de audio.
- Hasta `INFERENCE_STT_MAX_BYTES` por archivo (25 MB): 413 `payload_too_large`. Para audios largos, partirlos.

### TTS: `POST /audio/speech`

```bash
curl $BASE/audio/speech -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"voice":"sofia","input":"Hola, ¿en qué te puedo ayudar?"}' --output respuesta.wav
```

- `voice` es obligatoria y tiene que ser una de `GET /voices` (41 voces con nombres argentinos: `sofia`,
  `martin`...). Una voz que no existe da 422 `invalid_voice`: el motor no la acepta.
- `input` hasta `INFERENCE_TTS_MAX_CHARS` (1500) caracteres; para textos más largos, varios pedidos.
- `response_format`: `wav` (default, con encabezado) o `pcm` (crudo: 24 kHz, mono, 16 bits). Responde en
  streaming: el primer audio llega antes de que termine la síntesis. Lo que se descuenta son los segundos
  de audio generado.

### Con el SDK de OpenAI (Python)

```python
from openai import OpenAI

client = OpenAI(base_url="https://app.atentina.com.ar/api/v1/inference", api_key="vaas_...")

chat = client.chat.completions.create(model="atentina", messages=[{"role": "user", "content": "Hola"}])
text = client.audio.transcriptions.create(model="atentina", file=open("audio.wav", "rb"), language="es").text
client.audio.speech.create(model="atentina", voice="sofia", input="Hola", response_format="wav").write_to_file("r.wav")
```

## 3. Límites del plan

Los fija el **tier** del cliente (Tiers > Nuevo tier / Editar) y valen para **todas las keys del
cliente juntas**. Aplican de inmediato (un cambio de tier cuenta para el mes en curso).

| Límite del tier | Qué mide | Unidad |
|---|---|---|
| `api_llm_input_tokens` | Tokens del prompt (`prompt_tokens`) | por mes |
| `api_llm_output_tokens` | Tokens generados (`completion_tokens`) | por mes |
| `api_tts_minutes` | Audio sintetizado | minutos por mes |
| `api_stt_minutes` | Audio transcripto | minutos por mes |
| `api_rate_limit` | Pedidos a los tres motores, de todas las keys | pedidos por minuto |

- **Valores:** vacío (`null`) = ilimitado; `0` = el plan no incluye ese motor (403 `not_in_plan`).
  Un tier nuevo arranca **sin inferencia** (`0`) y con 60 pedidos por minuto: hay que dársela.
- **Mes calendario** en `BILLING_TIMEZONE` (Argentina): el cupo se renueva el día 1 a las 00:00.
- Las entradas y salidas del LLM, y TTS y STT, son cupos **separados**: agotar uno no afecta a los otros.

### Cómo se corta

1. **Antes de cada pedido** se verifica la key y su alcance, el cliente activo, el tope de pedidos por
   minuto y el cupo del motor. Si no pasa, el pedido **no llega al motor** ni gasta GPU.
2. **Después** se suma lo que el motor informó (tokens, segundos de audio). Un pedido que falla en el
   motor no se cobra.
3. Un pedido puede **pasarse del cupo por lo que consume el último que entró** (el prompt y el audio se
   miden al terminar), pero el siguiente ya no pasa. En el chat el desborde de salida no existe: el
   `max_tokens` se achica al saldo. Dos pedidos simultáneos con el cupo casi agotado pueden pasarse
   juntos, también sin más que el consumo de esos pedidos.
4. Un stream que el cliente corta se cobra igual: con el `usage` si el motor alcanzó a informarlo, y si
   no, estimado (tokens de salida = chunks con contenido; de entrada, un token cada 3 caracteres).

### Errores

Cuerpo `{"detail": "texto para mostrar", "code": "codigo_estable", "errors": []}`.

| HTTP | `code` | Cuándo |
|---|---|---|
| 401 | | Sin API key, inválida o revocada |
| 403 | `scope_missing` | La key no tiene el alcance de ese motor (o es de la otra API) |
| 403 | `not_in_plan` | El tier tiene `0` para ese motor (o `api_rate_limit` en 0) |
| 429 | `rate_limited` | Se pasó de `api_rate_limit` pedidos en el último minuto. Trae `Retry-After` (segundos). Los pedidos rechazados también cuentan |
| 429 | `api_llm_input_tokens`, `api_llm_output_tokens`, `api_tts_minutes`, `api_stt_minutes` | Cupo del mes agotado. Reintentar no sirve hasta el día 1 o hasta que se amplíe el plan |
| 429 | `client_inactive` | El cliente está desactivado |
| 400 | `upstream_rejected` | El motor rechazó el pedido (prompt más largo que el contexto, audio ilegible) |
| 400 | `payload_too_large` | Audio de más de `INFERENCE_STT_MAX_BYTES` |
| 422 | `invalid_request`, `invalid_voice` | Pedido mal armado, o voz inexistente |
| 502 | `upstream_error` | El motor no responde o está caído |

## 4. Consumo

- **Dashboard:** API > "Consumo de la API" (el admin, en la ficha del cliente > API keys): barras por
  cupo, pedidos del mes y desglose por key, con selector de mes.
- **API:** `GET /api/v1/inference/usage` (con una key de inferencia) o
  `GET /api/v1/clients/{id}/inference-usage?month=YYYY-MM` (sesión de usuario, o key `calls`).

```json
{"month": "2026-10", "rate_limit": 60,
 "llm_input_tokens": {"used": 21, "limit": 400, "remaining": 379},
 "tts_minutes": {"used": 0.07, "limit": 1, "remaining": 0.93}, "...": "...",
 "requests": {"llm": 2, "stt": 1, "tts": 1},
 "keys": [{"name": "CRM", "scopes": ["llm"], "requests": {"llm": 2, "stt": 0, "tts": 0}, "llm_input_tokens": 21}]}
```

- Se guarda por cliente, key y día (`api_usage_daily`), sin el contenido de los pedidos: **la plataforma no
  guarda prompts, audios ni textos de la API**.

## 5. Para quien opera

- Variables (`.env`, ver `.env.example`): `INFERENCE_LLM_MAX_TOKENS`, `INFERENCE_STT_MAX_BYTES`,
  `INFERENCE_TTS_MAX_CHARS`, `INFERENCE_TIMEOUT_SECONDS`.
- Los motores se llaman con la clave interna (`VLLM_API_KEY`), por las URL `VLLM_*_BASE_URL` de la app.
  El cliente nunca ve esa clave ni el proxy `:8100`.
- **La API comparte GPU con los agentes integrados.** El tope de pedidos por minuto protege de un cliente,
  pero no hay (todavía) un tope global ni medición de capacidad de esta API: antes de venderla en volumen,
  hay que medirla con el test de capacidad ([`capacity/`](capacity/README.md)).
- El tope de pedidos por minuto es **en memoria** y por proceso (como los de login): sirve mientras `app`
  corra un solo worker, que es lo que hay hoy.
- Los tiers que existían al migrar (0009) quedaron sin inferencia (`0`) y con 60 pedidos por minuto, salvo los
  que no tenían ningún límite de llamadas (Interno), que quedan ilimitados. Las API keys que existían son
  `calls`.
- Pruebas: `tests/test_inference.py` (motores simulados). Prueba real contra los motores vivos:
  backend de desarrollo con `VLLM_*_BASE_URL` en `127.0.0.1:8101-8103`, y una key con los tres alcances.
  Medido así el 9-oct-2026 (3090): primer chunk del stream del LLM a los 0,09 s; 4 s de audio
  sintetizados en 0,84 s; transcripción de esos 4 s en 0,13 s. Los cortes de tokens y minutos y el
  tope de pedidos por minuto responden 429 con el `code` de arriba.
