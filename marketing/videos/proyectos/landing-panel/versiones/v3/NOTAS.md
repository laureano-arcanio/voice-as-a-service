Estado: cerrada (30-10-2026)

# Landing: el panel para configurar tu agente, v3

## Pedido

> la fuente de arriba donde va diciendo lo que se hace es muy grande y ocupa demasiado espacio

(30-oct-2026.) Además: en la página el video va sin borde sobre fondo blanco, así que el fondo del video tiene que
ser blanco puro en todo el cuadro, sin sombra ni borde que marque el límite contra la página. Mismo formato que la v2.

## Qué cambió respecto de la v2

- **Títulos de los momentos:** 62 px en una línea centrada (eran 100 px en dos líneas), unos 31 px a 540 px de
  ancho. Arriba a 40 px; la franja blanca del título pasó de 345 a 150 px de alto.
- **Intro y cierre:** logo de 112 a 72 px y frase de 100 a 62 px ("Todo tu agente, / en un solo panel." y
  "Agentes con IA / que atienden / a tus clientes.").
- **Más lugar para el panel:** la cámara se centra en y = 745 (era 845). Con el mismo zoom se ve mucho más de cada
  pantalla en alto (p. ej. el agente entero con Agente y Objetivo, la grilla de voces con la prueba, el modal de la
  llamada entero). El zoom no sube porque el ancho ya está al límite (el contenido mide 728 px de ventana).
- **Bordes blancos:** la ventana del panel no tiene sombra (queda su borde suave de 2 px) y los bordes izquierdo,
  derecho e inferior del cuadro se funden a blanco (56, 56 y 70 px). Medido en un cuadro con el modal oscurecido: la
  columna izquierda, la derecha y la fila de abajo quedan entre 251 y 255 (ruido del códec); la de arriba, en 255.
- Reportes: al final, la cámara baja un poco menos (se ven las barras arriba de los KPI).

## Archivos

| Archivo | Para qué | Tamaño |
|---|---|---|
| `landing-panel-v3.mp4` | Máster (H.264, CRF 18, sin audio) | 5,0 MB |
| `landing/public/videos/landing-panel-v3.mp4` | Web, 1080 × 1350, H.264 CRF 26 `slow`, yuv420p, `faststart`, `-an` | 2,3 MB |
| `landing/public/videos/landing-panel-v3.jpg` | Poster: cuadro de 5,4 s (Sofía elegida y la prueba de voz), 1080 × 1350 | 134 KB |

Mismos comandos de ffmpeg que la v2 (con `v3`).

## Locución

Ninguna.

## Controles

- v2 cerrada antes de tocar el código (`make video-cerrar P=landing-panel V=2`).
- `npx tsc --noEmit` sin errores.
- Cuadros de prueba (`scratch/videos/landing-panel/v3-*.png`) y hoja de un cuadro por segundo a 540 px
  (`scratch/videos/revision/landing-panel-v3/`): los títulos entran en una línea, sin cortes.
- Primer y último cuadro blancos puros: el loop empalma.

## A revisar antes de mostrarlo afuera

- Lo mismo que la v2: datos ilustrativos (Reportes, nombres, teléfonos, URL, respuesta, horario, conversación), el
  nodo "Tu sistema" y los retratos del equipo no son del panel real; Herramientas y Equipo dependen del plan;
  `docs/features/PRIMERA_VEZ.md` todavía dice "sin desplegar".
- Con el modal abierto (Derivás y Lo probás), el velo oscuro del panel llega cerca del borde de abajo y se funde a
  blanco en los últimos 70 px: mirarlo en la página.
