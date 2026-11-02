# simtecuida-propuesta · v2

Estado: borrador

- **Pedido (Laureano, textual):** "Quita la sección piloto y agreguemos una sección presupuesto. En esta sección comentamos el
  costo de 29.000 pesos de base y le vamos a sumar 10.000 pesos más por mantenimiento del sistema CRM para el almacenaje de los
  pacientes y las consultas, y además esto incluye el teléfono 0800 si es que lo quieren. quita también la sección oportunidades."
  Regla nueva: sin fondos azul oscuro; todo en blanco o claro, y el azul de marca solo para acentos.
- **Archivos:** `documento.html` (copiado de v1), `documento.pdf` (5 hojas A4), `vista-1.png` a `vista-5.png`.
- **Qué cambió:**
  - Sale la hoja "Dónde podríamos mejorar con Atentina" con sus preguntas, "lo que también se ve" de la portada y la tabla "lo
    observado → qué lo resuelve" del panel.
  - Sale el piloto: 30 días, línea de base, decisión con números, revisión semanal, "si no, se termina", "Después del piloto" y
    el precio en la reunión. En emergencias, "se revisa cada semana" pasa a "se prueba con ustedes antes de salir en vivo".
  - Puesta en marcha en tres pasos, con quién hace qué sin las tareas del piloto y su WhatsApp a definir en el relevamiento.
  - Sección nueva "Presupuesto": $ 29.000 + $ 10.000 = $ 39.000 por mes, con la fecha y dos aclaraciones (capacidad y 0800).
    Portada: "Plan Mostrador y mantenimiento del sistema CRM: $ 39.000 por mes". Salen "dos llamadas simultáneas como mínimo" y
    "con la capacidad ajustada a su guardia".
  - Sin fondos oscuros: bandas de los mocks y pie de contacto en claro, con el logo oscuro; el chip "Posible emergencia" del
    diagrama, blanco con borde de acento. Se hace en el `<style>` del documento.
  - El mock del panel se lee más grande: ahora tiene la hoja para él.
- **Controles:** `make doc P=simtecuida-propuesta V=2 HOJAS=6` (5 hojas, fuentes de la marca); vistas revisadas a 110 dpi; `grep`
  en el HTML y en el texto del PDF sin piloto, oportunidades, 30 días, línea de base, revisión semanal, dos llamadas, SMS ni redes;
  sin `background` oscuro ni logo blanco en el HTML; contacto igual a `site.ts`; $ 29.000 igual a `site.ts` y `tiers`.
