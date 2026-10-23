# cimepa-propuesta · v1

Estado: borrador

- **Pedido:** propuesta técnica y de integración para CIMEPA S.A. (Pablo), con la solución decidida por Laureano el
  22-oct-2026; texto completo en el [README](../../README.md).
- **Archivos:** `documento.html` (fuente), `documento.pdf` (5 hojas A4, fuentes de la marca incrustadas),
  `vista-1.png` a `vista-5.png`.
- **Qué es:** primera versión, con la plantilla y los componentes de `base.css` más estilos locales en un `<style>`
  (pedidos con cita, tabla agrupada pedido → solución, flujos, vías de integración, bloque de código, preguntas, pasos de
  a cuatro y fases), tomados de Goldman y BAIC.
- **Cambios durante el armado:** en el diagrama, la etiqueta rotada "contexto y salientes por API" pisaba la flecha
  punteada y la de la app web → dos flechas cortas entre la plataforma y su sistema, con sus dos leyendas abajo; la
  cifra "Cada llamada" partía en dos líneas → "Todas".
- **Controles:** `make doc P=cimepa-propuesta V=1 HOJAS=5` (5 hojas, fuentes de la marca); vistas revisadas a 110 dpi
  (`scratch/cimepa-doc/`); `pdftotext` muestra el 0800, la web, el mail y el WhatsApp como texto; contacto igual a
  `site.ts`; `grep` sin "Anura", "Asterisk", "Zoiper", "central", "gateway", "portabilidad" ni precios; sin logo de
  CIMEPA.
