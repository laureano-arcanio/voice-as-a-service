# Documentos de Atentina

Cómo hacemos los documentos profesionales (propuestas, overviews, one-pagers, fichas de producto, casos): la
plantilla, el tono, la estructura, los diagramas, el control de las afirmaciones, el PDF y las versiones. Lo usa el
agente [`documentos`](../.claude/agents/documentos.md). Los videos siguen [`VIDEOS.md`](VIDEOS.md).

## Dónde está

```text
marketing/documentos/
  plantilla/
    base.css               estilos de la marca para A4 (tokens de la landing, tipografías, componentes)
    plantilla.html         punto de partida con todos los bloques
    fonts/, marca/         fuentes locales y logos (copias de docs/brand/)
  proyectos/<slug>/
    README.md              pedido, destinatario, estructura, afirmaciones y su fuente, tabla de versiones
    versiones/vN/          documento.html (fuente), documento.pdf, vista-N.png (una por hoja), NOTAS.md
                           y, al cerrarla, fuente/base.css
    slides.css, slides.js  plantilla de presentaciones 16:9 (ver "Presentaciones")
  scripts/render.sh        HTML → PDF con Chrome + controles; scripts/cerrar.sh
  scripts/render-slides.sh una presentación → PDF 16:9 + una PNG por diapositiva
```

Proyecto de referencia: [`yoizen-propuesta`](../marketing/documentos/proyectos/yoizen-propuesta/README.md)
(propuesta de integración de 2 hojas, con diagrama).

| Paso | Comando |
|---|---|
| Imprimir y controlar | `make doc P=<slug> V=<n> [HOJAS=<máximo>]` |
| Presentación: imprimir y controlar | `make slides P=<slug> V=<n> [DIAPOS=<máximo>]` |
| Presentación: abrir para presentar | `make slides-abrir P=<slug> V=<n>` |
| Cerrar la versión | `make doc-cerrar P=<slug> V=<n>` |

## Cómo se hace un documento

1. **Pedido → README del proyecto** (`proyectos/<slug>/README.md`): el pedido textual, el destinatario y qué tiene
   que lograr el documento (que lo lleven a una reunión interna, que pidan un piloto, que entiendan el precio), el
   formato (hojas máximas) y el contexto (reunión, prospecto en [`mercado/`](../comercial/plan-salida-al-mercado.md)).
2. **Copiar la plantilla** a `versiones/v1/documento.html` (las rutas `../../../../plantilla/` funcionan desde ahí) y
   borrar los bloques que no se usen.
3. **Escribir:** primero el mensaje en una frase (el `h1`), después el resto.
4. **Verificar las afirmaciones** (ver abajo) y anotar la fuente de cada cifra en el README.
5. **`make doc`** y mirar las vistas (`vista-N.png`) a 110 dpi o más: textos que no entran, cajas que se tapan,
   el pie que pisa contenido. Ajustar espaciados en el HTML, no en `base.css`, salvo que el cambio sirva a todos.
6. **NOTAS.md** y la fila de la versión en el README; cerrar al entregar.

## Tono

Sigue [`DESIGN_GUIDELINE.md`](../docs/DESIGN_GUIDELINE.md), sección 10, adaptado a un documento de negocios:
- **Orientado a negocio:** qué gana el destinatario, qué tiene que hacer y qué cuesta, antes que cómo funciona por
  dentro. Lo técnico, solo si el pedido lo pide o en una línea ("por API").
- **Directo y concreto:** frases cortas, una idea por punto, con el énfasis en negrita al principio
  ("**Costos en dólares** y varios proveedores…"). Sin superlativos vacíos ni signos de exclamación.
- **Persona:** voseo para una persona o un negocio chico; con una empresa como destinatario, en tercera persona
  ("Yoizen conserva su plataforma") o "ustedes".
- **Honesto:** lo que no está desplegado o falta validar se dice ("en evaluación", "a medir en el piloto"); un límite
  conocido va en una nota (la de otros países en la propuesta de Yoizen).
- **Categoría:** agentes con IA que atienden a los clientes; la voz con acento argentino es el diferencial.

## Estructura que funciona (2 hojas A4)

- **Hoja 1, overview:** encabezado (logo, tipo de documento, destinatario, fecha) → rótulo + `h1` con el remate en
  el acento → párrafo de entrada → cuatro cifras → el problema frente a lo que aporta Atentina → diagrama con una
  línea de explicación.
- **Hoja 2, propuesta:** opciones o formas de trabajar (tarjetas numeradas, cada una con un ejemplo concreto) → qué
  gana → quién hace qué → próximos pasos (los acordados, en orden) → nota honesta → pie de contacto.
- Un documento de 1 hoja recorta: hero, tres cifras, tres puntos, próximos pasos y contacto.

## Componentes (`base.css`)

| Clase | Para qué |
|---|---|
| `.page` | Una hoja A4 (210 × 297 mm), con su padding; el contenido no puede pasar del pie |
| `header`, `.meta` | Logo a la izquierda; tipo de documento, destinatario y fecha en mono a la derecha |
| `.eyebrow`, `h1 .accent`, `.lead` | Rótulo en mono, título con remate y entrada |
| `.stats > .stat` | Cuatro cifras: el número en Bricolage con el acento y qué mide en palabras simples |
| `.two`, `ul`, `ul.warn` | Dos columnas de puntos; `warn` con viñeta naranja para problemas |
| `.diagram`, `.caption` | Caja del diagrama (SVG inline) y su explicación |
| `.cards > .card` (`.num`, `.ej`) | Opciones numeradas, con un ejemplo al pie |
| `.ops` (`.ours`, `.theirs`) | Quién hace qué, con tildes |
| `.steps > .step` | Próximos pasos numerados |
| `.note` | Aclaración o límite |
| `footer.contact` (`.tag`, `.who`, `.data`) | Pie oscuro con logo blanco, frase, contacto y datos |
| `.pagefoot` | Pie chico de las hojas sin `footer.contact` |

## Presentaciones

Para compartir pantalla en una videollamada (la primera: [`yoizen-tu-propio-agente`](../marketing/documentos/proyectos/yoizen-tu-propio-agente/README.md)).
Mismo proyecto, README, versiones y controles que un documento; cambia la plantilla:
- **`plantilla/slides.css` + `slides.js`:** una `section.slide` de 1920 × 1080 por diapositiva (`.top` con logo y rótulo,
  `.body`, `.foot` con el contador `<span class="n" data-total="N">`), `.dark` para portada y cierre. En el navegador
  muestra una por pantalla, escalada a la ventana (flechas, espacio, Home/End, F pantalla completa, `#n` en la URL);
  impresa con Chrome, una página 16:9 por diapositiva (`@page 508mm 285.75mm`).
- **Componentes:** `.cols.two/.three/.wide/.code`, `.card` (`.ours`, `.soft`, `.accent-bg`), `ul.check` (`.theirs`),
  `.pill`, `pre.code` (código sobre `ink`, con `.k`, `.s`, `.c`, `.hl` y `.label`), `.diagram`, `.steps`, `.note`,
  `.contact` y `.compact` para achicar una columna.
- **Para una charla en vivo:** pocas palabras y tipografía grande (cuerpo 34 px, títulos 56 a 64 px), una idea por
  diapositiva, el remate en el acento; quien presenta habla y la diapositiva acompaña. Las notas del presentador
  (2 a 5 líneas por diapositiva, con las objeciones esperables) van en `NOTAS.md`, no impresas.
- **Controles:** `make slides ... DIAPOS=<máximo>` falla si hay más diapositivas, si alguna página no es 16:9 (un
  desborde agrega páginas) o si una fuente no es de la marca. Plex Mono latin no tiene "→" (U+2192): no usar flechas
  en los rótulos en mono. Mirar las `vista-NN.png` (1920 × 1080) y una captura del modo pantalla.
- Cerrar la versión guarda `slides.css` y `slides.js` en `fuente/`.

## Diagramas

- **SVG inline** dentro de `.diagram`, `viewBox` de ~720 de ancho, con `font-family` de la marca y los colores de los
  tokens: lo nuestro con borde y fondo de acento (`#2456e6`, `#eaf0ff`); lo del cliente, neutro (`#cbd5e1`,
  `#f1f4f9`).
- Flechas con `<marker>`; las etiquetas que cruzan una línea llevan halo
  (`stroke="#fff" stroke-width="4" paint-order="stroke"`).
- Pocas cajas y palabras de negocio ("Entiende lo que dicen", "Habla"), no nombres de componentes.

## Imágenes

- **Vistas de las hojas:** `render.sh` deja `vista-N.png` a 80 dpi; para una imagen de mejor calidad,
  `pdftoppm -r 200 -png documento.pdf <prefijo>`.
- **Una pieza suelta (imagen para redes o mail):** HTML de una sola `.page` con el tamaño que haga falta y
  `google-chrome --headless=new --screenshot=<archivo>.png --window-size=<ancho>,<alto> file://...`.
- **Capturas del panel:** solo con datos de demo, desde el backend de desarrollo (:8111) y Vite, con los scripts
  de `scratch/shots/`. Nunca datos de clientes reales.

## Afirmaciones

Mismas reglas que los videos ([`VIDEOS.md`](VIDEOS.md), "Afirmaciones"): estado de cada función en AGENTS.md y su
plan; latencia de llamadas reales (consulta en VIDEOS.md); capacidad solo con un CAP vigente; nada de logos ni
pantallas de terceros. Además:
- **Precios y planes:** de la base (`tiers.price_ars`) o de la landing (`landing/src/data/site.ts`), con la fecha.
- **"Propio":** la inferencia y los servidores son propios; la telefonía es de Anura (decir "4 en 1", no "100 % propio").
- **Promesas comerciales** (piloto sin costo, plazos): solo las que hizo Laureano; anotarlas en el README como "a
  validar".

## Contacto (siempre al pie)

De `landing/src/data/site.ts` (verificarlo antes de cada documento):
- **0800-220-1233** (lo atiende el agente comercial);
- **atentina.com.ar** y **hola@atentina.com.ar**;
- **WhatsApp +54 9 351 700-2592**;
- contacto: **Laureano Arcanio**.

## Controles antes de entregar

1. `make doc ... HOJAS=<máximo>` falla si hay más hojas o si una fuente no es de la marca (si Chrome no encuentra
   una fuente, cae a una del sistema).
2. Mirar cada vista: nada cortado ni tapado por el pie, diagramas legibles, cifras con su unidad.
3. Afirmaciones del README revisadas; contacto igual al de `site.ts`; fecha del encabezado.
4. El texto del PDF se puede copiar (`pdftotext documento.pdf -`): los links y el 0800 tienen que estar como texto.

## Versiones

- Cada entrega es una versión: `versiones/vN/` con `documento.html`, `documento.pdf`, las vistas y `NOTAS.md`
  (`Estado: borrador` o `Estado: cerrada (fecha)`, el pedido textual, qué cambió y los controles).
- Un borrador se puede volver a imprimir. **Cerrar** (`make doc-cerrar`) copia `base.css` a `fuente/` y congela el
  PDF: `make doc` ya no la pisa y un cambio es una versión nueva (copiar `documento.html` de la anterior).
- El PDF y las vistas se versionan en git (pesan poco).
