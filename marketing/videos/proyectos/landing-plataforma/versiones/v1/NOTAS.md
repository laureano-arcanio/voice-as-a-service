# landing-plataforma v1

Estado: cerrada (30-10-2026)

- **Archivo:** `landing-plataforma-v1.mp4` (1920 × 1080, 30 fps, H.264 + AAC), 46,9 s, −15,2 LUFS, 5,4 MB.

## Pedido

> Una animación como la que hicimos para casos de uso (proyecto `atencion-punta-a-punta`), pero para la landing
> page. Abarcativa y general de los servicios que ofrecemos, bien orientada a ventas, sin detalles técnicos. El
> objetivo es mostrar rápidamente cómo funciona la plataforma y qué se puede hacer.

Unos 45 s (máximo 48) y, al final, una escena para desarrolladores con API y MCP (30-oct-2026).

## Qué tiene

Primera versión. Intro en blanco → la plataforma alrededor del agente (atiende, resuelve, llama, deriva, voces y
panel) → todo en uno → para desarrolladores (API y MCP) → cierre en blanco. Guion y fuentes en el
[README](../../README.md). Diagrama, `Avatar`, subtítulos, `Paquete`, aro, intro y cierre copiados de
`atencion-punta-a-punta`.

## Locución

`paula` (l1, l3, l5, l7, l9): 19,6 s; `gonzalo` (l2, l4, l6, l8): 19,7 s. `velocidad` 1,08, `ganancia_db` −1,5,
mejor de 4 tomas con fidelidad 1,00 en todas (l9, 0,85 por cómo el STT escribe "atentina.com.ar"). Grafías: `ápi`,
`M C P`. l6 se regeneró: la primera toma elegida decía "cuarenta y un a voces" (el STT del video oyó "41 a voces");
la nueva, "41 voces".

## Controles

- Cuadros de prueba de cada escena y hojas de `make video-revisar` (cada 2 s): empieza y termina en blanco; sin
  textos cortados ni tarjetas encimadas (en l6 lo de alrededor del agente se va antes de que entren las voces y la
  conversación).
- Volumen: −15,2 LUFS (−16 ± 1,5).
- Transcripción por tramo (`--tramos 0,4.4,9.6,14.0,19.1,23.0,29.6,36.2,42.0`): todas las líneas como el guion; el
  STT escribe "desarrollas" y "Conéctalo" (no distingue el voseo) y "Atentina.com.ar".
- Afirmaciones revisadas contra `site.ts`, los docs de cada función y `app/api/routers/` el 30-oct-2026.

## A revisar

- De oído: "cuarenta y una voces" (l6), "ápi" y "M C P" con `gonzalo` (l8; la grafía de MCP se probó con `paula`).
- MCP.md tiene pendiente "primera conexión OAuth real desde Claude.ai o Claude Code" aunque dice que Claude, ChatGPT,
  Claude Code y Cursor funcionan: la tarjeta nombra Claude y Cursor.
- Las llamadas salientes (campañas de voz) son de Sucursal y Red: va el aviso de plan en la escena.
- Datos ilustrativos: nombres, turno, pedido, motivos de las llamadas y la conversación con Lucía.
