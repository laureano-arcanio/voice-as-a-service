Estado: cerrada (30-10-2026)

# Landing: el panel para configurar tu agente, v2

## Pedido

> Hacé la v2 de landing-panel en formato vertical, para que se vea más lo que pasa en pantalla y no quede tanto
> espacio en blanco.

(30-oct-2026.) En la home el video va en la columna derecha (~540 px de ancho), al lado de una lista de 6 funciones de
~780 px de alto: en 16:9 quedaba bajito, con mucho blanco, y el panel se veía chico. Formato 4:5 (1080 × 1350),
mismo largo, mudo y en loop; mismos momentos y textos; "Hablarle ahora" se deja (según el usuario, la app en
producción ya tiene Inicio con ese botón).

## Qué cambió respecto de la v1

- **Formato:** 1080 × 1350 (4:5) en vez de 1920 × 1080. Mismo largo (20,0 s) y mismos tiempos.
- **Ventana del panel angosta y alta** (1100 × 1600, menú de 300 px, contenido de 728 px): cada pantalla se
  reacomodó en una columna, como se ve el panel en una pantalla chica. Agente: Nombre e Idioma en una fila y Rol
  abajo; voz: la grilla de 3 × 2 y la elegida con la prueba debajo (VoiceSelect pasa a una columna en `base`);
  herramienta: el formulario, "Tu sistema" y la tarjeta Probar uno abajo del otro; Reportes: el gráfico y los tres
  KPI apilados.
- **Cámara más cerca:** cada momento abre con la ventana entera (zoom 1,12) y se acerca a 1,34–1,48 sobre lo que
  importa; a 540 px el texto del panel queda en ~16–20 px.
- **Títulos en dos líneas** (frase en `ink`, remate en `accent`), 100 px: ~50 px a 540 px. Intro y cierre también
  partidos en líneas.
- **Tu sistema:** la respuesta vuelve sin línea punteada (en vertical cruzaba la tarjeta Probar); el paquete "{ }"
  baja por la derecha hasta el resultado.
- Pestañas un poco más chicas (21 px) para que entren hasta "Voz y canales"; las que no entran se cortan, como en
  una pantalla angosta.

## Archivos

| Archivo | Para qué | Tamaño |
|---|---|---|
| `landing-panel-v2.mp4` | Máster (H.264, CRF 18, sin audio) | 4,8 MB |
| `landing/public/videos/landing-panel-v2.mp4` | Web, 1080 × 1350, H.264 CRF 26 `slow`, yuv420p, `faststart`, `-an` | 2,3 MB |
| `landing/public/videos/landing-panel-v2.jpg` | Poster: cuadro de 5,4 s (Sofía elegida y la prueba de voz), 1080 × 1350 | 142 KB |

```bash
cd marketing/videos/proyectos/landing-panel/versiones/v2
ffmpeg -i landing-panel-v2.mp4 -an -c:v libx264 -preset slow -crf 26 -pix_fmt yuv420p -movflags +faststart ../../../../../../landing/public/videos/landing-panel-v2.mp4
ffmpeg -ss 5.4 -i landing-panel-v2.mp4 -frames:v 1 -q:v 3 ../../../../../../landing/public/videos/landing-panel-v2.jpg
```

## Locución

Ninguna. No se usó el TTS ni el STT.

## Controles

- v1 cerrada antes de tocar el código (`make video-cerrar P=landing-panel V=1`; `scripts/cerrar.sh` ahora copia
  `vo/` y `voces/` solo si existen: los videos mudos no tienen `vo/`).
- `npx tsc --noEmit` sin errores.
- Cuadros de prueba en `scratch/videos/landing-panel/v2-*.png` y hojas (dos cuadros por segundo, a 540 px) en
  `scratch/videos/revision/landing-panel-v2/`. Corregido en el camino: el zoom de 1,5–1,55 cortaba los bordes del
  modal de Ventas, del modal de la llamada y de los KPI (bajó a 1,34–1,48); al final del momento 1 la grilla de voces
  quedaba bajo el título; el cursor del momento 3 caía en la ayuda y no en "Rotativa"; la línea de vuelta de "Tu
  sistema" cruzaba la tarjeta.
- Primer y último cuadro blancos puros (255): el loop empalma.
- `make video-revisar` no aplica (sin audio; las hojas, con ffmpeg).

## A revisar antes de mostrarlo afuera

- **Ilustrativo:** números de Reportes, nombres ("Sofía", "Ana"), teléfonos, URL, respuesta de la herramienta,
  horario y la conversación. El nodo "Tu sistema" no es una pantalla del panel; los retratos de las personas del
  equipo no existen en el panel real.
- **"Hablarle ahora":** el usuario confirma que está en producción; `docs/features/PRIMERA_VEZ.md` todavía dice "sin
  desplegar" (actualizarlo en su sesión).
- Herramientas y Equipo dependen del plan.
