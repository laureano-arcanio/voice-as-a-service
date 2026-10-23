# sqlamoblamientos-propuesta · v1

Estado: cerrada (22-10-2026)

- **Pedido (22-oct-2026, Laureano, textual):** "Un PDF con el análisis de su situación actual, fáctico pero con lenguaje
  amable. La solución propuesta. Y cómo se pondría en marcha."
- **Archivos:** `documento.html` (fuente), `documento.pdf` (5 hojas A4, fuentes de la marca incrustadas),
  `vista-1.png` a `vista-5.png`.
- **Qué es:** primera versión, con los estilos locales de `baicenter-propuesta` v2. Cambios respecto de BAIC: hoja 1
  con el camino del mueble a medida en siete pasos (los de espera del cliente marcados) y "Por qué ahora"; hoja 2 une
  "Dónde podríamos mejorar" (seis tarjetas) con las dos reseñas y lo positivo; el panel suma una segunda fila (pedidos
  contra el plazo, reclamos y el origen de la consulta para marketing, destacado).
- **Cambios durante el armado:** la hoja 4 se pasaba del pie → lead más corto, encabezados y nombres de la tabla del
  mock más cortos (sin partir filas) y la tabla "Dónde → Qué lo resuelve" en una línea por fila; "9 provincias" partía
  la cifra → "20 locales"; la hoja 1 tenía aire abajo → "Por qué ahora"; se sacaron frases sin fuente ("una promesa que
  pocas fábricas pueden hacer", "se decide por recomendación", "suele llegar a Córdoba").
- **Controles:** `make doc P=sqlamoblamientos-propuesta V=1 HOJAS=6` (5 hojas, fuentes de la marca); vistas revisadas a
  110 dpi (`scratch/sql-doc/`); `pdftotext` muestra el 0800, la web, el mail y el WhatsApp como texto; contacto igual a
  `site.ts`; sin logo de SQL; sin competencia ni fallas del sitio; sin el texto oculto del sitio.
