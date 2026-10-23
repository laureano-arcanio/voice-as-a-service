# sqlamoblamientos-propuesta · v2

Estado: borrador

- **Pedido (22-oct-2026, usuario por el coordinador):** h1 nuevo ("Cada consulta atendida. Su cliente y ustedes, siempre
  al tanto de lo que pasa."); igualar con el video v2 ("Lo que ya hacen muy bien" y la tarjeta de horario reducido, sin
  la cocina de noche); sumar una línea 0800 o 0810 como canal; énfasis en el pase a una persona del equipo; dejar claro
  que el agente atiende llamadas de voz (0800/0810, línea y llamadas de WhatsApp) además de mensajes y audios; el agente
  con pedidos y catálogo actualizados, conectado a sus sistemas o planillas.
- **Archivos:** `documento.html` (copiado de v1), `documento.pdf` (5 hojas A4), `vista-1.png` a `vista-5.png`.
- **Qué cambió:**
  - Hoja 1: eyebrow "Un asesor de guardia 24/7, al teléfono y en WhatsApp"; h1 nuevo; lead con llamadas y WhatsApp,
    pedidos y catálogo al día y el pase a una persona sin repetir nada; "Lo que ya hacen muy bien".
  - Hoja 2: tarjeta "HORARIO REDUCIDO · Atención en horario reducido: 44 de las 168 horas" (horario completo, sin la
    cocina de noche) con "Oportunidad: responder también fuera de horario y dejar la visita o la medición agendada.";
    fabricación con "el dato de su pedido"; red con "un número para todo el país".
  - Hoja 3: h2 "Un asesor de guardia, y una persona cuando hace falta."; lead con las llamadas (0800/0810, línea, llamadas
    de WhatsApp) y los mensajes y audios; seis tarjetas nuevas (atiende y califica, conoce sus productos, sabe cómo va
    cada pedido, agenda y avisa, toma los reclamos, **pasa a una persona**, destacada); recuadro "Una persona, a un
    paso" con la ficha; diagrama con cuatro canales (0800/0810, línea, WhatsApp con mensajes, audios y llamadas, sitio),
    flecha gruesa "pasa a una persona, con la charla y la ficha", caja neutra "Sus datos: pedidos y catálogo" y el panel
    con "resueltas y pasadas a una persona: quién la tomó y cuánto tardó".
  - Hoja 4: lead y KPIs con resueltas solas (189) contra pasadas a una persona (121); canales con 0800/0810 y llamadas
    de WhatsApp; la tabla por persona pasa a "Pasadas a una persona: quién y cuánto tardó"; filas de la tabla final con
    el pase a una persona, el horario reducido, el dato del sistema y el 0800 para todo el país.
  - Hoja 5: piloto "0800, WhatsApp y línea"; relevamiento y salida en vivo con el pase a una persona; "Atentina hace"
    con el alta del 0800/0810 y la conexión a pedidos y catálogo; "Necesitamos de ustedes" con el acceso a la fuente de
    pedidos y el catálogo; fase de franquicias por el 0800; nota de precio con la elección del 0800 o 0810; pie "Cada
    consulta atendida, a toda hora."
- **Cambios durante el armado:** la hoja 3 se pasaba del pie → h2 en una línea, tarjetas y caption más cortos.
- **Controles:** `make doc P=sqlamoblamientos-propuesta V=2 HOJAS=6` (5 hojas, fuentes de la marca); vistas revisadas a
  110 dpi; `grep` sin "noche" ni "cocina se piensa"; `pdftotext` con el 0800, el mail y el WhatsApp como texto; contacto
  igual a `site.ts`.
