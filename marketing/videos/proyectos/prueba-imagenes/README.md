# Prueba de imágenes generadas (pipeline video + Qwen-Image-2.1)

- **Pedido (21-nov-2026, Laureano):** "produci un video de prueba con imagenes, de atentina." Es la prueba de punta a punta
  del pipeline recuperado: API de imágenes local (`make imagenes-up`) → `make video-imagen` → escenas de Remotion → render.
- **Público:** nadie; es material interno de prueba. No se publica ni se cierra.
- **Mensaje:** el mismo de la marca (el agente atiende, deriva y registra), con copy real de la landing.
- **Formato:** 16:9, 1920×1080, 30 fps, 21,8 s. Sin locución (prueba de imágenes; el TTS del entorno está apagado),
  con la música determinística de `make video-musica` (mezclada a `musicVolume` 0,75, ver NOTAS de v1).
- **Escenas:** intro en blanco (logo + rótulo), tres escenas con una imagen generada a sangre cada una
  (dos `foto` de día y una `marca`), cierre en blanco con logo y contacto.

## Afirmaciones y de dónde salen

| Afirmación | Fuente |
|---|---|
| Atiende teléfono, WhatsApp y web | Canales de la plataforma (`docs/ARQUITECTURA.md`) |
| "Lo importante le llega a tu equipo" | Derivaciones ([`docs/features/EQUIPO_TELEFONIA.md`](../../../docs/features/EQUIPO_TELEFONIA.md)) |
| "Todo queda registrado" | Conversaciones, transcripción y resultado en el panel (`docs/features/REPORTES.md`) |
| `atentina.com.ar` / 0800-220-1233 | `landing/src/data/site.ts` (los mismos del cierre de `atencion-punta-a-punta`) |

## Imágenes

Generadas con `make video-imagen` (API local, Qwen-Image-2.1); prompts, semillas y tiempos en
[`imagenes.json`](imagenes.json).

| Archivo | Escena | Estilo |
|---|---|---|
| `img/01-cafe.png` | mostrador de café de día, celular arriba | `foto` 16:9 |
| `img/02-oficina.png` | oficina luminosa, dos personas y notebook | `foto` 16:9 |
| `img/03-marca.png` | placa de marca: aro de puntos y tres barras | `marca` 16:9 |

## Versiones

| Versión | Fecha | Duración | Qué es | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 21-nov-2026 | 21,8 s | Primera prueba del pipeline | borrador |
