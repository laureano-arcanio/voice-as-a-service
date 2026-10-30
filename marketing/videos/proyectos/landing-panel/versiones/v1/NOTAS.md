Estado: cerrada (30-10-2026)

# Landing: el panel para configurar tu agente, v1

## Pedido

> Un pequeño video a la derecha [de una sección nueva de la home] que muestre rápidamente y de forma muy
> marketinera cómo es el panel de administración para configurar.

(30-oct-2026; detalle del encargo en el README.)

## Qué es

Primera versión. 20,0 s (600 cuadros a 30 fps), 1920 × 1080, sin pista de audio. Intro en blanco, cinco momentos
del panel recreado de ~3 s (el primero, 3,8 s) y cierre en blanco. Guion en el README.

## Archivos

| Archivo | Para qué | Tamaño |
|---|---|---|
| `landing-panel-v1.mp4` | Máster (H.264, CRF 18, sin audio) | 5,3 MB |
| `landing/public/videos/landing-panel-v1.mp4` | Web, 1920 × 1080, H.264 CRF 26 `slow`, yuv420p, `faststart`, `-an` | 2,4 MB |
| `landing/public/videos/landing-panel-v1.jpg` | Poster: cuadro de 5,3 s (Sofía elegida y la prueba de voz), 1280 px | 90 KB |

```bash
cd marketing/videos/proyectos/landing-panel/versiones/v1
ffmpeg -i landing-panel-v1.mp4 -an -c:v libx264 -preset slow -crf 26 -pix_fmt yuv420p -movflags +faststart ../../../../../../landing/public/videos/landing-panel-v1.mp4
ffmpeg -ss 5.3 -i landing-panel-v1.mp4 -frames:v 1 -vf scale=1280:-2 -q:v 3 ../../../../../../landing/public/videos/landing-panel-v1.jpg
```

## Locución

Ninguna. No se usó el TTS ni el STT.

## Controles

- `npx tsc --noEmit` sin errores.
- Cuadros de prueba en `scratch/videos/landing-panel/` y hojas (dos cuadros por segundo, a 560 px de ancho, el
  tamaño de la columna) en `scratch/videos/revision/landing-panel-v1/`. Los títulos se leen a 560 px; la letra
  del panel es chica pero la cámara la agranda en lo que importa (nombres de voz, botones, KPI). Corregido en el
  camino: el cursor del momento 1 hacía click en "Probar" en vez de "Voz y canales" y el del momento 4 en
  "Llamame"; las tarjetas de voz tapaban la vista previa; el modal de la llamada se cortaba arriba; el gráfico
  quedaba cortado a la derecha; la línea de transferencias tenía otra escala que las barras (ahora la misma).
- Primer cuadro y último cuadro (render de Remotion) blancos puros (255): el loop empalma.
- `make video-revisar` no aplica: sin audio, `revisar.py` falla al medir el volumen (las hojas se hicieron con ffmpeg).
- Ningún texto con signos de exclamación.

## A revisar antes de mostrarlo afuera

- **"Hablarle ahora" (Inicio y la llamada por el navegador) está hecho pero sin desplegar** (PRIMERA_VEZ.md,
  30-oct-2026). Publicar el video cuando esté en producción, o cambiar el momento 4 por la pestaña Probar del agente.
- **Ilustrativo:** todos los números de Reportes, nombres, teléfonos, URL, respuesta de la herramienta, horario y
  la conversación. Los retratos en las personas del equipo no existen en el panel real.
- Herramientas y Equipo dependen del plan.
