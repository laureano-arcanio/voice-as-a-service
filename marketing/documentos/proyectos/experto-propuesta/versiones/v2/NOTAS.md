# experto-propuesta · v2

Estado: borrador

- **Pedido (11-nov-2026, Laureano, textual):** "quita en 'LO QUE YA HACEN BIEN' la frase de con esta última
  quintuplicamos nuestra capacidad productiva, no tiene sentido en el contexto. Si hay algo mejor, alguna reseña que
  pueda mencionar, si no, no lo ponemos. Resulta muy largo, tiene 5 hojas. Veamos si podemos reducirlo a 2 o 3 con lo
  más importante y más relevante."
- **Archivos:** `documento.html` (copiado de v1), `documento.pdf` (3 hojas A4), `vista-1.png` a `vista-3.png`.
- **Qué cambió:**
  - La cita de los dueños sale; en su lugar, la reseña "Gran asesoramiento para quienes justamente no somos expertos!"
    (5★, Villa Carlos Paz; la misma que usa el video).
  - "7 canales" sale: el texto nombra los canales sin número (WhatsApp central, cuatro líneas de sucursal, 0800, mail y
    formulario; la base cuenta 8).
  - Hoja 1 = portada + lo que hacen bien (cuatro cifras y la reseña) + "Dónde podríamos mejorar" en cuatro tarjetas
    (retiros y reclamos juntos) + las dos reseñas críticas en una línea. Salen los seis puntos de fortalezas y el
    recuadro "en tres líneas".
  - Hoja 2 = la solución de v1 sin cambios (canales, resuelve/deriva, diagrama, segunda etapa).
  - Hoja 3 = panel reducido (cinco indicadores, por sucursal y cotizaciones por asesor; salen por canal y por tipo) +
    piloto en un párrafo, seis pasos cortos, "Necesitamos de ustedes" y "Después" en dos bloques, precio y contacto.
    Salen la tabla "Lo observado → qué lo resuelve", "Atentina hace" y las cuatro fases detalladas.
- **Controles:** `make doc P=experto-propuesta V=2 HOJAS=3` (3 hojas, fuentes de la marca); vistas revisadas a 110 dpi;
  `pdftotext` con el 0800, el mail y el WhatsApp como texto; contacto igual a `site.ts`; sin "quintuplicamos" ni
  "7 canales".
