# propuesta-atentina · v1

Estado: borrador

- **Pedido:** "Revisá el PDF que armamos para Yoiser. Creá uno nuevo pero genérico, que incluya toda la propuesta
  de Atentina, sin ser demasiado largo. Mantené el mismo template y estilo."
- **Archivos:** `documento.html` (fuente), `documento.pdf` (3 hojas A4, fuentes de la marca incrustadas),
  `vista-1.png` a `vista-3.png`.
- **Qué es:** primera versión, a partir de la estructura de `yoizen-propuesta` v1 (hero, cuatro cifras, problema
  frente a aporte, diagrama, tarjetas numeradas, quién hace qué, pasos, nota y pie). Componentes nuevos, en un
  `<style>` del documento (no en `base.css`): seis tarjetas, etiqueta "Próximamente", usos, bloque de inferencia
  propia y tarjetas de planes.
- **Cambios durante el armado:** "0800, 0810 y números regionales" se salía de la caja del diagrama → "0800, 0810
  y regionales"; título de la tarjeta 1 acortado a "Teléfono"; menos aire en la hoja 2 para separar el bloque de
  privacidad del pie; la nota de campañas no promete fecha ("llegan próximamente").
- **Controles:** `make doc P=propuesta-atentina V=1 HOJAS=4` (3 hojas, fuentes de la marca); vistas revisadas a
  110 dpi; `pdftotext` muestra el 0800, la web, el mail y el WhatsApp como texto; contacto igual a `site.ts`.
