# zennonbi-propuesta · v1

Estado: borrador

- **Pedido (22-oct-2026, Laureano, textual):** "Investiga la empresa zennonbi, identifica posibles alianzas o
  integraciones a sus productos. Arma un pdf y un video diseñado para ellos."
- **Archivos:** `documento.html`, `documento.pdf` (5 hojas A4), `vista-1.png` a `vista-5.png`.
- **Qué tiene:** primera versión. Estructura y fuentes en el [README](../../README.md). Estilos locales de Axioma
  (tarjetas de oportunidad, tabla `spec`, oferta, pasos de a seis, fases) y de BAIC (tablero y tabla `map`); nuevos: el
  recuadro "Un dato del mercado" (`.market`), los recorridos saliente y entrante (`.flows`), el módulo junto a los
  KickStart (`.module`) y "qué gana cada parte" (`.gains`).
- **Controles:**
  - `make doc P=zennonbi-propuesta V=1 HOJAS=6`: 5 hojas, fuentes de la marca (Bricolage, Figtree, Plex Mono).
  - Vistas revisadas a 110 dpi (`scratch/zennonbi-doc/`): en la hoja 4 la tabla "Hoy / Con Atentina" pisaba el pie (se
    sacó la fila del agente de calificación, que ya está en la hoja 2, y se ajustaron márgenes); en la hoja 3 el texto
    "Sus clientes" se salía de su caja (se partió en más líneas) y la tabla quedaba pegada al pie (márgenes del título).
    El título de la hoja 4 decía "con la marca y el cliente de Zennon": se cambió para no sugerir marca blanca.
  - `pdftotext`: 0800, mail, web y WhatsApp como texto; contacto igual a `site.ts`; sin precios nuestros, sin "MCP",
    sin logos de Zennon ni de Microsoft.
