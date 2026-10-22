# Transcripción y voz para call centers

- **Pedido (21-oct-2026, Laureano, textual):** "Crea un nuevo video con el formato que ya tenemos, pero orientado a
  vender Transcripcion. Y sintetizacion. Sencillo de unos 40 segundos. Muestra un panel donde la persona suelta un
  .txt y se transcribe, mostrando quien habla mientas lo hace, animado. luego lo puede descargar. tambien comenta que
  se accede desde API, y que es posible conextar el sistema e integrarlo a sistemas existentes para transcribir en
  tiempo real, sentiment analysis y extraccion de datos. Es para una empresa de call center que necesitan
  transcripcion. Sencillo, sin mucho ruido visual, clean. professional"
- **Público:** una empresa de call center que necesita transcribir sus llamadas (responsables de operación y de
  sistemas). Sin nombre de prospecto.
- **Mensaje:** Atentina pasa cada llamada a texto (y el texto a voz), desde un panel o por API, con modelos propios
  en Argentina, y se integra a tus sistemas para tiempo real, sentimiento y extracción de datos.
- **Formato:** 1920 × 1080, 30 fps, ~42 s. Composición `transcripcion` (`src/Video.tsx`). Limpio: sin personajes
  (solo la mascota como nodo de Atentina), una idea por escena.
- **Decisión:** el pedido dice "suelta un .txt"; para transcribir tiene que ser audio, así que se suelta
  `llamada-0142.wav` y lo que se descarga es el `.txt`.

## Guion (v1)

| Escena | Tiempo | Locución | Qué se ve |
|---|---|---|---|
| `intro` | 0–7,6 s | t1 | Oscura: "Transcripción y voz para call centers", logo, "Cada llamada de tu call center, **en texto.**", onda → "Cliente · Hola, me llegó un cargo…", chips (Transcripción, Síntesis de voz, API, Servidores en Argentina) |
| `panel` | 7,0–18,6 | t2 | Ventana "Transcripciones": se arrastra `llamada-0142.wav` (estéreo, un canal por lado) a la zona; las ondas de los dos canales avanzan y los turnos aparecen escribiéndose con su rótulo Agente / Cliente; "Transcripción lista · 2 hablantes"; Descargar → TXT / JSON → "llamada-0142.txt descargado" |
| `api` | 18,6–27,8 | t3 | `call_center.py` con el SDK de OpenAI (`audio.transcriptions` y `audio.speech`), "Compatible con el SDK de OpenAI", respuestas `POST /audio/transcriptions` (texto) y `POST /audio/speech` (audio, voz `sofia`), "41 voces argentinas" |
| `integracion` | 27,8–36,8 | t4 | Tu central → Atentina → Tu CRM (voz y texto viajando); tarjetas: transcripción en vivo, sentimiento (Molesto → Conforme), extracción de datos (JSON); "Integración a medida, con nuestros motores de transcripción, lenguaje y voz" |
| `cierre` | 36,8–42,4 | t5 | Oscura: logo, "Cada llamada, **en texto y en datos.**", "Probalo con tus grabaciones", atentina.com.ar · 0800-220-1233 |

Locución en [`guion.json`](guion.json), solo narrador `lucas` (el de los otros videos).

## Afirmaciones y de dónde salen

- **Transcripción por API, compatible con OpenAI, wav/mp3/ogg, hasta 25 MB:** `docs/API_INFERENCIA.md` y
  `/plataforma/transcripcion` de la landing (`POST /audio/transcriptions`, `language=es`).
- **Síntesis, voz `sofia`, 41 voces argentinas:** `docs/API_INFERENCIA.md`, `tts/finetune/voces.tsv`.
- **"Modelos propios y servidores en Argentina":** landing (facts "Servidores en Argentina", inferencia propia).
- **"Aparece al instante":** la landing mide 4 s de audio en 0,13 s; un archivo de 3 min no se midió.
- **Código:** recortado de `docs/API_INFERENCIA.md` (SDK de OpenAI con `base_url`); `ATENTINA_URL` y `ATENTINA_KEY`
  son variables, sin claves.
- **Ilustrativo / no existe hoy como producto (a revisar antes de mostrarlo afuera):**
  - **La pantalla del panel** (soltar un archivo, transcripción por turnos, botón Descargar TXT / JSON): el panel
    (`web/`) no tiene una pantalla de transcripción de archivos; hoy es la API.
  - **Separación por hablante:** el STT no separa hablantes (Parakeet sin diarización; la API devuelve un solo
    `text`). En el video sale de una grabación estéreo con un canal por lado (lo usual en una central), transcribiendo
    cada canal: es integración a medida.
  - **JSON "por hablante":** la API devuelve `json`, `text` o `verbose_json` (sin segmentos ni hablantes).
  - **Transcripción en tiempo real, sentimiento y extracción de datos** de llamadas de terceros: se presentan como
    "integración a medida". Los agentes de Atentina ya transcriben en vivo y extraen datos de sus propias llamadas;
    el sentimiento no existe como función (se haría con el LLM, `POST /chat/completions`).
  - Conversación, número de cliente, duración, "En curso · 01:24" y el JSON extraído.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 21-oct-2026 | 42,4 s | Primera versión | borrador |
