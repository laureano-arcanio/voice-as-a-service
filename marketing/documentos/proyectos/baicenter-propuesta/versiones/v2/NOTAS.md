# baicenter-propuesta · v2

Estado: borrador

- **Pedido (22-oct-2026, Laureano, textual):** "No ofrecen planes de ahorro. Seguramente financiación." El banner "BAIC
  Plan, 84 cuotas" es el plan de la marca; lo confirmado es la financiación con Bancor, Banco Nación, Santander y
  Galicia y los créditos propios de la concesionaria (Edgardo, Punto a Punto, 29-jun-2026). Leasing y prendarios (solo
  LinkedIn) no se nombran.
- **Archivos:** `documento.html` (copiado de v1), `documento.pdf` (5 hojas A4), `vista-1.png` a `vista-5.png`.
- **Qué cambió:**
  - Hoja 1: la tarjeta 3 pasa de "Plan de ahorro / 84 cuotas" a "FINANCIACIÓN / Cuatro bancos y crédito propio: muchas
    preguntas antes de venir"; en "Canales", "plan de ahorro" → "financiación".
  - Hoja 2: sin el "~30 % de las operaciones" ni los 84 meses ("Muchas formas de pagar, muchas preguntas"); "Lo
    prometido" sin la cuota del plan; la fuente de Punto a Punto queda para la financiación.
  - Hoja 3: forma de pago "contado, financiación bancaria o crédito propio" (sin leasing); en el diagrama, "Plan de
    ahorro" → "Financiación"; ficha con "financiación bancaria".
  - Hoja 4: "Plan de ahorro 132" → "Financiación 132"; fila "Preguntas de financiación antes de venir → Explica las
    opciones y toma los datos; montos y tasas, el vendedor."
  - Hoja 5: relevamiento y "Necesitamos de ustedes" con las opciones de financiación vigentes; la fase "Plan de ahorro"
    sale y entra "Mitsubishi" (el piloto es BAIC y Arcfox; las otras marcas se suman por fases).
- **Controles:** `make doc P=baicenter-propuesta V=2 HOJAS=6` (5 hojas, fuentes de la marca); vistas revisadas a 110 dpi;
  `grep` sin "plan de ahorro", "84", "leasing" ni "30 %" en el HTML; contacto igual a `site.ts`.

## Cambio del 22-oct-2026 (en la misma v2)

- Pedido (Laureano, textual): "cambia areas a mejorar por \"Donde podriamos mejorar con Atentina\" pdf y video."
- Hoja 1: el título "Áreas a mejorar" pasa a "Dónde podríamos mejorar con Atentina".
- Hoja 4: la tabla se titula "Dónde podríamos mejorar con Atentina, y cómo", con las columnas "Dónde" y "Qué lo resuelve".
