# llamadas-salientes v1

Estado: borrador

- **Archivo:** `llamadas-salientes-v1.mp4` (1920 × 1080, 30 fps, H.264 + AAC), 89,2 s, −16,7 LUFS, 15 MB.
- **Pedido (28-oct-2026, textual):** "un nuevo video explicando cómo hacer desde el panel para configurar un número de
  llamada saliente para el cliente y cómo utilizar la app de teléfono para hacer llamadas. Incluye la creación de
  contactos y equipo. El objetivo del video es que un usuario pueda entender cómo iniciar y configurar para hacer
  llamadas salientes utilizando los contactos y la aplicación de teléfono. que sea corto y sencillo de entender.
  horizontal con dos voces para publicar en youtube y link a la documentación".
- **Qué cambió:** primera versión.
- **Texto para YouTube:** [`../../youtube.md`](../../youtube.md) (título, descripción con el link y capítulos).

## Locución

Mejor de 3 tomas (`make video-voces P=llamadas-salientes TOMAS=3`), `velocidad` 1,05, `ganancia_db` −1,5. Voces:
`paula` (narradora) y `gonzalo` (l6, grabación; l10, requisitos). Ortografía normal, sin grafías forzadas.
Fidelidad de las tomas elegidas: 0,99 a 1,00 en las 11 líneas.

| Línea | Voz | s | Fidelidad |
|---|---|---|---|
| l1 | paula | 9,15 | 1,00 |
| l2 | paula | 8,23 | 0,99 |
| l3 | paula | 12,01 | 1,00 |
| l4 | paula | 9,45 | 1,00 |
| l5 | paula | 10,43 | 1,00 |
| l6 | gonzalo | 4,49 | 1,00 |
| l7 | paula | 10,60 | 1,00 |
| l8 | paula | 4,35 | 1,00 |
| l9 | paula | 3,70 | 1,00 |
| l10 | gonzalo | 3,95 | 0,99 |
| l11 | paula | 2,19 | 1,00 |

## Controles

- `npx tsc --noEmit` sin errores; cuadros de prueba de cada escena (`scratch/videos/llamadas-salientes/`): se
  ajustó el encuadre de las capturas para que los recuadros no queden cortados y los tiempos de los recuadros a lo que
  dice cada frase (por largo de texto).
- `make video-revisar P=llamadas-salientes V=1 ARGS="--tramos 0,10.4,20.8,33.8,44.2,60.4,76.8"`: 89,2 s, −16,7 LUFS
  (dentro de −16 ± 1,5), hojas en `scratch/videos/revision/llamadas-salientes-v1/`. La transcripción por escena
  coincide con el guion, con las salvedades de abajo (son del STT sobre la mezcla con música).

## A revisar antes de mostrarlo afuera

- **Nada de esta función se probó con llamadas reales todavía** (`docs/LLAMADAS_DIRECTAS_PLAN.md`, secciones 15 y 16:
  paso 6 de "Cómo desplegar", celular con la pantalla bloqueada, eco, Anura). El video muestra el flujo y las pantallas;
  las dos pantallas de llamada de la app (Sonando y En curso, "0:43") son el componente real con un estado fijo, no una
  llamada. Conviene hacer una llamada real con un número propio antes de publicarlo.
- **La página enlazada se contradice con el video:** `https://atentina.com.ar/plataforma/telefono-del-equipo` dice
  "No hay una app de celular" (cuerpo, "Qué esperar" y la primera pregunta frecuente; `landing/src/data/site.ts`),
  y el video muestra la aplicación Teléfono (`telefono.atentina.com.ar`, desplegada el 28-oct-2026). Hay que
  actualizar la landing antes de publicar el video, o cambiar el link. **Corregido el 28-oct-2026** en
  `site.ts` (cuerpo y pregunta frecuente); falta publicarlo (la landing sale por push a `main`).
- **Condiciones `2026-10-28`:** revisadas por el abogado (28-oct-2026); falta el aviso por mail con 30 días (plan,
  sección 14). El video dice que hay que haberlas aceptado: un cliente que no recibió el aviso puede no saber de qué se
  trata.
- **"El administrador lo asigna":** el cliente no se asigna números solo; los asigna el administrador de la
  plataforma (Atentina). Se dijo así a propósito; si el video es para clientes finales, a lo mejor conviene decir
  "Atentina lo asigna a tu cuenta".
- **El equipo no hace falta para salir:** para llamar alcanza con el plan, las condiciones aceptadas, minutos
  salientes y un número asignado. El video presenta el equipo como paso 2 (lo pidió el pedido) y lo liga a las
  entrantes ("para que también reciban las llamadas entrantes").
- **Planes:** se dice "Mostrador, Sucursal o Red" como la landing; Red es a medida (sin tier propio en la base).
- **De oído:** en l3 el STT oye "usuario de lo panel" (por "del panel") en la toma elegida y en la mezcla; "Tené",
  "podés", "tocás" y "Teléfono" (acento); y "haber aceptado" en l10 (el STT sobre la mezcla oyó "habrá aceptado").
- **Datos ilustrativos:** cliente "Mi Empresa", "Ana Ríos", "Pedro Gómez", los contactos y los teléfonos (`+54 9 351
  555-…`, `+54 11 5263 0862`); el video dice "datos de ejemplo" junto al celular.
