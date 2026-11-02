# simtecuida-propuesta · v1

Estado: cerrada (02-11-2026)

- **Pedido:** el textual está en el [README](../../README.md) del proyecto.
- **Archivos:** `documento.html` (fuente), `documento.pdf` (6 hojas A4, fuentes de la marca incrustadas),
  `vista-1.png` a `vista-6.png`.
- **Qué es:** primera versión, con la plantilla y los estilos locales de `goldman-propuesta` y `baicenter-propuesta`
  (oportunidades, mock del panel, tabla de mapeo, piloto, pasos de a tres y fases), más la ficha de clientes, la minuta y
  el recuadro de emergencias.
- **Cambios durante el armado:**
  - Seis hojas, no cinco: ficha, minuta y emergencias tienen hoja propia, para no apretar la hoja de la solución.
  - Hoja 1: "CABA y GBA" se cortaba en dos líneas, cifras a 15 pt.
  - Hoja 2: el pie tapaba las preguntas; títulos de una línea y ocho preguntas cortas. Se sacó "es lo que eligen las
    familias" (no tiene fuente).
  - Hoja 3: "atiende cada llamada" pasó a "las llamadas simultáneas que definamos" (la capacidad se define en el
    relevamiento).
  - Hoja 5: el pie tapaba la tabla; filas de una línea y un motivo menos en el mock ("Problema de guardia" dentro de
    "Novedad de cliente", las sumas siguen cerrando en 186).
  - Hoja 6: la última fila quedaba pegada al pie; "Atentina hace" en líneas cortas. "Con todo incluido" pasó a "con la
    puesta en marcha incluida" (se podía leer como precio).
- **Controles:** `make doc P=simtecuida-propuesta V=1 HOJAS=6` (6 hojas, fuentes de la marca); vistas revisadas a
  110 dpi; `pdftotext` muestra el 0800, la web, el mail y el WhatsApp como texto; contacto igual a `site.ts`; sin logo de
  SIM; búsqueda en el texto del PDF sin SMS, redes, `/admin/`, leyes, topes del plan, precios, idiomas ni competidores.
