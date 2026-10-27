# Integrar la API de Atentina (desarrolladores)

- **Pedido (25-oct-2026, resumido fiel):** video técnico en español, 16:9 1080p, para YouTube y la documentación,
  que explique paso a paso cómo integrar la API de Atentina en una aplicación, con solicitudes y respuestas reales.
  1 a 2 min (ideal ~90 s). Público: desarrolladores. Profesional, claro, directo y dinámico: demo técnica real, no
  publicidad. Estructura: intro (~10 s), capacidades (10-15 s), auth y configuración (~15 s), demo práctica (40-50 s:
  SDK de OpenAI con el LLM, TTS con voz argentina que se escucha, consultar un agente, `POST /calls`,
  `GET /calls/{conversation_id}`, mención de webhooks) y cierre (~10 s) con el link a la documentación. Fuente única:
  `/desarrolladores/docs/api` (`landing/src/pages/desarrolladores/docs/`), `docs/API_INFERENCIA.md`, la OpenAPI y
  `app/api/`. Marcar lo que depende del plan; keys enmascaradas; no disparar llamadas telefónicas reales.
- **Público:** desarrolladores que integran Atentina en su sistema.
- **Mensaje:** con una API key y pocas líneas sumás agentes, telefonía y voz a tu aplicación.
- **Formato:** 1920 × 1080, 30 fps, 108,6 s. Composición `api-desarrolladores` (`src/Video.tsx`). Subtítulos
  quemados (abajo al centro, con la grafía normal).
- **Publicado (25-oct-2026):** https://www.youtube.com/watch?v=HmdiVFv5jXA, embebido al principio de `/desarrolladores/docs/api`.
- **Contexto:** pieza para YouTube y para `/desarrolladores/docs`. Complementa a [`yoizen`](../yoizen/README.md)
  (técnico para un integrador concreto).

## Guion (v1)

| Escena | Locución | Qué se ve |
|---|---|---|
| `intro` (11,6 s) | a1 paula: "Con las ápis de Atentina sumás agentes de inteligencia artificial, llamadas, campañas y voz a cualquier aplicación. Y la ápi de inferencia es compatible con el ese de ká de ópen, ei, ái." | Fondo oscuro: "API de Atentina · para desarrolladores", logo, "Agentes, llamadas y voz, en tu aplicación.", chips y `OpenAI(base_url="…/api/v1/inference")` |
| `capacidades` (14 s) | a2 paula: las dos APIs | Dos tarjetas: plataforma (`/api/v1`, key `calls`: agentes, llamadas, contactos, campañas, equipo y derivaciones, eventos y reportes) e inferencia (`/api/v1/inference`, `llm` `stt` `tts`: chat, transcripción, síntesis con 41 voces, streaming), con su aviso de plan |
| `auth` (14,6 s) | a3 paula (panel, alcances, se muestra una vez) + a4 gonzalo ("Cada pedido lleva la key en el encabezado de autorización, y listo.") | Capturas reales del panel: Nueva API key con Llamadas, LLM y Síntesis marcados → API key creada (enmascarada). Tabla de alcances y ventana con las dos URL base y `Authorization: Bearer vaas_••••` |
| `llm` (10,4 s) | a5 paula: SDK de OpenAI, solo cambia la dirección base y la key, el modelo lo fija la plataforma | `llm.py` (el que se corrió), con `base_url`/`api_key` y `model` resaltados; terminal con la salida real ("Sí, atendemos los sábados de 9 a 13 horas." y `65 17` de usage) |
| `tts` (10,6 s) | a6 paula + el audio real que devolvió el pedido (voz `sofia`, 3,04 s) | `curl …/audio/speech` con `voice` e `input`, `HTTP 200 · audio/wav · 3,04 s`; reproductor con la onda del WAV y el logo que habla; `GET /voices` (41) y `pcm` (53 ms, medido en el servidor) |
| `agente` (9,2 s) | a7 paula: la API de plataforma con la key de llamadas, consultar un agente | `GET /api/v1/agents/{id}` del agente Turnos (respuesta real recortada) con versión/voz y `fields` resaltados; tarjeta del agente con el logo y sus datos |
| `llamada` (10,4 s) | a8 paula: agente y teléfono; sin teléfono es de prueba; la respuesta trae el id | Cuerpo con `phone` (ejemplo de la documentación, aviso de plan) y sin `phone` (el que se corrió); respuesta real 201 con `conversation_id` resaltado |
| `resultado` (10,4 s) | a9 paula: estado, duración, cómo terminó y datos, listos para tu sistema | `GET /api/v1/calls/{conversation_id}` de una llamada entrante real, anonimizada; `tu_app.py` que arma `datos` y "Tu sistema · nuevo lead" (ilustrativo) |
| `webhook` (8 s) | a10 gonzalo: en las campañas el resultado llega por webhook, firmado | `POST /campaigns` con `callback_url`, el POST `contact.finished` con `X-Atentina-Signature` que viaja a tu sistema, `firma_valida` de la doc; aviso de plan; `GET /events` para llamadas sueltas |
| `cierre` (10 s) | a11 paula: una key y pocas líneas; la documentación | Fondo oscuro: TL;DR en tres pasos y `atentina.com.ar/desarrolladores/docs/api` (y la de MCP) |

Voces: `paula` narradora, `gonzalo` en a4 y a10 (VIDEOS.md). `velocidad` 1,05 y `ganancia_db` −1,5.

## Pedidos reales (25-oct-2026)

Con la key `video-api-desarrolladores` del cliente `atentina` (alcances `calls,llm,tts`; ver NOTAS). Salidas en
`scratch/videos/api-desarrolladores/` (no versionado).

| En pantalla | Pedido | Cómo |
|---|---|---|
| `llm.py` y su salida | `POST /inference/chat/completions` con el SDK de OpenAI 2.54 | Corrido tal cual contra `https://app.atentina.com.ar` (1,3 s de punta a punta desde el server) |
| `curl …/audio/speech` y el audio | `POST /inference/audio/speech`, voz `sofia` | Corrido contra la URL pública: 200, `audio/wav`, 3,04 s; el WAV es el que suena (bajado 4,5 dB para la mezcla) |
| `GET /voices` (41) | `GET /inference/voices` | Corrido (local) |
| `GET /agents/{id}` | Agente `turnos` de la demo de la landing | Corrido (pública y local); recortado |
| `POST /calls` sin `phone` y su 201 | Llamada de prueba del agente `turnos` (`mode: prueba`) | Corrida: no llama a nadie; se cortó a los 5 s con `POST /calls/{id}/hangup` (`finalizada`, `hangup_by_user`). `join_url` recortado (trae un token) |
| `POST /calls` con `phone` | — | Ejemplo de la documentación, **no corrido** (llamaría a un número real) |
| `GET /calls/{id}` | Llamada entrante real del 20-oct-2026 al agente Atentina Comercial | Corrido; nombre, empresa y teléfono **anonimizados** ("Martín", "Empresa Ejemplo", `351 ••• ••••`); recortado |
| Webhook y `firma_valida` | — | De la documentación (sección Webhook), no corrido: no se creó ninguna campaña |

## Afirmaciones y de dónde salen

- **Dos APIs, alcances, URL base, Bearer, `model` ignorado, 41 voces, 1.500 caracteres, streaming:** `api.astro`
  (`/desarrolladores/docs/api`) y `docs/API_INFERENCIA.md`; alcances de la UI en `web/src/features/clients/ApiKeysSection.tsx`.
- **53 ms del primer audio en `pcm`:** medición del 9-oct-2026 en el servidor (API_INFERENCIA.md); se aclara en pantalla.
- **28 mujeres y 13 hombres:** AGENTS.md / `tts/finetune/voces.tsv`.
- **Llamada de prueba sin `phone`:** `CallIn.phone` en `app/api/schemas.py` ("sin telefono es una llamada de prueba")
  y `start_call` en `app/api/routers/calls.py`. La página pública de la doc no lo menciona.
- **Planes:** tabla "Qué incluye cada plan" de `api.astro` (Free sin llamadas telefónicas; campañas de llamadas en
  Sucursal y Red) y tiers de la base (Free con API: 262.144 tokens y 20 min de TTS/STT por mes). En la base el plan
  "Red" se llamaba **Central** (borrado el 26-oct-2026; Red es a medida, sin tier): en pantalla va "Red", como en la landing.
- **Webhook:** solo en campañas (`callback_url`, `X-Atentina-Signature`, `contact.finished`); para llamadas sueltas,
  `GET /events` (`call.ended`). No hay webhook por llamada suelta.
- **Ilustrativo:** `crm.guardar` y la tarjeta "Tu sistema · nuevo lead"; el cliente "Mi Empresa" y la usuaria "Ana"
  de las capturas (backend aislado).

## Capturas

Del panel real (`web/`) contra un backend aislado (SQLite, :8114, sin LiveKit) con datos ficticios, a 1600 × 900
con DPR 1,2. Los scripts quedaron en `capturas/`:

1. `capturas/backend.sh` y, en `web/`, `VITE_API_PROXY=http://127.0.0.1:8114 npx vite --port 5176 --strictPort`.
2. `capturas/seed.py` (tier Sucursal como el de producción, cliente "Mi Empresa" y su usuaria).
3. `capturas/api_video.mjs`, copiado a `scratch/shots/` (tiene puppeteer): tapa la key y cambia el dominio de
   desarrollo por `app.atentina.com.ar` en el DOM antes de cada captura. Salen a
   `public/proyectos/api-desarrolladores/capturas/`.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 25-oct-2026 | 108,6 s | Primera versión | borrador |
