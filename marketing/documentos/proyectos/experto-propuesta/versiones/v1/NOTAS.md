# experto-propuesta · v1

Estado: cerrada (11-11-2026)

- **Pedido:** "crea una propuesta en PDF y en video de cómo Atentina podría integrarse en sus operaciones."
- **Archivos:** `documento.html` (fuente), `documento.pdf` (5 hojas A4, fuentes de la marca incrustadas),
  `vista-1.png` a `vista-5.png`.
- **Qué es:** primera versión, con los componentes de `base.css` y estilos locales copiados de goldman y baicenter
  (cita, mock del panel, tabla de mapeo, piloto, pasos de a tres y fases), más filas "Hoy / Con Atentina" para las
  oportunidades, el bloque de tres líneas de la portada, "Resuelve solo / Deriva" y la segunda etapa saliente.
- **Cambios durante el armado:** las hojas 2 y 3 desbordaban el pie → títulos de una línea, textos de las filas y de
  las tarjetas de canales más cortos, entrada de la hoja 3 en tres líneas, línea de fuentes de la hoja 2 en una línea;
  el texto del panel en el diagrama pisaba el rótulo "Para los dueños" → corrido a la derecha.
- **Controles:** `make doc P=experto-propuesta V=1 HOJAS=6` (5 hojas, fuentes de la marca); vistas revisadas a 110 dpi;
  `pdftotext` muestra el 0800, la web, el mail y el WhatsApp como texto; contacto igual a `site.ts`; sin logo de
  Experto; sin precios; sin "varias a la vez"; sin la página de Envíos ni la competencia.
