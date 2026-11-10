# Empresa La Estrella: la propuesta en video

- **Pedido (7-nov-2026, Laureano por la sesión principal, textual):** "Hacé el video de la propuesta para Empresa La Estrella
  (colectivos de corta y media distancia, Resistencia, Chaco), siguiendo marketing/VIDEOS.md. Proyecto nuevo, versión 1. El
  video sigue al PDF ya aprobado [...] el video cuenta lo mismo, con los mismos mensajes y el mismo tono. [...] respetá lo
  que el PDF dejó afuera (sin teléfonos de la empresa, CUIT, nombres de personas, precios ni problemas de su sitio o
  reseñas). Duración entre 60 y 90 segundos como máximo. Dos voces en igual medida: paula y gonzalo [...]. Simple y
  concreto. Efectivo, moderno y entendible para gente no técnica: nada de jerga (SIP, LLM, troncal, etc.). Formato blanco de
  la marca (sin fondos azul oscuro), con intro y cierre." Mensajes en orden: quiénes son y la vanguardia; la propuesta;
  observabilidad; etapa 1; etapa 2; cómo funciona (teléfono IP: "se instala", no lo instalamos nosotros); cierre con próximos
  pasos y el contacto del PDF.
- **Contexto:** acompaña al PDF [`laestrella-propuesta`](../../../documentos/proyectos/laestrella-propuesta/README.md) v2,
  después de la charla del 6-nov-2026. Base: [`comercial/demos/laestrella.md`](../../../../comercial/demos/laestrella.md).
- **Público:** la dirección de Empresa La Estrella, no técnica. En "ustedes".
- **Mensaje:** todas las llamadas de las 6 sucursales atendidas, y por primera vez, medidas; arranca en 10 días.
- **Formato:** 1920 × 1080, 30 fps, 84,6 s. Composición `laestrella-propuesta` (`src/Video.tsx`). Todo en blanco; el
  agente es `AgenteLogo`. Piezas del diagrama (aro, paquetes, baldosas) copiadas de `simtecuida-analisis`, sin tocar
  `src/comun/`.

## Guion (v2)

`paula` y `gonzalo` alternan como diálogo dentro de cada escena (37,0 s y 35,4 s de voz: 51 / 49 %). Ortografía normal;
números en palabras; "0800" se dice "cero ochocientos"; "IP" escrito normal. `ganancia_db` −2,2.

| Escena | Tiempo | Locución | Qué se ve |
|---|---|---|---|
| `intro` | 0–14,6 s | a1 (paula) "La Estrella: más de noventa años uniendo Resistencia con el interior del Chaco. Trece corredores, seis sucursales, encomiendas, alquiler y tarjeta prepaga." · a2 (gonzalo) "Un sistema como este los pone a la vanguardia de la atención al pasajero en Argentina." | Blanco, logo oscuro, "PROPUESTA · EMPRESA LA ESTRELLA · NOVIEMBRE 2026", "Todas las llamadas atendidas, **y por primera vez, medidas.**"; las cuatro cifras del PDF (+90 años, 13 corredores, 6 sucursales, 3 servicios más) y la banda de vanguardia |
| `propuesta` | 14,0–29,3 | a3 (paula) "La propuesta: un agente con inteligencia artificial atiende todas las llamadas de las seis sucursales, las veinticuatro horas." · a4 (gonzalo) "Consulta horarios y disponibilidad. No vende. Y solo pasa a una persona de la sucursal cuando hace falta, con el motivo ya anotado." | "LA PROPUESTA · Un solo agente para las seis sucursales, **las 24 horas.**" Sucursal 1 a 6 → logo con aro ("Agente de IA", "24 horas") → "Lo resuelve el agente" (consulta de ejemplo del PDF, chips, "No vende: informa") y "Pasa a la sucursal, solo si hace falta" con el motivo anotado |
| `datos` | 29,3–39,9 | a5 (paula) "Hoy no tienen ningún dato de sus llamadas." · a6 (gonzalo) "Con Atentina, ven cuántas entran, cuántas se pierden, quién atendió y de qué hablan. Por sucursal, y por horario." | "LO MÁS IMPORTANTE · Sus llamadas, a la vista **desde el primer día.**" Hoy · sin datos contra Con Atentina · todo medido: cuatro tarjetas y dos gráficos de barras (ilustrativos, rotulados) |
| `etapa1` | 39,9–53,3 | a7 (paula) "En diez días arranca la etapa uno. Durante una o dos semanas, las llamadas pasan por nuestro sistema y van directo a la persona, sin agente." · a8 (gonzalo) "Así medimos la línea de base, y aprendemos de qué hablan sus clientes para configurar el agente." | "ETAPA 1 · EN 10 DÍAS · DE 1 A 2 SEMANAS · Diagnóstico: **medir antes de cambiar.**" El pasajero → Nuestro sistema → La sucursal ("sin agente"); "Para el pasajero nada cambia"; la línea de base y de qué hablan sus clientes |
| `etapa2` | 53,3–60,8 | a9 (paula) "En la etapa dos, el agente se suma sucursal por sucursal, y comparamos los resultados contra esa línea de base." | "ETAPA 2 · SUCURSAL POR SUCURSAL · Implementación escalonada, **contra la línea de base.**" Seis sucursales que pasan de "Directo a la persona" a "Con el agente"; atendidas, perdidas y derivadas |
| `funciona` | 60,8–70,2 | a10 (gonzalo) "Conservan sus números de siempre, fijo o cero ochocientos. El agente atiende, y si hace falta, pasa al teléfono IP que se instala en cada sucursal." | "CÓMO FUNCIONA · Sus números de siempre, **y una persona si hace falta.**" El diagrama del PDF: pasajero → el fijo de siempre o un 0800 → agente de IA → "si hace falta" → la sucursal (teléfono IP); los dos mensajes clave del PDF |
| `pasos` | 70,2–76,8 | a11 (paula) "Para arrancar en diez días, confirmamos las sucursales, los horarios y el desvío de las líneas." | "PRÓXIMOS PASOS · Para arrancar **en 10 días.**" Los tres pasos del PDF; el desvío "se activa desde el mismo teléfono, con un código" (corrección del usuario, v2) |
| `cierre` | 76,8–84,6 | a12 (gonzalo) "Cada llamada atendida, cada llamada medida." · a13 (gonzalo) "¿Damos juntos el primer paso?" | Blanco: logo oscuro, la frase del PDF con el remate en el acento, el contacto (Laureano Arcanio, 0800-220-1233, atentina.com.ar, laureano@atentina.com.ar, WhatsApp +54 9 351 700-2592) y la invitación; 2,5 s quieto y fundido a blanco con la música |

## Afirmaciones y de dónde salen

Todo sale del PDF v2 (y sus fuentes, en el README del documento):
- **+90 años, 13 corredores, unas 60 localidades, 6 sucursales, encomiendas, alquiler y tarjeta prepaga:** PDF, hoja 1.
  "+90" a confirmar con ellos (89 en ene-2024); las 6 sucursales son las que pidieron, sin lista confirmada.
- **Vanguardia, agente 24 h, consulta horarios y disponibilidad, no vende, deriva con el motivo:** PDF, hoja 1. La consulta
  "¿A qué hora sale el domingo para Villa Ángela?" es la del PDF; el motivo "comprar un pasaje para el domingo" es un
  ejemplo (rotulado en el pie).
- **Métricas:** PDF, hoja 1 (`docs/features/REPORTES.md`). **Barras ilustrativas**, rotuladas en el pie.
- **Etapas 1 y 2, plazo de 10 días:** PDF, hoja 2; promesa comercial a validar. La etapa 1 usa el entrante al equipo, en
  producción pero sin probar con llamadas reales (EQUIPO_TELEFONIA).
- **Teléfono IP en cada sucursal:** PDF, hoja 2, "se instala", sin decir quién. A validar (no está en los docs de la plataforma).
- **Omitido, como en el PDF:** precios, capacidad, teléfonos, CUIT y nombres de la empresa, problemas del sitio y reseñas.
- **Contacto:** el pie del PDF (`landing/src/data/site.ts`); desde v2, laureano@atentina.com.ar por pedido del usuario.
- **Desvío:** se activa desde el mismo teléfono con un código (dato del usuario, 7-nov-2026); el PDF v2 todavía dice que lo habilita la compañía.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 7-nov-2026 | 82,2 s | Primera versión | cerrada |
| [v2](versiones/v2/NOTAS.md) | 7-nov-2026 | 84,6 s | El desvío se activa desde el teléfono con un código (sin la nota de la compañía); frase final de invitación, espera y fundido; mail laureano@ | borrador |
