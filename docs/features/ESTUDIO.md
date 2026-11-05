# Estudio: texto a voz y transcripción

Dos pantallas para todos los planes: **Texto a voz** (`/texto-a-voz`) y **Transcribir** (`/transcribir`). Todo lo que se
genera queda guardado en el cliente y descuenta de los minutos de síntesis o de transcripción del plan, los mismos de la
[API de inferencia](../API_INFERENCIA.md). Las pruebas de voz son sin cargo, con tope.
Estado: en producción.

## Decisiones

| Tema | Decisión | Por qué |
|---|---|---|
| Qué cupo descuenta | Texto a voz, `api_tts_minutes`; Transcribir, `api_stt_minutes` (los de la API de inferencia). Con el cupo en 0, 403 `not_in_plan` | Es el mismo uso de los mismos motores que la API; los entrantes quedan solo para llamadas, y el Estudio no puede cortar ni rechazar una llamada |
| Pruebas de voz | Sin cargo: no descuentan minutos ni se guardan en el Estudio. Tope de texto: una frase, hasta `TTS_PREVIEW_MAX_CHARS` (250; entra la más larga fija, 160 del editor y 128 de la landing). Sin tope por hora en el panel, la API key y el MCP; la demo de la landing tiene `DEMO_IP_TTS_PER_HOUR` | Sirven para elegir una voz, no para generar audio. Quedan en Uso de la API como `voice_test_*` ([`API_INFERENCIA.md`](../API_INFERENCIA.md)) |
| Cómo se cuenta | Segundos reales de audio, sumados en el mes (`billed_seconds`) | Por minuto iniciado, 20 pruebas de voz de 5 s agotarían los 20 minutos de Free. Cambiar la regla es una línea (`studio.billable`) |
| Motores | Los mismos de las llamadas, por `tts._send` y el HTTP del STT | Sin servicios nuevos ni cambios de GPU |
| Trabajo en segundo plano | Fila en `studio_items` y `studio_loop` en la app | Un texto largo tarda minutos y el pedido HTTP no puede esperar por el túnel. Mismo patrón que `campaign_loop` |
| Protección de las llamadas | Un trabajo a la vez por motor, en pedazos cortos (`STUDIO_TTS_CHUNK_CHARS`, `STUDIO_STT_CHUNK_SECONDS`) | Los motores atienden llamadas en vivo: un pedazo pesa como un turno. Un audio entero en un solo pedido frenaría al STT |
| Dónde se guarda | Texto en la base; audio en `CALL_RECORDINGS_DIR/studio/<cliente>/<item>/` | Ya es un volumen de `app`, en el disco de datos, y entra en el backup de `storage/` |
| Formatos | Se guarda WAV (24 kHz, mono) y se convierte al bajar: `wav`, `mp3`, `ogg` (Opus), `flac` | PyAV ya está en la imagen. La conversión queda guardada al lado y no se vuelve a sintetizar |
| Subir texto | `.txt` leído en el navegador, a la misma caja | Sin parsers ni archivos del lado del servidor |
| Borrar | Borra audio y texto, y la fila queda con sus segundos | Borrar no devuelve minutos |
| Falla | `failed`, sin descontar nada | El cliente no paga un resultado que no recibió |
| Admin como el cliente | Ve y baja; no crea | No gasta minutos ajenos |

## Modelo de datos (migración 0047)

`studio_items`: `client_id`, `created_by`, `kind` (`tts`/`stt`), `origin` (`studio`/`voice_test`), `status`
(`queued`/`processing`/`done`/`failed`), `title`, `voice`, `language`, `text` (entrada del TTS o resultado del STT),
`progress`, `audio_seconds`, `billed_seconds`, `file_name`, `error`, `created_at`, `finished_at`, `deleted_at`.
Las filas con `origin='voice_test'` (pruebas de voz) se ven en el historial y no cuentan para ningún cupo; el código no
las crea.

## Flujo de minutos

1. **Reserva.** Con el lock de la fila del cliente (`studio._reserve`), `api_usage.check` mira el cupo del motor (403
   `not_in_plan` en 0, 429 si está agotado), se compara la estimación con lo que queda y se inserta el ítem con
   `billed_seconds` = estimación. Así dos trabajos a la vez no venden el mismo minuto.
   TTS: caracteres / `car_s` de la voz. STT: duración del archivo.
2. **Ajuste.** Al terminar, `billed_seconds` pasa a los segundos reales; si falla, a 0.
3. **Consumo.** `api_usage.studio_seconds` suma los `studio_items` con `origin='studio'` del mes (en `BILLING_TIMEZONE`,
   por `created_at`: un trabajo cuenta en el mes en que se reservó) a lo de la API: lo ven `check()` (el 429 de la API
   y del Estudio) y el uso de inferencia (`GET /inference/usage`, `GET /clients/{id}/inference-usage`), donde los
   medidores `tts_minutes`/`stt_minutes` suman las keys y el campo `studio`. No suma pedidos ni cuenta para el tope por
   minuto (`api_rate_limit`).

**Tolerancias aceptadas.** Contra un pedido de la API en el mismo instante, el Estudio puede pasarse por lo que consume
ese pedido (la API no toma lock y suma al terminar: "el último pedido puede pasarse"). La estimación del TTS puede quedar
corta y el ajuste al real pasarse unos segundos.

## API

| Ruta | Qué hace |
|---|---|
| `POST /studio/speech` | `{text, voice}`. 201 con el ítem en cola; 429 `api_tts_minutes` sin minutos o si no alcanzan ("Necesita unos N minutos y te quedan M"); 403 `not_in_plan` con el cupo en 0 |
| `POST /studio/transcriptions` | Multipart con `file`. 201 con el ítem; 422 `audio_invalid` si no se puede leer; 413 si es muy grande; 429 `api_stt_minutes` y 403 `not_in_plan` como el anterior |
| `GET /studio/items` | `kind`, `limit`, `offset`; del más nuevo al más viejo, sin el texto completo |
| `GET /studio/items/{id}` | El ítem con su texto |
| `GET /studio/items/{id}/audio` | `format` y `download`. El STT devuelve el archivo que se subió |
| `DELETE /studio/items/{id}` | Borra el contenido. 409 `studio_busy` mientras se procesa |

## Límites

| Variable | Valor | Motivo |
|---|---|---|
| `STUDIO_TTS_MAX_CHARS` | 20.000 | Unos 20 minutos de audio, el cupo de síntesis de Free |
| `STUDIO_STT_MAX_BYTES` | 95 MB | Por debajo del tope de subida de Cloudflare (100 MB según su plan, sin medir) |
| `STUDIO_STT_MAX_SECONDS` | 7.200 | Dos horas |
| `RATE_STUDIO_PER_HOUR` | 60 | Trabajos por usuario |

## Medido

Con los modelos de este host, en el entorno local, un trabajo a la vez y sin llamadas de carga (3-nov-2026):

| Prueba | Resultado |
|---|---|
| Texto a voz de 1.056 caracteres (reserva 62,8 s) | 55,8 s de audio en 15 s |
| Conversión de ese audio | MP3 447 KB en 0,55 s; OGG 223 KB en 0,49 s; FLAC 1,4 MB en 0,06 s; WAV 2,7 MB |
| Transcripción del mismo audio | 1 a 3 s |
| Palabras recuperadas, texto variado de 66 s | 99 % con pedazos de 15, 20, 30 y 60 s |

**Falla del modelo de STT, sin corregir** (regla de `AGENTS.md`): con la misma frase repetida seis veces, el STT se saltea frases
y, con pedazos de 15 s, devolvió 1.281 palabras de un audio de 216. Con texto variado no pasó. Queda para un eval del STT.

## Trampas

- El audio del Estudio crece: un minuto de WAV son 2,9 MB. El tope de Sucursal son unos 3,4 GB por mes y por cliente, sin
  vencimiento. Mirar el disco de datos de server2.
- Si la app se reinicia a mitad de un trabajo, vuelve a la cola y se rehace al arrancar (`processing` a `queued`).
- La carga del Estudio sobre los motores con llamadas en vivo no está medida. Antes de abrirlo a todos, correr el test de
  capacidad ([`docs/capacity/`](../capacity/README.md)) con un trabajo largo de cada motor.

- Un cliente sin agentes ve el asistente de primera vez y no el menú ([`PRIMERA_VEZ.md`](PRIMERA_VEZ.md)): llega al Estudio al
  terminarlo. Las voces que escucha en el asistente no descuentan minutos.

## Pendientes

- **Legales.** La política de privacidad no menciona audios y textos subidos ni su conservación. Hace falta una versión
  nueva ([`LEGAL.md`](LEGAL.md)).
