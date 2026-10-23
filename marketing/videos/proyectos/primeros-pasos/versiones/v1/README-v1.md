# Primeros pasos: crear un agente y probarlo

- **Pedido (23-oct-2026, Laureano, textual):** "Crea un nuevo video sobre como crear un Agente basico como
  cliente. - formato vertical para mobiles - Voz por defecto (1 sola) - zoom in cuando escriba (sin abusar del
  recurso) - Empieza con gracias por probar Atentina, te cuento como empezar. - que explique los pasos a seguir
  y como hacer una llamada de prueba desde la web."
- **Público:** un cliente que acaba de registrarse y abre el panel por primera vez (dueño o responsable de
  atención), en el celular.
- **Mensaje:** en pocos pasos creás un agente con el asistente básico, le ponés voz, apertura y lo que sabe, y lo
  probás con una llamada desde el navegador, sin teléfono.
- **Formato:** 1080 × 1920 (9:16), 30 fps, 69,8 s. Composición `primeros-pasos` (`src/Video.tsx`). Una sola voz:
  `paula`. El panel se recrea a 390 px de ancho y se agranda con un zoom suave en los tres momentos de tipeo
  (nombre, apertura y base de conocimiento).

## Guion (v1)

| Escena | Tiempo | Locución | Qué se ve |
|---|---|---|---|
| `intro` | 0–4,8 s | p1 | Pantalla oscura: logo, "PRIMEROS PASOS", "Gracias por probar Atentina. **Te cuento cómo empezar.**"; subtítulo "Creá tu agente y probalo con una llamada desde el navegador" |
| `agentes` | 4,2–9,9 s | p2 | Panel en el celular, menú lateral: se toca **Agentes** y después **Nuevo agente**; la lista vacía dice "No tenés agentes activos" |
| `nuevo` | 9,9–16,2 s | p3 | Modal **Nuevo agente**: se escribe el nombre (zoom al tipear), se elige **Asistente básico** y se toca **Crear agente** |
| `voz` | 16,2–23,2 s | p4 | Aviso "Agente Atención al cliente creado"; en **Definición · Voz** se elige **Sofía**, se ve la grilla de voces con los filtros Todas / Mujeres / Hombres y se reproduce la **Prueba de voz** |
| `apertura` | 23,2–28,4 s | p5 | **Objetivo y apertura**: se reemplaza la apertura de la plantilla por la de un negocio (zoom al tipear); se ven "Pregenerar el audio de la apertura" y "Espera antes de la apertura" |
| `conocimiento` | 28,4–37,3 s | p6 | **Base de conocimiento**: se escribe lo que el agente sabe (horarios, dirección, envíos, cambios; zoom al tipear) y abajo **Datos a obtener**, con el dato "Consulta" |
| `guardar` | 37,3–41,8 s | p7 | Barra de la definición: "Cambios sin guardar" → **Guardar versión nueva**; el aviso dice "Versión 2 guardada" y el encabezado pasa a `v2` |
| `probar` | 41,8–48,4 s | p8 | Pestaña **Probar**: se activa **Modo prueba**, se toca **Crear llamada de prueba** y aparece el aviso con el link "Conectate acá para hablar con el agente" |
| `llamada` | 48,4–56,8 s | p9 | El link abre una pantalla genérica de llamada: el agente conecta, se permite el micrófono y se habla con él; se ve el intercambio sobre el horario de atención |
| `conversaciones` | 56,8–62,5 s | p10 | **Conversaciones**: la llamada de prueba con origen "Prueba", resultado "Consulta resuelta", fecha y la transcripción completa |
| `cierre` | 62,5–69,8 s | p11 | Pantalla oscura: "Ajustalo y probalo las veces que quieras", los cuatro pasos del video y el logo con atentina.com.ar · hola@atentina.com.ar |

Locución en [`guion.json`](guion.json): solo `paula`, sin voz secundaria (pedido). Velocidad 1×; `ganancia_db`
−1,5 para que la mezcla quede en −16 LUFS.

## Afirmaciones y de dónde salen

- **Nombres, campos y botones del panel:** se copiaron de la vista de cliente de `web/`: `AgentsPage`,
  `NewAgentModal`, `AgentDetailPage`, `DefinitionTab`, `DefinitionForm`, `VoiceSelect`, `VoicePreview`,
  `TestTab`, `NewCallForm` y `CallDetailPage`. La recreación está en `src/panel.tsx` y `src/escenas.tsx`.
- **Asistente básico:** es la plantilla `asistente` del cliente (`app/agents/templates/asistente.json`); el
  texto de la tarjeta es su `objective`.
- **41 voces, 28 mujeres y 13 hombres:** catálogo del TTS vigente (`tts/finetune/voces.tsv`, `AGENTS.md`) y los
  contadores de `VoiceSelect`; la grilla muestra seis para que entren en la pantalla.
- **Modo prueba y llamada de prueba:** `NewCallForm` (`web/src/features/calls/NewCallForm.tsx`): sin teléfono,
  "te conectás por navegador y hacés de interesado", y el aviso con `join_url` ("Abrilo ahora: el link no se
  vuelve a mostrar").
- **Guardar versión nueva y versiones:** `DefinitionTab` y `VersionsTab`; cada cambio es una versión nueva.
- **La llamada queda en Conversaciones:** `CallDetailPage`/lista de conversaciones, con transcripción.
- **Ilustrativo:** el cliente "Casa Norte" y sus datos (horarios, dirección, envíos, cambios), el nombre del
  agente ("Atención al cliente"), la fecha y hora de la conversación, y el intercambio de la llamada. La pantalla
  de la llamada es genérica, no imita la de LiveKit ni la de ningún navegador.
- **No se dicen cifras** de latencia, capacidad ni precios.

## Versiones

| Versión | Fecha | Duración | Qué cambió | Estado |
|---|---|---|---|---|
| [v1](versiones/v1/NOTAS.md) | 23-oct-2026 | 69,8 s | Primera versión | cerrada (23-10-2026) |
