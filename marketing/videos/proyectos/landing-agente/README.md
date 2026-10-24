# Landing: el agente resuelve y deriva lo importante

Video horizontal para la landing, sin locución y en loop: el agente (el logo con un aro de puntos que gira como
una espera) recibe consultas de clientes distintos por canales distintos, resuelve casi todas y solo pasa las
importantes a una persona del equipo, que le responde al cliente.

## Pedido

> quiero hacer un nuevo video, no en el mismo que este. Para usar en la landing. formato horizontal. El fondo es
> siempre blanco. Inicia en blanco todo. Luego aparece en el centro el logo, con el circulo de puntos simulando un
> loop de agente/progreso/espera. Luego aparecen clientes a la izquierda, que envian mensages al agente, estos
> mensajes giran en el circulo central en la medida que van entrando. Los clientes aparecen de arriba hacia abajo,
> distintas personas, medios y "consultas" es decir que se entienda que quieren diferentes cosas. luego aparece el
> operarrio, la persona humana en la transferencia, solo algunos mensajes le llegan y los vuelve a mandar a su
> cliente. que se entienda que el agente solo deriva lo que importante.

("No en el mismo que este" = no es el proyecto [`derivaciones`](../derivaciones/README.md).)

## Público, mensaje y formato

- **Público:** quien entra a la landing (empresas que atienden clientes por teléfono, WhatsApp o la web).
- **Mensaje:** el agente resuelve lo de todos los días y a tu equipo le llega solo lo importante.
- **Formato:** 1920 × 1080, 30 fps, 27,6 s. Fondo blanco siempre (sin la grilla de puntos de los otros videos),
  empieza y termina en blanco para que el loop empalme. **Sin audio** (ni locución ni música): en la landing se
  reproduce silenciado; el texto de pantalla cuenta todo.
- **Contexto:** para el `<video autoplay muted loop playsinline>` de la landing. No está integrado en `landing/`
  todavía: los archivos para web están en `versiones/vN/web/`.

## Guion (un solo plano)

| Tiempo | Qué se ve | Texto en pantalla |
|---|---|---|
| 0,0–0,5 | Blanco | — |
| 0,5–1,3 | Los 40 puntos del aro aparecen uno por uno, en sentido horario | — |
| 1,1–3,2 | El isotipo entra en el centro; el aro gira como una espera (un tramo en el acento recorre los puntos); debajo, "Atentina" | Atentina |
| 3,4–7,9 | Seis clientes aparecen a la izquierda, de arriba hacia abajo: persona, canal y consulta. Cada consulta sale como un paquete con el ícono del canal, entra al aro y gira con él; el logo mueve las barras según cuántas hay | TUS CLIENTES · Consultan por teléfono, **WhatsApp o la web.** |
| 6,8–9,9 | Las cuatro consultas del día a día dan una vuelta y vuelven con un check: aparece la respuesta del agente (con el isotipo) y el estado "resuelta". Abajo del aro, el contador | EL AGENTE · Entiende cada consulta **y la resuelve.** |
| 8,2–12,0 | Las dos importantes (una venta grande y un reclamo, las dos por llamada) se quedan girando, se ponen verdes con un halo y la fila dice "para tu equipo" | — |
| 10,6–15,4 | Entra Lucía (tu equipo) a la derecha. Las dos importantes salen del aro hacia ella, con su resumen ("Venta grande · Javier · 200 unidades", "Reclamo · Jorge · cobro doble"); "en curso" → "respondida", y su respuesta viaja por debajo del aro directo al cliente ("Lucía: …") | TU EQUIPO · Le llega **solo lo importante.** |
| 11,2–17,4 | Mientras tanto, cuatro clientes repreguntan y el agente también lo resuelve | — |
| 17,4–18,6 | Cuadro completo: 8 resueltas · 2 derivadas | — |
| 18,6–23,4 | Se van los clientes y Lucía; queda el logo con el aro y el contador | AGENTES CON IA QUE ATIENDEN A TUS CLIENTES · Resuelven el día a día. **Te pasan lo importante.** |
| 23,7–25,9 | Logo, aro y "Atentina" (el mismo cuadro del principio) | Atentina |
| 26,0–27,1 | Los puntos se van en orden inverso y el isotipo se achica | — |
| 27,1–27,6 | Blanco (empalma con el principio) | — |

**Clientes y consultas (ilustrativos):**

| Fila | Persona · canal | 1.ª consulta → respuesta | 2.ª consulta → respuesta |
|---|---|---|---|
| 1 | Carolina · WhatsApp | ¿Hasta qué hora abren hoy? → Hoy, hasta las 20. | ¿Tienen estacionamiento? → Sí, en la esquina. |
| 2 | Martín · Llamada | Quiero un turno para el jueves. → Listo, jueves a las 10:30. | ¿Qué tengo que llevar? → Solo tu DNI. |
| 3 | Ana · Web | ¿Cuánto sale el plan mensual? → $ 18.500 por mes. | ¿Puedo pagar con tarjeta? → Sí, en hasta 3 cuotas. |
| 4 | Diego · WhatsApp | ¿Hacen envíos a Rosario? → Sí, llegan en 48 horas. | ¿Cuánto sale el envío? → Es gratis desde $ 50.000. |
| 5 | Javier · Llamada | Necesito 200 unidades para mi empresa. → **a Lucía** → "Te armo la cotización hoy." | — |
| 6 | Jorge · Llamada | Me cobraron dos veces este mes. → **a Lucía** → "Lo reviso con vos ahora." | — |

## Afirmaciones y fuentes

- **Canales: teléfono, WhatsApp y la web** (link para llamar y la demo). Desplegados: [`AGENTS.md`](../../../../AGENTS.md),
  [`docs/WHATSAPP_PLAN.md`](../../../../docs/WHATSAPP_PLAN.md), [`docs/LINK_LLAMADA_PLAN.md`](../../../../docs/LINK_LLAMADA_PLAN.md).
- **Derivación a una persona del equipo:** la transferencia de **llamadas** está desplegada desde el 23-oct-2026
  (fases 1 y 2), **sin probar todavía con llamadas reales** ([`docs/DERIVACIONES_PLAN.md`](../../../../docs/DERIVACIONES_PLAN.md),
  13.4). Por eso las dos derivadas son llamadas. La derivación de **WhatsApp** (puente por la bandeja, 5.8) no
  está implementada: ninguna consulta de WhatsApp se deriva en el video.
- **La persona recibe de qué se trata antes de atender** (el aviso con el resumen, "Derivación de {{area}}:
  {{resumen}}"): DERIVACIONES_PLAN 13.1. Las tarjetas de Lucía lo representan; no es una pantalla del panel.
- **"Agentes con IA que atienden a tus clientes":** la categoría de la marca ([`docs/DESIGN_GUIDELINE.md`](../../../../docs/DESIGN_GUIDELINE.md), 10).
- **Sin cifras medidas:** no hay latencia, capacidad ni porcentaje de resolución. El contador (8 resueltas · 2
  derivadas) cuenta lo que pasa en el video; es ilustrativo.

**Ilustrativo:** las personas, sus consultas y respuestas, los precios ($ 18.500, $ 50.000, 3 cuotas), "Lucía" y
el contador. Las respuestas que dependen de datos del negocio (precios, turnos, envíos) suponen que el agente los
tiene en su definición o en una herramienta. Sin logos ni pantallas de terceros: WhatsApp aparece como ícono de
trazo propio (`Icon`) y su nombre escrito.

## Decisiones

- **El "círculo de puntos"**: un aro de 40 puntos alrededor del isotipo (el isotipo queda intacto, como pide la
  guía de marca). Un tramo en el acento recorre el aro como un spinner; las consultas giran sobre el mismo aro a
  una vuelta cada 1,8 s y el tramo brilla más cuantas más hay girando.
- **Paquetes:** a la ida, el color del canal (llamada en el acento, WhatsApp en `wa`, web en `ink`); a la vuelta,
  un check en el acento (agente) o en `ok` (equipo). Lo derivado pasa a verde con halo antes de salir.
- **Sin audio:** la landing lo reproduce silenciado; la música no suma y pesa. `guion.json` no tiene líneas.
- **Títulos arriba a la derecha** durante la acción (arriba al centro, los paquetes de la primera fila pasaban
  por encima del texto); el del cierre, centrado.

## Versiones

| Versión | Estado | Qué cambió |
|---|---|---|
| v1 | borrador | Primera versión: 27,6 s, sin audio, con versiones para web (MP4 1080p y 720p, WebM 720p) y póster. |
