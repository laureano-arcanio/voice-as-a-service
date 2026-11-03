# Estudio: texto a voz y transcripción

Dos pantallas para todos los planes: **Texto a voz** (`/texto-a-voz`) y **Transcribir** (`/transcribir`). Todo lo que se
genera queda guardado en el cliente y descuenta minutos del plan, igual que las pruebas de voz.
Estado: implementado en `development`, sin desplegar.

## Decisiones

| Tema | Decisión | Por qué |
|---|---|---|
| Qué cupo descuenta | `inbound_minutes` (el mismo de las entrantes) | Es el único que tienen todos los planes: Free tiene 20 entrantes y 0 salientes. `api_tts_minutes` y `api_stt_minutes` siguen siendo solo de la API de inferencia |
| Cómo se cuenta | Segundos reales de audio, sumados en el mes (`billed_seconds`) | Por minuto iniciado, 20 pruebas de voz de 5 s agotarían los 20 minutos de Free. Cambiar la regla es una línea (`studio.billable`) |
| Motores | Los mismos de las llamadas, por `tts._send` y el HTTP del STT | Sin servicios nuevos ni cambios de GPU |
| Trabajo en segundo plano | Fila en `studio_items` y `studio_loop` en la app | Un texto largo tarda minutos y el pedido HTTP no puede esperar por el túnel. Mismo patrón que `campaign_loop` |
| Protección de las llamadas | Un trabajo a la vez por motor, en pedazos cortos (`STUDIO_TTS_CHUNK_CHARS`, `STUDIO_STT_CHUNK_SECONDS`) | Los motores atienden llamadas en vivo: un pedazo pesa como un turno. Un audio entero en un solo pedido frenaría al STT |
| Dónde se guarda | Texto en la base; audio en `CALL_RECORDINGS_DIR/studio/<cliente>/<item>/` | Ya es un volumen de `app`, en el disco de datos, y entra en el backup de `storage/` |
| Formatos | Se guarda WAV (24 kHz, mono) y se convierte al bajar: `wav`, `mp3`, `ogg` (Opus), `flac` | PyAV ya está en la imagen. La conversión queda guardada al lado y no se vuelve a sintetizar |
| Subir texto | `.txt` leído en el navegador, a la misma caja | Sin parsers ni archivos del lado del servidor |
| Borrar | Borra audio y texto, y la fila queda con sus segundos | Borrar no devuelve minutos |
| Falla | `failed`, sin descontar nada | El cliente no paga un resultado que no recibió |
| Admin como el cliente | Ve y baja; no crea. Sus pruebas de voz no descuentan ni se guardan | No gasta minutos ajenos |

## Modelo de datos (migración 0047)

`studio_items`: `client_id`, `created_by`, `kind` (`tts`/`stt`), `origin` (`studio`/`voice_test`), `status`
(`queued`/`processing`/`done`/`failed`), `title`, `voice`, `language`, `text` (entrada del TTS o resultado del STT),
`progress`, `audio_seconds`, `billed_seconds`, `file_name`, `error`, `created_at`, `finished_at`, `deleted_at`.

## Flujo de minutos

1. **Reserva.** Con el lock de la fila del cliente (el de `quota.admit`), se compara la estimación con lo que queda
   y se inserta el ítem con `billed_seconds` = estimación. Así dos trabajos a la vez no venden el mismo minuto.
   TTS: caracteres / `car_s` de la voz. STT: duración del archivo.
2. **Ajuste.** Al terminar, `billed_seconds` pasa a los segundos reales; si falla, a 0.
3. **Consumo.** `quota.used_seconds` suma `studio_items` a los minutos entrantes: lo ven el corte de llamadas, los medidores
   y el panel, sin otro cambio. Una llamada en curso también se corta si el Estudio agota el cupo.

La prueba de voz (`POST /tts/preview`, panel, API key y MCP) rechaza con 429 `inbound_minutes` si no quedan minutos, descuenta
lo entregado (también si el navegador corta) y queda en el historial de Texto a voz. La demo de la landing no descuenta:
no tiene cliente y va por `/api/v1/demo`.

## API

| Ruta | Qué hace |
|---|---|
| `POST /studio/speech` | `{text, voice}`. 201 con el ítem en cola; 429 `inbound_minutes` sin minutos |
| `POST /studio/transcriptions` | Multipart con `file`. 201 con el ítem; 422 `audio_invalid` si no se puede leer; 413 si es muy grande |
| `GET /studio/items` | `kind`, `limit`, `offset`; del más nuevo al más viejo, sin el texto completo |
| `GET /studio/items/{id}` | El ítem con su texto |
| `GET /studio/items/{id}/audio` | `format` y `download`. El STT devuelve el archivo que se subió |
| `DELETE /studio/items/{id}` | Borra el contenido. 409 `studio_busy` mientras se procesa |

## Límites

| Variable | Valor | Motivo |
|---|---|---|
| `STUDIO_TTS_MAX_CHARS` | 20.000 | Unos 20 minutos de audio, el cupo de Free |
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
  terminarlo. Las voces que escucha en el asistente ya descuentan de sus minutos.

## Pendientes antes de producción

- **Legales.** Las condiciones vigentes (2026-10-28) cuentan los minutos por llamada, y la política de privacidad no
  menciona audios y textos subidos ni su conservación. Hace falta una versión nueva ([`LEGAL.md`](LEGAL.md)).
- **Precios en la landing.** Dice "minutos entrantes": aclarar que incluyen el Estudio.
