# baicenter-propuesta · v1

Estado: cerrada (22-10-2026)

- **Pedido:** "Similar al video que hicimos para isaias goldman, haremos uno igual pero con la informacion de BAIC.
  Cambiamos el enfasis un poco en lo que falla, sino mas bien areas a mejorar. Analiza el documento de BAIC luego
  implementa el video y el PDF como se hizo en Isaias."
- **Archivos:** `documento.html` (fuente), `documento.pdf` (5 hojas A4, fuentes de la marca incrustadas),
  `vista-1.png` a `vista-5.png`.
- **Qué es:** primera versión, con la estructura y los estilos locales de `goldman-propuesta` v1. Cambios de enfoque:
  "Lo que observamos" pasa a "Áreas a mejorar", con tarjetas de borde azul (no naranja) y una línea de "Oportunidad"
  cada una; la hoja 2 lleva dos citas (no cinco) y un bloque "Lo que se puede sumar"; la tabla de la hoja 4 es "Área a
  mejorar → Qué la resuelve" sin rojo; en "Por qué ahora" las viñetas son azules, no de advertencia.
- **Cambios durante el armado:** la línea de fuentes de la hoja 1 pisaba el pie → tarjetas más compactas y fuentes en
  una línea; en la hoja 3 el diagrama quedaba pegado al pie → lead más corto; el texto del panel del diagrama rozaba el
  rótulo → corrido a la derecha; en el mock, nombres de vendedor y de tipo más cortos para que no partan la línea. Se
  suavizaron afirmaciones sin fuente ("la mayoría habla bien de la atención", "no hay forma de saber").
- **Controles:** `make doc P=baicenter-propuesta V=1 HOJAS=6` (5 hojas, fuentes de la marca); vistas revisadas a 110 dpi
  (`scratch/baic-doc/`); `pdftotext` muestra el 0800, la web, el mail y el WhatsApp como texto; contacto igual a
  `site.ts`; sin logo de BAIC; la competencia no se nombra.
