Estado: borrador

# Landing: el panel para configurar tu agente, v5

## Pedido

> Quitemos todo el texto, incluida la introducción, y que directamente se muestre cómo funciona la aplicación. Que
> no tenga tanto zoom, porque hay partes que no se entienden.

(30-oct-2026.) Sin títulos, sin intro ni cierre; fundido corto desde y hacia blanco; zoom de 1,0 a 1,15 como mucho;
sin velo gris ni sombras que lleguen a los bordes; 4:5, ~20 s (hasta 24), mudo y en loop.

## Qué cambió respecto de la v4

- **Sin texto:** se quitaron los títulos de los momentos, la intro y el cierre (logo y frase). El video arranca en el
  panel (el editor del agente) con un fundido desde blanco de 9 cuadros y termina con un fundido a blanco de 9.
- **Zoom 1 = la ventana entera** en el cuadro, con margen blanco (escala 0,94 de la ventana de 1100 × 1400, que
  bajó de 1600 de alto). Cada momento abre con la pantalla entera (menú, pestañas y título de la sección) y, como
  mucho, se acerca a 1,06–1,08 con un movimiento suave:

  | Momento | Zoom |
  |---|---|
  | Agente y voz | 1,0 → 1,08 (a la grilla de voces y la prueba) |
  | Herramienta y Tu sistema | 1,0 → 1,06 |
  | Área Ventas | 1,0 → 1,06 |
  | Hablarle ahora | 1,0 → 1,08 (al modal) |
  | Reportes | 1,0 fijo |

- **Más tiempo por momento:** 22,0 s en total (4,8 · 4,4 · 4,4 · 4,2 · 4,2 s), mismos movimientos del cursor y
  apariciones; lo que sobra queda a la vista para leerlo.
- Los bordes del cuadro se funden a blanco en 22 px (antes 56–70: con la ventana entera no hace falta más) y se
  agregó el borde de arriba. Sin velo gris ni sombras grandes, como la v4.
- Reportes: las tarjetas de KPI un poco más bajas para que entren en la ventana más corta.

## Archivos

| Archivo | Para qué | Tamaño |
|---|---|---|
| `landing-panel-v5.mp4` | Máster (H.264, CRF 18, sin audio) | 2,4 MB |
| `landing/public/videos/landing-panel-v5.mp4` | Web, 1080 × 1350, H.264 CRF 26 `slow`, yuv420p, `faststart`, `-an` | 1,2 MB |
| `landing/public/videos/landing-panel-v5.jpg` | Poster: cuadro de 3,6 s (Voz y canales, Sofía elegida y la prueba), 1080 × 1350 | 114 KB |

## Controles

- v4 cerrada antes de tocar el código. `npx tsc --noEmit` sin errores.
- Hoja de un cuadro por segundo en `scratch/videos/revision/landing-panel-v5/`: en cada momento se ven el menú con el
  ítem activo, las pestañas o el título de la pantalla y la acción; nada cortado salvo el borde de la ventana con el
  zoom de 1,06–1,08.
- Primer cuadro blanco puro (255); el último, 252–255 (ruido del códec): el loop empalma.

## A revisar antes de mostrarlo afuera

- Sin zoom, el texto del panel se ve chico a 540 px (~12–13 px): se entiende la pantalla pero no se lee cada campo.
  Era el pedido; si hace falta leer algo puntual, subir el zoom de ese momento.
- Lo mismo que antes: datos ilustrativos, "Tu sistema" y los retratos del equipo no son del panel real, funciones
  por plan, PRIMERA_VEZ.md desactualizado.
