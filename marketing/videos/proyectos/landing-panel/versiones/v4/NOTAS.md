Estado: cerrada (30-10-2026)

# Landing: el panel para configurar tu agente, v4

## Pedido

(30-oct-2026, sobre la v3 puesta en la página.) En "Derivás a tu equipo" y "Lo probás en el momento" el velo gris de
los modales se veía como un bloque gris debajo de la tarjeta, contra el fondo blanco de la sección. Igual a la v3,
sin el velo oscuro: el modal sobre fondo blanco o un velo blanco muy suave, sin nada gris que llegue a los bordes.

## Qué cambió respecto de la v3

- El velo detrás de los modales pasó de `rgba(11,18,32,0.42)` (gris oscuro) a `rgba(255,255,255,0.72)` (blanco):
  la pantalla de atrás queda lavada y el modal se destaca.
- Los modales ("Editar área Ventas" y "Hablar con Sofía") llevan el borde de 2 px de las tarjetas y una sombra
  suave (`0 16px 40px rgba(11,18,32,.10)`, era `0 30px 80px` al 30 %), para que no marque una mancha gris abajo.
- Nada más cambia (títulos de 62 px, fondo blanco, bordes que se funden a blanco, tiempos).

## Archivos

| Archivo | Para qué | Tamaño |
|---|---|---|
| `landing-panel-v4.mp4` | Máster (H.264, CRF 18, sin audio) | 4,8 MB |
| `landing/public/videos/landing-panel-v4.mp4` | Web, 1080 × 1350, H.264 CRF 26 `slow`, yuv420p, `faststart`, `-an` | 2,2 MB |
| `landing/public/videos/landing-panel-v4.jpg` | Poster: cuadro de 5,4 s (igual al de la v3: ahí no hay modal), 1080 × 1350 | 134 KB |

## Controles

- v3 cerrada antes de tocar el código. `npx tsc --noEmit` sin errores.
- Cuadros del render a 10,0, 11,0, 13,0 y 14,5 s (con los modales abiertos): las columnas de los bordes izquierdo y
  derecho y la franja de 60 px de abajo quedan entre 251 y 255 (ruido del códec, sin gris). Revisados a la vista en
  `scratch/videos/landing-panel/v4-hoja2.png`.
- Primer y último cuadro blancos puros.

## A revisar antes de mostrarlo afuera

Lo mismo que la v3 (datos ilustrativos, "Tu sistema" y los retratos del equipo no son del panel, funciones por plan,
PRIMERA_VEZ.md desactualizado).
