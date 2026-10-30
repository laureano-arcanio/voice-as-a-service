Estado: borrador

# Landing: el agente resuelve y deriva lo importante, v1

## Pedido

> quiero hacer un nuevo video, no en el mismo que este. Para usar en la landing. formato horizontal. El fondo es
> siempre blanco. Inicia en blanco todo. Luego aparece en el centro el logo, con el circulo de puntos simulando un
> loop de agente/progreso/espera. Luego aparecen clientes a la izquierda, que envian mensages al agente, estos
> mensajes giran en el circulo central en la medida que van entrando. Los clientes aparecen de arriba hacia abajo,
> distintas personas, medios y "consultas" es decir que se entienda que quieren diferentes cosas. luego aparece el
> operarrio, la persona humana en la transferencia, solo algunos mensajes le llegan y los vuelve a mandar a su
> cliente. que se entienda que el agente solo deriva lo que importante.

## Qué es

Primera versión. Un solo plano de 27,6 s (828 cuadros a 30 fps), 1920 × 1080, fondo blanco, sin audio. Guion y
tiempos en el README del proyecto.

## Archivos

| Archivo | Para qué | Tamaño |
|---|---|---|
| `landing-agente-v1.mp4` | Máster (H.264, CRF 18, sin pista de audio) | 2,3 MB |
| `web/landing-agente-1080.mp4` | Web, 1920 × 1080, H.264 CRF 26, `faststart`, sin audio | 1,2 MB |
| `web/landing-agente-720.mp4` | Web, 1280 × 720, ídem | 0,7 MB |
| `web/landing-agente-720.webm` | Web, 1280 × 720, VP9 CRF 42, sin audio | 0,7 MB |
| `web/landing-agente-poster.jpg` / `.webp` | Póster: el cuadro de 2,4 s (logo, aro y "Atentina") | 31 KB / 13 KB |

Las versiones web y el póster salen del máster con ffmpeg (comandos abajo). Los MP4 no se versionan; el WebM y los
pósters, tampoco hace falta (se regeneran).

```bash
cd marketing/videos/proyectos/landing-agente/versiones/v1
ffmpeg -i landing-agente-v1.mp4 -an -c:v libx264 -preset slow -crf 26 -pix_fmt yuv420p -movflags +faststart web/landing-agente-1080.mp4
ffmpeg -i landing-agente-v1.mp4 -an -vf scale=1280:-2 -c:v libx264 -preset slow -crf 26 -pix_fmt yuv420p -movflags +faststart web/landing-agente-720.mp4
ffmpeg -i landing-agente-v1.mp4 -an -vf scale=1280:-2 -c:v libvpx-vp9 -crf 42 -b:v 0 -row-mt 1 web/landing-agente-720.webm
ffmpeg -ss 2.4 -i landing-agente-v1.mp4 -frames:v 1 -q:v 3 web/landing-agente-poster.jpg
```

## Locución

Ninguna (pedido para la landing, que reproduce silenciado). No se usó el TTS ni el STT.

## Controles

- `npx tsc --noEmit` sin errores.
- Cuadros de prueba en `scratch/videos/landing-agente/` (2,4 · 5,5 · 7,2 · 9,0 · 12,4 · 14,6 · 17,6 · 21,0 s) y
  hojas de cuadros (uno por segundo) en `scratch/videos/revision/landing-agente-v1/`: sin textos cortados ni
  superposiciones. Se corrigió en el camino: los títulos pasaron arriba a la derecha (un paquete pasaba sobre el
  texto), el panel de Lucía se ensanchó (el detalle se partía) y las derivadas esperan menos en el aro.
- El primer y el último cuadro son blancos puros (255): el loop empalma.
- `make video-revisar` no aplica: no hay audio que medir ni transcribir (las hojas se hicieron con ffmpeg).

## A revisar antes de mostrarlo afuera

- **Ilustrativo:** personas, consultas, respuestas, precios, "Lucía" y el contador (8 · 2 cuenta lo que se ve, no
  es un dato medido).
- **Tamaño de los textos en la landing:** a ~960 px de ancho en pantalla, las consultas (25 px en el original) se
  ven a ~12 px; se leen, pero en mobile no. Para mobile convendría una versión vertical o no mostrarlo.
