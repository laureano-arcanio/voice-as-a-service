# api-desarrolladores v1

Estado: borrador

- **Archivo:** `api-desarrolladores-v1.mp4` (1920 × 1080, 30 fps, H.264 + AAC), 108,6 s, −17,3 LUFS.
- **Pedido (25-oct-2026, resumido fiel):** ver el [README](../../README.md): video técnico para desarrolladores,
  1-2 min (ideal ~90 s), intro, capacidades, auth, demo práctica con pedidos reales (LLM con el SDK de OpenAI, TTS
  que se escucha, agente, `POST /calls`, `GET /calls/{id}`, webhooks) y cierre con la documentación.
- **Qué cambió:** primera versión.

## Locución

Mejor de 4 tomas (`make video-voces P=api-desarrolladores TOMAS=4`), `velocidad` 1,05, `ganancia_db` −1,5.
Fidelidad: todas ≥ 0,95. a1 se regeneró dos veces (el STT oía "Open, LEI" y "la diferencia"); quedó "Y la ápi de
inferencia…" (1,00). a7 pasó de "una key" a "la key" (el STT oía "un aquí") y de "Consultás el agente" a "un agente"
("a la gente"). a10 pasó de "con firma" a "firmado" (el STT oía "Confirma"). a6 da 0,89 solo porque el STT escribe
"41" en cifras y oye "pasar la voz" por "pasarla a voz" (a confirmar de oído). a11, 0,95 por "atentina.com.ar".

Grafías nuevas: **`ese de ká` = SDK** (el STT oye "SDK" en a1 y a5; agregado a `GRAFIAS` de `scripts/voces.py`, a
confirmar de oído) y el plural **`ápis`** (el STT oye "APIs").

## Pedidos reales y adaptaciones

- **Key:** `video-api-desarrolladores`, del cliente `atentina`, creada con `make api-key CLIENT=atentina
  NAME=video-api-desarrolladores` (sale con `calls`) y con los alcances `llm` y `tts` sumados por SQL sobre esa fila
  (el CLI no recibe alcances y la API de keys pide sesión de usuario). **Revocarla** en el panel (ficha del cliente
  Atentina › API keys). El texto de la key no está en el video ni en estas notas; el archivo `.key` de scratch se borró.
- **Corridos:** LLM y TTS contra la URL pública con el código que se ve; `GET /voices`; `GET /agents/{id}` (Turnos);
  `POST /calls` sin `phone` (llamada de prueba `2465c035…`, cortada con `/hangup`: queda en las conversaciones de
  Atentina como prueba finalizada); `GET /calls/{id}` de la llamada real `42f6c59d…` (20-oct-2026).
- **Adaptado:** `POST /calls` con `phone` es el ejemplo de la documentación, no se corrió. El `GET /calls/{id}` es de
  otra conversación (entrante real, anonimizada), no de la de prueba, que no tiene datos. Webhook: no existe para
  llamadas sueltas, solo en campañas (`callback_url`); se muestra así y, para llamadas sueltas, `GET /events`.
- **Recortes:** ids truncados con "…", `join_url` recortado (trae un token de LiveKit), JSON sin los campos que no
  hacen al ejemplo. Nada inventado.

## Controles

- `npx tsc --noEmit` sin errores; cuadros de prueba de cada escena (`scratch/videos/api-desarrolladores/stills/`):
  se agrandó el acercamiento de las capturas y se separó el aviso de plan de la segunda ventana en `llamada`.
- `make video-revisar P=api-desarrolladores V=1 ARGS="--tramos 0,11,25,39.6,50,60.6,69.8,80.2,90.6,98.6"`:
  108,6 s, −17,3 LUFS (dentro de −16 ± 1,5), hojas en `scratch/videos/revision/api-desarrolladores-v1/`,
  transcripción por escena coincidente con el guion.

## A revisar antes de mostrarlo afuera

- **Duración:** 108,6 s, más que los ~90 s ideales (dentro de 1-2 min). Para acortar: sacar a4 o el `webhook`.
- **De oído:** "ese de ká" (SDK), "ápis", "key" y "streaming" con paula; el audio de la demo (voz `sofia`).
- **La doc pública dice que la referencia completa está "en el panel, en `/api/v1/docs`",** pero esa ruta es solo para
  admins (`API_DOCS=admin`, `_docs_access` en `app/main.py`; con una key de cliente da 403). No se usó en el video.
- **La llamada de prueba sin `phone`** está en la OpenAPI pero no en la página pública: si se quiere mostrar como
  función, sumarla a `api.astro`.
- **"Red" vs "Central":** la landing dice Red y la base, Central.
- Al cortar una llamada de prueba antes de que alguien entre, el worker loguea un `RuntimeError: room disconnected
  while waiting for participant` (la llamada termina bien, `finalizada`); ruido en el log, no del video.
