# Landing: el panel para configurar tu agente

Video corto, mudo y en loop para la sección de la home que explica que Atentina es una plataforma completa (agentes
con herramientas, derivación de llamadas y más). Va a la derecha del texto, en una columna de ~540 px al lado de una
lista de seis funciones (~780 px de alto): el panel recreado en cinco momentos, con cámara que hace zoom a lo que
importa, cursor que hace click y elementos con pop. Vertical 4:5 desde la v2.

## Pedido

> Un pequeño video a la derecha [de una sección nueva de la home] que muestre rápidamente y de forma muy
> marketinera cómo es el panel de administración para configurar.

Encargo (30-oct-2026): 1920 × 1080, 30 fps, 15 a 20 s, sin audio, empieza y termina en blanco para que el loop
empalme, sin subtítulos, un rótulo corto y grande por momento; recorrido: editor del agente con la voz, herramienta
"Consultar turnos" conectada a "Tu sistema", derivación al área Ventas con dos personas (retratos de valentina y
lucas), "Hablarle ahora" con subtítulos y reportes. Versión web en `landing/public/videos/landing-panel-v1.mp4`
con su poster.

## Público, mensaje y formato

- **Público:** quien entra a la home (empresas; no técnico).
- **Mensaje:** todo lo del agente se configura en un solo panel: voz, sistema, equipo, prueba y resultados.
- **Formato (v5):** 1080 × 1350 (4:5), 30 fps, 22,0 s, sin pista de audio, **sin texto** (desde la v5: arranca en
  el panel y muestra el recorrido; zoom 1,0–1,08 sobre la ventana entera, ver `versiones/v5/NOTAS.md`). Hasta la v4:
  20,0 s, con títulos. Composición `landing-panel`. Fondo
  blanco puro en todo el cuadro (va sin borde sobre la página): la ventana del panel no tiene sombra y los bordes
  del cuadro se funden a blanco. El título en una línea centrada (Bricolage 800, 62 px: ~31 px a 540 px de ancho)
  va arriba, y la ventana del panel (angosta y alta, con el contenido en una columna) ocupa el resto. Cada momento abre
  con la ventana entera y la cámara se acerca a 1,34–1,48. Entra con un fundido de 0,35 s sobre el anterior.
  La v1 era 1920 × 1080 con la ventana ancha (quedaba bajita en la columna).
- **Contexto:** `<video autoplay muted loop playsinline>` de la landing. La integración en la página la hace otra
  sesión; acá solo quedan los archivos en `landing/public/videos/`.

## Guion (v1 a v4; la v5 no tiene intro, cierre ni títulos, y los cinco momentos duran 4,2–4,8 s: ver `versiones/v5/NOTAS.md`)

| Tiempo | Pantalla del panel (recreada) | Qué pasa | Título |
|---|---|---|---|
| 0,0–1,9 | — | Blanco; entra el logo y la frase | Todo tu agente, **en un solo panel.** |
| 1,9–5,7 | Agente "Sofía", pestaña Conversación → Voz y canales (menú: Mis agentes) | Se escriben Nombre "Sofía" y Objetivo; click en "Voz y canales"; en la grilla de voces (Paula, Sofía, Carolina, Martín, Diego, Mateo, con retrato y género) click en Sofía; a la derecha, Sofía con su retrato y la prueba de voz que suena | Creás tu agente y **elegís la voz.** |
| 5,7–8,8 | Herramienta `consultar_turnos` (menú: Herramientas) | Nombre, "Qué hace y cuándo usarla", Método GET y URL; aparece "Tu sistema" unido a la URL; click en Probar: el pedido va a tu sistema y vuelve; "Funcionó · HTTP 200" y "Lo que recibe el agente" con los turnos libres | Lo conectás **a tu sistema.** |
| 8,8–11,9 | Equipo, modal "Editar área Ventas" (menú: Equipo) | Personas 1 Valentina y 2 Lucas con su teléfono; "A quién se llama primero": click de En orden a Rotativa (cambia la ayuda); Timbre por persona; Horario lunes a jueves 09:00 a 18:00 | Derivás **a tu equipo.** |
| 11,9–15,0 | Inicio (menú: Inicio), modal "Hablar con Sofía" | Tarjeta del agente; click en "Hablarle ahora"; modal con el retrato que late al hablar, estado "Sofía habla…" / "Te escucha…" y los subtítulos de la conversación; botón Cortar | Lo probás **en el momento.** |
| 15,0–18,0 | Reportes, pestaña Resumen (menú: Reportes) | "Consultas por día": barras apiladas que crecen (Teléfono entrante, WhatsApp, Web) y la línea de Transferencias pedidas; la cámara baja a los KPI que cuentan: Consultas 1.218, Objetivo cumplido 84 %, Transferidas 66 | Ves **los resultados.** |
| 18,0–19,85 | — | Blanco, logo y frase; se desvanece | Agentes con IA / que atienden / **a tus clientes.** |
| 19,85–20,0 | — | Blanco (empalma con el principio) | — |

## Afirmaciones y fuentes

Rótulos, pestañas, campos y botones copiados de `web/src` (30-oct-2026):

| Momento | Verificado en |
|---|---|
| Menú (Inicio, Reportes, Conversaciones, Agentes › Mis agentes, Herramientas, Voces; Canales › WhatsApp; Agenda › Equipo) | `web/src/components/nav.ts` (`CLIENT_NAV`; el video omite algunos ítems) |
| Pestañas del agente (Resumen, Conversación, Datos, Herramientas, Voz y canales, Modelo, Probar) | `features/agents/AgentTabs.tsx` (`TAB_META`; el video omite JSON, Versiones y Link para llamar) |
| Secciones "Agente" (Nombre, Rol, Idioma), "Objetivo y apertura" (Objetivo), "Voz" y su descripción | `features/agents/DefinitionForm.tsx` |
| Selector de voces: Todas/Mujeres/Hombres con cantidad, tarjetas con retrato, nombre y género, "Prueba de voz" | `features/voices/VoiceSelect.tsx`, `VoicePreview.tsx`, `names.ts`; 41 voces, 28 mujeres y 13 hombres (`tts/finetune/voces.tsv`) |
| Herramienta: título = slug, Nombre, "Qué hace y cuándo usarla", Método, URL, panel "Probar", "Funcionó", "HTTP 200", "Lo que recibe el agente"; `consultar_turnos` es el ejemplo del propio panel | `features/tools/ToolEditorPage.tsx`, `ToolForms.tsx`, `ToolTestPanel.tsx`; [`HERRAMIENTAS.md`](../../../../docs/features/HERRAMIENTAS.md) (en producción) |
| "Editar área Ventas": Nombre, Personas ("Se las llama en este orden…"), "A quién se llama primero" En orden / Rotativa con su ayuda, "Timbre por persona", Horario con franjas por día | `features/team/AreaModal.tsx`, `labels.ts`, `ScheduleFields.tsx`; [`EQUIPO_TELEFONIA.md`](../../../../docs/features/EQUIPO_TELEFONIA.md) (en producción) |
| Inicio: "Hola, …", "Tus agentes, listos para probar…", tarjeta con "Voz de …", "Hablarle ahora", "Llamame", "Editar", "Crear otro agente"; modal "Hablar con Sofía", "Sofía habla…", "Te escucha…", subtítulos, "Cortar" | `features/onboarding/HomePage.tsx`, `VoiceCallModal.tsx`; [`PRIMERA_VEZ.md`](../../../../docs/features/PRIMERA_VEZ.md): el doc dice "sin desplegar"; según el usuario (30-oct-2026) ya está en producción |
| Reportes: pestañas, "Consultas por día" con sus series, KPI "Consultas", "Objetivo cumplido", "Transferidas" con su subtítulo y "vs. período anterior" | `features/reports/ReportsPage.tsx`, `SummaryTab.tsx`, `parts.tsx`; [`REPORTES.md`](../../../../docs/features/REPORTES.md) (en producción). El pedido decía "resueltas y derivadas": se usaron los rótulos reales |

**Ilustrativo:** el agente "Sofía", el usuario "Ana", el rol y el objetivo, la URL `tusistema.com.ar`, el campo
`fecha` y la respuesta de la herramienta, los teléfonos de Valentina y Lucas, el horario, la conversación de prueba
y todos los números de Reportes (días, barras, KPI y variaciones). "Tu sistema" (el nodo con la línea punteada) no es
una pantalla del panel: muestra adónde se conecta la herramienta. Las personas del equipo no tienen retrato en el
panel (MemberPicker muestra nombre y teléfono): los retratos de valentina y lucas son del pedido. Las herramientas y
el equipo dependen del plan (`custom_tools`, `team`). Sin logos ni pantallas de terceros.

## Decisiones

- **Panel recreado, no capturas:** permite zoom nítido y animar cada elemento. La ventana es una sola (header con el
  logo, menú con el ítem activo de cada momento y el lienzo), con la cámara por momento (`Camara`, puntos clave de
  zoom y encuadre).
- **Título grande arriba, sin rótulo en mono:** a 540 px un rótulo de 24 px se vería a 12 px. La estructura queda en
  la frase, con el remate en el acento. En la v2 iba a 100 px en dos líneas: el usuario lo encontró demasiado grande
  (v3: 62 px, una línea).
- **Vertical (v2):** la columna de la home es alta (la lista de funciones mide ~780 px); en 4:5 la pantalla del
  panel ocupa casi todo el cuadro y el zoom deja el texto del panel en ~16–20 px a 540 px.
- **Sin audio:** `guion.json` sin líneas; `make video` genera `musica.wav` (ignorado por git) pero el video no la usa.

## Versiones

| Versión | Estado | Qué cambió |
|---|---|---|
| v1 | cerrada (30-10-2026) | Primera versión: 1920 × 1080, 20,0 s, sin audio, cinco momentos del panel; web en `landing/public/videos/landing-panel-v1.mp4` (2,4 MB) y poster |
| v2 | cerrada (30-10-2026) | Vertical 4:5 (1080 × 1350), mismos momentos y textos: ventana angosta con el contenido en una columna, cámara más cerca, títulos en dos líneas; web en `landing/public/videos/landing-panel-v2.mp4` (2,3 MB) y poster |
| v3 | cerrada (30-10-2026) | Títulos de 100 a 62 px en una línea (intro y cierre igual), más alto para el panel; fondo blanco puro sin sombra de ventana y bordes que se funden a blanco; web en `landing/public/videos/landing-panel-v3.mp4` (2,3 MB) y poster |
| v4 | cerrada (30-10-2026) | Sin el velo gris de los modales (se veía como un bloque gris en la página): velo blanco suave y modales con borde y sombra suave; web en `landing/public/videos/landing-panel-v4.mp4` (2,2 MB) y poster |
| v5 | borrador | Sin texto (ni títulos, ni intro, ni cierre): arranca en el panel con un fundido de 9 cuadros desde blanco; zoom 1,0–1,08 sobre la ventana entera; 22,0 s; web en `landing/public/videos/landing-panel-v5.mp4` (1,2 MB) y poster |
