# meta-review-management v1

Estado: borrador

- **Archivo:** `meta-review-management-v1.mp4` (1920 × 1080, 30 fps, H.264 CRF 18 + pista AAC en silencio), 80,0 s,
  13,1 MB.
- **Pedido (25-oct-2026):** video para el App Review de Meta que muestre el uso de `whatsapp_business_management`,
  con las capturas reales del panel, subtítulos en inglés, sin locución y sin música (o muy baja), cursor y cámara
  suave, placa de inicio y de cierre, 60–120 s. Textual en el [README](../../README.md).
- **Qué cambió:** primera versión.

## Decisiones

- **Sin música:** el pedido la permitía muy baja; para un revisor es más limpio el silencio. El MP4 lleva igual una
  pista de audio en silencio (`public/.../silencio.wav`, 1 s en loop) para que los reproductores y `make
  video-revisar` funcionen.
- **Operadores desenfocado** en m01 a m05 (las capturas de `public/` ya vienen desenfocadas, ver
  `capturas/preparar.py`); en m03, m04 y m05 también la parte que se veía detrás del velo del modal.
- **Entre el login y el modal de conexión** se muestra m01 (la página WhatsApp) para que el cursor llegue al botón
  "Conectar WhatsApp" que abre el modal. No es una pantalla nueva: es la misma captura de la escena 3.
- **"Crear" sin clic:** el cursor se posa en el botón pero no hace clic, porque no hay captura del resultado.
- **Placa de inicio:** logo de Atentina, "WhatsApp Business Management" y el permiso en mono, más "Screen recording
  of the Atentina dashboard · app.atentina.com.ar" (el texto pedido, partido en líneas; sin el guion largo).
- Componente propio (`src/Video.tsx`): cámara por keyframes en px de la captura, cursor que sigue a la cámara y
  subtítulos por toma. No usa `Montaje` (no hay voces).

## Locución

Ninguna. No se usó el TTS. El STT se usó solo en `make video-revisar` (10 tramos en silencio).

## Controles

- `npx tsc --noEmit` sin errores.
- Cuadros de prueba (`npx remotion still`, en `scratch/videos/meta-review-management/`): uno por toma en el momento
  más cargado. Se corrigió: el zoom a la tabla de números cortaba la columna Número (1,9× → 1,4×), el de Plantillas
  cortaba `hello_world` y el desenfoque derramaba el blanco del modal como un halo (ahora se desenfoca sin el modal).
- `make video-revisar P=meta-review-management V=1 ARGS="--tramos 0,4.6,10.8,15.4,21.4,31.6,45.2,54.4,66.4,75"`:
  80,0 s; volumen integrado −70 LUFS (silencio, esperado: no aplica la referencia de −16); transcripción vacía en
  los 10 tramos (no hay voz); hojas de cuadros cada 2 s en `scratch/videos/revision/meta-review-management-v1/`:
  subtítulos sin cortar y sin tapar los botones de cada paso, Operadores ilegible en todos los cuadros, el cursor
  llega a cada botón antes del corte.
- Afirmaciones revisadas contra el código (README, "Afirmaciones y fuentes").

## A revisar antes de mandarlo a Meta

- **Datos personales que siguen a la vista** (vienen en las capturas, no se tocaron): el nombre "Laureano Martín
  Arcanio" en la ventana de Meta (m06), "Laureano" y el email `larcanio@gmail.com` en el panel (arriba a la derecha
  y abajo del menú). Son del usuario; si no se quieren mostrar, se desenfocan igual que Operadores.
- **Los dos números dicen "Alta manual"** debajo de "Conectado", y la columna Calidad está en "–": el subtítulo 3
  dice que el número aparece conectado después del alta y que leemos su calidad y su límite. Es lo que hace el
  código (Embedded Signup), pero las capturas son de números dados de alta a mano, sin calidad cargada. Un revisor
  que traduzca la pantalla puede notarlo; si Meta lo objeta, rehacer m01 con un número conectado por Embedded Signup
  (cuando esté aprobado) o con la calidad leída de Meta ("Releer de Meta").
- **La creación de la plantilla no termina en pantalla** (no hay captura de `recordatorio_turno` "En revisión"). Si
  Meta pide ver el resultado, sumar una captura de la lista con la plantilla nueva pendiente.
- **El Embedded Signup se corta en la primera pantalla de Meta** ("¿Continuar como…?"): la elección de la cuenta de
  WhatsApp Business y del número que dice el subtítulo 2b no se ve, porque el Tech Provider todavía no está
  aprobado (META_APP_REVIEW.md, sección 3, paso 3 del guion).
- El video incluye la sección Administración del menú (vista de admin): no muestra datos de otros clientes más allá
  de los dos números de Atentina.
