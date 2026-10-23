# Primeros pasos (tutorial vertical)

Video para un cliente nuevo: cómo crear un agente básico y probarlo con una llamada desde el navegador.
Versión **v2**, reescrita desde cero (no se leyó ni se reutilizó la v1; la fuente de la v1 quedó cerrada en
`versiones/v1/`).

## Pedido

> Crea un nuevo video, v2. No utilizes la v1 ni la leas. Crea desde cero.
> Crea un nuevo video sobre como crear un Agente basico como cliente.
> - formato vertical para mobiles
> - Voz por defecto (1 sola)
> - zoom in cuando escriba (sin abusar del recurso)
> - Empieza con gracias por probar Atentina, te cuento como empezar.
> - que explique los pasos a seguir y como hacer una llamada de prueba desde la web.

## Público y mensaje

Cliente que acaba de entrar al panel y quiere escuchar al agente antes de contratar un número.
Mensaje: crear el agente es un formulario corto y la prueba se hace desde el navegador, sin teléfono.

Formato 1080 × 1920 (9:16), ~60 s, una sola voz (`paula`) y música propia. Pensado para verse en el celular.

## Guion

| Escena | Voz | Qué se dice | Qué se ve |
|---|---|---|---|
| `intro` | t1 | Gracias por probar Atentina, te cuento cómo empezar. | Fondo oscuro, logo y título; se funde sobre la siguiente. |
| `agentes` | t2 | Entrá al panel, abrí Agentes y tocá Nuevo agente. | Panel en el teléfono: Agentes, estado vacío y botón Nuevo agente; click. |
| `nombre` | t3 | Ponele un nombre, por ejemplo, Atención al cliente. Elegí Asistente básico y creá el agente. | Modal Nuevo agente; se escribe el nombre (zoom de cámara al escribir), Asistente básico seleccionado y click en Crear agente. |
| `definicion` | t4 | Se abre la definición. Completá el rol, el objetivo y la apertura. La voz ya viene elegida y la podés cambiar. | Formulario: Agente, Voz (Sofía), Objetivo y apertura, Reglas y Base de conocimiento. |
| `guardar` | t5 | Guardá. Cada cambio queda como una versión nueva. | Pestaña Versiones; click en Guardar, aviso y v2 en el historial. |
| `probar` | t6 | Para probarlo, abrí la pestaña Probar y activá Modo prueba. | Pestaña Probar: conversación por texto y Llamada con este agente; se activa el switch. |
| `enlace` | t7 | No hace falta un teléfono. Tocá Crear llamada de prueba y abrí el link que aparece. | Click en Crear llamada de prueba; alerta con el link Conectate acá para hablar con el agente. |
| `llamada` | t8 | Te conecta por el navegador. Hablá como si fueras un cliente: el agente te escucha y te responde con su voz. | Llamada en el navegador: Sofía, timer, onda, dos mensajes y controles de micrófono y colgar. |
| `cierre` | t9 | Cuando esté listo, asignalo a tu número desde Mi cuenta. Gracias por probar Atentina. | Fondo oscuro, logo, app.atentina.com.ar y cierre. |

## Afirmaciones y fuentes

- **El cliente crea y edita sus agentes. Para que atienda, elige el agente del número en Mi cuenta.**
  [`docs/GUIA_UI.md`, "Agentes (cliente)"](../../../../docs/GUIA_UI.md#agentes-cliente).
- **"Asistente básico" y la voz `sofia` por defecto.** `web/src/features/agents/NewAgentModal.tsx` y
  [`app/agents/templates/asistente.json`](../../../../app/agents/templates/asistente.json).
- **Guardar crea una versión nueva; las llamadas en curso siguen con la suya.**
  [`docs/GUIA_UI.md`, "Crear el agente"](../../../../docs/GUIA_UI.md#3-crear-el-agente-agentes).
- **Modo prueba, "Crear llamada de prueba" y el link de una sola vez.**
  `web/src/features/calls/NewCallForm.tsx` (`HINT_TEST`, `CallStartedAlert`) y `TestTab.tsx`.
- **Dominio del panel.** `app.atentina.com.ar` ([`AGENTS.md`](../../../../AGENTS.md)).
- **Sin cifras de latencia ni capacidad:** el video no promete tiempos ni llamadas simultáneas.

**Ilustrativo:** el nombre "Atención al cliente", los textos de rol, objetivo, apertura y base, las fechas de las
versiones, la pantalla de la llamada y su diálogo. Las pantallas son una recreación de la UI (no capturas) y el
link de la llamada de prueba no muestra la URL de LiveKit. La lista de voces muestra tres del catálogo real.

## Decisiones

- **Voz única:** `paula` (narradora por defecto), sin contrapuntos, como pidió el usuario.
- **Zoom al escribir:** un solo push-in del 10 % en la escena del nombre, mientras se tipea; no se repite.
- **Desde cero:** guion, escenas y componentes nuevos; no se consultó el código ni el guion de la v1.
- **Audio:** locución con 4 tomas por línea y la más fiel; música generada con `scripts/musica.py`.

## Versiones

| Versión | Estado | Qué cambió |
|---|---|---|
| v1 | cerrada | Versión anterior del tutorial. Su fuente está en `versiones/v1/`. |
| v2 | borrador | Recreación completa desde cero: guion nuevo, escenas nuevas, voz única `paula` y zoom al escribir. |

## Controles

- `npx tsc --noEmit` sin errores.
- Cuadros de cada escena revisados en `scratch/videos/pp2/` (textos sin cortes ni superposiciones).
- Render final: 59,7 s, 5,4 MB, **−17,0 LUFS** (referencia −16 ± 1,5).
- `make video-revisar` con transcripción por tramo: las nueve líneas se entienden. El STT escribe "a Tentina"
  por "Atentina" (t1 y t9) y confunde "crea el agente" con "crea a la gente" en la mezcla de t3; las tomas
  limpias dicen el texto correcto.
