# goldman-propuesta · v1

Estado: borrador

- **Pedido:** "Un PDF con el análisis observado de su problema actual, fáctico pero con lenguaje amable. La solución
  propuesta. Y cómo se pondría en marcha."
- **Archivos:** `documento.html` (fuente), `documento.pdf` (5 hojas A4, fuentes de la marca incrustadas),
  `vista-1.png` a `vista-5.png`.
- **Qué es:** primera versión, con la plantilla y los componentes de `base.css` más estilos locales en un `<style>` del
  documento (hechos con borde naranja, citas, bloque positivo, tres canales, bloque "un solo precio", mock del panel,
  tabla de mapeo, piloto, pasos de a tres y fases).
- **Cambios durante el armado:** "Desde los 90" no entraba en la cifra → "30 años"; la hoja 4 desbordaba el pie →
  título más corto, tabla de mapeo en una línea por fila y encabezados del mock más cortos; la nota de precio de la
  hoja 5 quedaba tapada por el pie → pasos y "quién hace qué" más compactos; se sumó lo positivo de las reseñas en la
  hoja 2 (tenía aire libre) y se suavizó "las reseñas son la única métrica" (no lo sabemos).
- **Controles:** `make doc P=goldman-propuesta V=1 HOJAS=6` (5 hojas, fuentes de la marca); vistas revisadas a 110 dpi;
  `pdftotext` muestra el 0800, la web, el mail y el WhatsApp como texto; contacto igual a `site.ts`; sin logo de
  Goldman.
