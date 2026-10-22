# Videos de Atentina

Cómo hacemos los videos animados con locución de nuestro propio TTS: estructura, mensaje y tono, estilo visual,
voces, música, control de las afirmaciones, revisión y versiones. Lo usa el agente
[`videos`](../.claude/agents/videos.md). Los documentos (PDF) siguen [`DOCUMENTOS.md`](DOCUMENTOS.md).

## Dónde está

`marketing/videos/` es un proyecto de [Remotion](https://www.remotion.dev) (React → MP4) con un proyecto por video:

```text
marketing/videos/
  src/Root.tsx              una <Composition> por proyecto, con id = carpeta del proyecto
  src/comun/                lo compartido: theme.ts (tokens y fuentes), ui.tsx (títulos, tarjetas, píldoras,
                            íconos, globos, onda), characters.tsx (personajes y el agente con el logo), code.tsx (ventana de
                            código y de pedidos HTTP), montaje.tsx (escenas, fundidos, locución y música)
  proyectos/<slug>/
    README.md               pedido, público, mensaje, guion por escena, afirmaciones y tabla de versiones
    guion.json              locución: {nota, musica_segundos, lineas: [{id, voz, texto}]}
    src/                    timeline.ts (duración de escenas y momentos de cada voz), escenas y Video.tsx
    versiones/vN/           <slug>-vN.mp4, NOTAS.md y, al cerrarla, fuente/ (código, guion y locución)
  public/                   fonts/, marca/ (logos) y proyectos/<slug>/{vo/, musica.wav}
  scripts/                  voces.py, musica.py, candidatas.py, revisar.py, cerrar.sh
```

Proyectos hoy: [`general`](../marketing/videos/proyectos/general/README.md) (el video de Atentina para empresas),
[`yoizen`](../marketing/videos/proyectos/yoizen/README.md) (técnico, para integradores),
[`transcripcion`](../marketing/videos/proyectos/transcripcion/README.md) (transcripción y voz para call centers) y
[`goldman`](../marketing/videos/proyectos/goldman/README.md) (propuesta para un prospecto: Isaías Goldman SA).

## Comandos

| Paso | Comando |
|---|---|
| Instalar (una vez) | `make video-setup` |
| Ver y ajustar en vivo | `make video-studio` |
| Locución (mejor de N tomas) | `make video-voces P=<slug> [IDS="n1 n3"] [TOMAS=4]` |
| Música | `make video-musica P=<slug> [SEG=<s>]` (sin SEG, `musica_segundos` del guion) |
| Render de una versión | `make video P=<slug> V=<n>` |
| Revisión | `make video-revisar P=<slug> V=<n> [ARGS="--tramos 0,6.2,11.4"]` |
| Cerrar la versión | `make video-cerrar P=<slug> V=<n>` |
| Un cuadro suelto | `cd marketing/videos && npx remotion still <slug> ../../scratch/videos/x.png --frame=N --scale=0.5` |

Los cuadros de prueba, hojas de revisión y tomas candidatas van a `scratch/videos/`.

## Cómo se hace un video

1. **Pedido → README del proyecto.** Carpeta `proyectos/<slug>/` (slug corto, en minúscula) con el README: pedido
   textual, público, mensaje en una frase, formato y duración, y el contexto (reunión, prospecto, landing).
2. **Guion.** Tabla de escenas: qué dice la locución y qué se ve. 5 a 13 s por escena; una idea por escena; el
   título de pantalla resume la escena aunque el video se vea sin sonido.
3. **Afirmaciones.** Antes de escribir una cifra o una función, verificarla (ver "Afirmaciones") y anotar la fuente
   en el README.
4. **Locución.** `guion.json` y `make video-voces`. Las duraciones salen de los WAV y fijan el largo de las escenas.
5. **Escenas.** En `proyectos/<slug>/src/`, con los componentes de `src/comun/`. `timeline.ts` define las escenas
   (`armarEscenas`) y cuándo arranca cada voz; `Video.tsx` usa `<Montaje>`. Registrar la composición en `Root.tsx`.
6. **Cuadros de prueba** de cada escena (`npx remotion still`) y corregir textos cortados o superpuestos.
7. **Render, revisión y notas** (ver "Controles" y "Versiones").

## Mensaje y tono

Sigue [`DESIGN_GUIDELINE.md`](DESIGN_GUIDELINE.md), sección 10:
- **Español rioplatense con voseo** para empresas ("atiende por vos", "programás la campaña"); con un destinatario
  plural concreto, "ustedes" (video de Yoizen).
- **Categoría:** agentes con IA que atienden a tus clientes. La voz y los canales son la prueba, no la categoría.
  En material para integradores, "agente de voz" está bien porque es lo que integran.
- **Directo y concreto, sin superlativos vacíos ni signos de exclamación** en el texto de pantalla. El diálogo de los
  videos actuales los tiene ("¡Hola, Carolina!", "¡Listo!"): sacarlos en la próxima versión.
- **Estructura de los títulos:** rótulo en mono (`EL PROBLEMA`, `CÓMO VIAJA LA VOZ`) + frase en Bricolage 800 con
  el remate en el acento ("Cada llamada sin atender es un cliente que se va **con la competencia.**").
- **Arco que funciona** (video general): problema → solución → cómo funciona → para desarrolladores → más
  funciones → panel → cierre con la marca. Para integradores: arquitectura → cada API con su caso → datos →
  modelo de operación.
- **Ejemplos genéricos**, no de un rubro, salvo que el pedido sea de un rubro (se cambió "turnos" por una consulta
  de atención en `general` v2).

## Estilo visual

- **Tokens y tipografías** de la landing (`src/comun/theme.ts`): fondo claro con grilla de puntos; acento `#2456e6`;
  Bricolage Grotesque 800 en títulos, Figtree en el resto, IBM Plex Mono en rótulos, rutas y cifras. Las fuentes
  se cargan locales (`public/fonts/`).
- **Fondo oscuro (`ink`)** solo para la intro y el cierre: logo blanco, frase con el remate en `accent-on-dark`.
- **Componentes** (`ui.tsx`, `code.tsx`): `Headline`, `Card`, `Pill`, `Bubble`, `Icon`, `Wave`, `CodeWindow` con
  `Typed` (código que se escribe, coloreado), `Link` (curva punteada que corre).
- **Personajes** (`characters.tsx`): bustos planos de estilo negocios, con el elenco fijo en `CAST` (cliente,
  cliente2, cliente3, dueña, integrador, otro) y poses `phone`, `texting`, `laptop`, `back`. Los personajes que
  hablan mueven la boca con la envolvente de su voz (`vo/envolventes.json`).
- **El agente de Atentina es el logo, no un robot** (decisión del usuario, 21-oct-2026): `AgenteLogo` dibuja la
  marca (aro y tres barras) en un círculo blanco, y las barras se mueven con su voz. La mascota con cuerpo
  (`Mascot`) no se usa más; queda en el código solo por los videos ya entregados (`general`, `yoizen`,
  `transcripcion` y `goldman` v1).
- **Movimiento:** `useCurrentFrame` + `interpolate`/`spring` (`useIn`, `usePop`). Nada de transiciones ni
  animaciones CSS: no se renderizan. Fundido de 8 cuadros entre escenas; la intro se funde 0,6 s sobre la primera.
- **Diagramas animados:** nodos en tarjetas, paquetes que viajan (onda = voz, "Aa" = texto, "{ }" = herramienta),
  el nodo activo se agranda y toma el acento. Que el paquete no vuelva sobre sus pasos y viaje a una velocidad que
  se pueda seguir (una respuesta viaja lo que dura su frase).
- **Velocidad como mensaje:** si algo es rápido, mostrarlo en tiempo real con un cronómetro y el dato medido (el
  tramo escucha → piensa → responde dura 0,9 s reales en `general`).

## Voces y pronunciación

El TTS es `vllm-tts` (Qwen3-TTS con 41 voces argentinas, [`TTS_FINETUNE.md`](TTS_FINETUNE.md); catálogo en
`tts/finetune/voces.tsv`). Se usa en vivo: pocos pedidos, sin reiniciarlo, y siempre con una voz del checkpoint
(sin `voice` se cae el engine).

| Papel | Voz | Por qué |
|---|---|---|
| Narrador | `lucas` | Hombre, WER 1,9 %, ritmo pausado (15,1 car/s) |
| Asistente (Atentina) | `valentina` | La de más variación de tono entre 14 voces de mujer (±2,8 semitonos; `sofia`, ±1,9) |
| Cliente | `carolina` | WER 1,8 %, distinta de la asistente |

- **Elegir una voz:** `python3 scripts/candidatas.py voces` genera la misma frase con varias voces y ordena por
  variación de tono (más variación, menos robótica). Las tomas quedan en `scratch/videos/candidatas/` para
  escucharlas: la decisión final es de oído.
- **Mejor de N tomas:** el TTS varía en cada toma. `make video-voces ... TOMAS=4` transcribe cada toma con nuestro
  STT y se queda con la más fiel al texto. Una fidelidad menor a 0,97 es para escuchar o regenerar.
- **Ortografía normal en la locución** (decisión del usuario, 21-oct-2026, después de escuchar `goldman` v2: las
  tildes forzadas en la sílaba tónica sonaban mal en general). Solo se fuerza una grafía puntual cuando el usuario
  la pide; esas van en la tabla. Para probar variantes, `scripts/candidatas.py` con un grupo propio y dos tomas por
  texto, y dejar las tomas para escuchar: el STT no distingue dónde cae el acento.
- **Velocidad:** `"velocidad": 1.1` en `guion.json` acelera cada línea con `ffmpeg atempo` (no cambia el tono)
  después de elegir la toma; las duraciones y envolventes salen del audio acelerado. Sin el campo, 1,0.
- **Grafías que funcionan:**

| Se dice | Se escribe en `guion.json` | Nota |
|---|---|---|
| API (como en español, "ápi") | `ápi` | Decisión del 20-oct-2026; "ei-pi-ai" sonaba mal |
| JSON (en inglés) | `yéison` | |
| OpenAI (en inglés) | `ópen, ei, ái` | Con comas; regenerar si el STT oye "Open LI" |
| Nombres que el TTS dice mal | no decirlos | "Yóisen" salió "Joyce": el nombre va escrito en pantalla |
| Números y horas | en palabras | "a las diez", no "10:00" |
| clasifica | `clasifíca` | Pedido del usuario (goldman v3) |
| Goldman | `Goldman` | Sin tilde: con `Góldman` el STT oyó "Colman" en una de dos tomas |
| Pausas | con puntuación | Comas y puntos marcan las pausas ("Actualmente, un solo número…") |

- **El STT no distingue "voz" de "vos":** esa diferencia en la transcripción no es un error de la toma.

## Música

`scripts/musica.py` sintetiza un pad suave con arpegio y bajo (sin licencias de terceros). Es determinística:
el WAV no se versiona y `make video` la genera si falta. `musica_segundos` del guion tiene que cubrir el video.
La mezcla (`montaje.tsx`) la deja en 0,32 sin voz y 0,12 debajo de la voz; el video queda en ~−16 LUFS.

## Afirmaciones

Lo que se dice o se muestra tiene que ser verdad hoy. Antes de poner una cifra o una función:
- **Estado de cada función:** [`AGENTS.md`](../AGENTS.md) y el plan de cada una dicen si está desplegada. Si no lo
  está, no se presenta como disponible: se marca ("en evaluación") o se avisa en el README y en el mensaje final.
- **Latencia:** la medida en llamadas reales. Consulta de solo lectura:

  ```bash
  docker compose exec -T db psql -U aiva_validate -d aiva_validate -At -c "with t as (select (x->>'total')::float tot
    from call_logs, jsonb_array_elements(latency->'turns') x where created_at > '<desde>' and latency ? 'turns')
    select count(*), percentile_cont(0.5) within group (order by tot), avg((tot<1)::int), avg((tot<1.5)::int) from t"
  ```

  `total` = fin de la frase + LLM + TTS (`app/voice/latency.py`). No incluye la consulta a un CRM o herramienta.
- **Capacidad:** solo lo medido en [`capacity/`](capacity/README.md) con la configuración vigente. Con Gemma no hay
  CAP: no poner "N llamadas simultáneas".
- **Tiempos de STT y TTS:** los de [`API_INFERENCIA.md`](API_INFERENCIA.md) y AGENTS.md son en el servidor; desde
  otra red se suma la ida y vuelta.
- **Rutas, campos y código** de la API: copiarlos de `app/api/` y `app/api/schemas.py`, recortados pero reales.
- **Ilustrativo** (números del panel, contactos, ids): se permite y se anota en el README. Nunca logos de terceros
  ni la interfaz de otra empresa imitada: su nombre va escrito y sus pantallas, genéricas.
- **Contacto:** 0800 y links de `landing/src/data/site.ts`.

## Controles antes de entregar

1. **Cuadros:** uno por escena en el momento más cargado; sin texto cortado (en ventanas de código, una línea en
   mono de 19 px entra hasta ~60 caracteres en 690 px), sin superposiciones ni tarjetas que tapen otras.
2. **`make video-revisar`:** duración, volumen integrado (−16 ± 1,5 LUFS), hojas de cuadros cada 2 s y la
   locución transcrita por tramo (con `--tramos` en los cortes de escena). Transcribir el video entero de una vez da
   errores que no están: hacerlo por tramos.
3. **Afirmaciones** del README revisadas contra el código y los datos del día.

## Versiones

- Cada render entregado es una versión: `proyectos/<slug>/versiones/vN/` con `<slug>-vN.mp4` y `NOTAS.md`. La
  primera línea del cuerpo de las notas es `Estado: borrador` o `Estado: cerrada (fecha)`.
- **NOTAS.md:** el pedido textual que la originó, qué cambió respecto de la anterior, la locución, los controles y
  lo que queda por revisar. Y una fila en la tabla de versiones del README del proyecto.
- **Borrador:** se puede volver a renderizar (`make video`) mientras se ajusta.
- **Cerrar** (`make video-cerrar`) copia el código, el guion y la locución a `vN/fuente/` y la congela; `make video`
  ya no la pisa. Se cierra al entregarla afuera o **antes de cambiar el código del proyecto para la versión
  siguiente**: el código del proyecto es uno solo y sin `fuente/` la versión anterior no se puede reproducir.
- Los MP4 no se versionan en git (pesan; se regeneran desde `fuente/`). El código, el guion, la locución, las
  notas y los README sí.

## Trampas

- **Hooks dentro de `map`:** está bien si la cantidad es fija (las listas de cada escena son constantes).
- **Rutas de `staticFile`:** relativas a `public/` (`proyectos/<slug>/vo/...`, `marca/...`).
- **La composición se llama como la carpeta del proyecto**; `make video P=<slug>` la busca por ese id.
- **La intro va última en el DOM** (`Montaje` lo hace) para quedar encima mientras se funde.
- **Duraciones:** `timeline.ts` importa `vo/duraciones.json`; si una locución nueva dura más que su escena, se
  pisa con la siguiente. Ajustar `LENS` después de regenerar voces.
