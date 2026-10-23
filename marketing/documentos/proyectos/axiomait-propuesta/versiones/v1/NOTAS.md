# axiomait-propuesta · v1

Estado: borrador

- **Pedido (22-oct-2026, Laureano, textual):** "Propuesta de demo, no sabemos qué necesitan, así que investigalos como
  integradores de lo nuestro. Más bien técnico y overview del producto." Y además: "Explicá que las voces pueden sonar
  mejor, dependiendo de la configuración y ajustando la latencia deseada."
- **Archivos:** `documento.html`, `documento.pdf` (6 hojas A4), `vista-1.png` a `vista-6.png`.
- **Qué tiene:** primera versión. Estructura y fuentes en el [README](../../README.md). Estilos locales nuevos respecto
  de BAIC: bloques de código (`.code`, en Plex Mono), tabla de piezas (`table.spec`), tarjetas de voces, escala de
  latencia (`.trade`) y tarjetas de la oferta (`.offer`).
- **Controles:**
  - `make doc P=axiomait-propuesta V=1 HOJAS=6`: 6 hojas, fuentes de la marca. El primer intento cayó a DejaVu Sans
    Mono: el `…` no está en el subset latino de Plex Mono (se cambió por `...` en el código) y el `<code>` de la nota no
    tenía la fuente (regla `code` general).
  - Vistas revisadas a 110 dpi (`scratch/axiomait-doc/`): la hoja 2 desbordaba sobre el pie (se acortó el título y se
    reordenaron los puntos); en la hoja 4 la leyenda del webhook pisaba la curva (se bajó); en la hoja 6 los rótulos de
    la oferta heredaban el borde de las tarjetas (`.offer > div`).
  - `pdftotext`: 0800, mail, web y WhatsApp como texto; contacto igual a `site.ts`; sin "No Llame", sin precios, sin
    logo de Axioma.
