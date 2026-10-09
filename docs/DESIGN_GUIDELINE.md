# Guía de diseño de Atentina

Cómo se ve y cómo habla la marca. La base es la landing (`landing/`): hub `/`, verticales
`/turnos`, `/cobranzas`, `/municipios` y páginas legales. Leerla antes de agregar o cambiar
cualquier pantalla de la landing. El dashboard (`web/`) sigue
[`DESIGN_GUIDELINE_APP.md`](DESIGN_GUIDELINE_APP.md), que adapta esta guía a la app.

- **Fuente de verdad:** los tokens de [`landing/src/styles/global.css`](../landing/src/styles/global.css)
  y los componentes de `landing/src/components/`. Si esta guía y el código difieren, se corrige la guía
  en el mismo cambio.
- **Regla general:** reutilizar un token o un componente que ya existe antes de crear uno. Lo nuevo
  se suma a la guía.

## 1. Principios

1. **Claro y sobrio.** Fondo blanco, texto casi negro, un solo color de acento por página. Solo tema claro.
2. **El acento marca la acción.** Va en el botón principal, lo seleccionado, links y palabras clave. No se usa de relleno ni de decoración.
3. **Bordes antes que sombras.** Las superficies se separan con un borde de 1 px. La sombra queda para lo que flota o se destaca.
4. **El producto es la ilustración.** Sin fotos de stock ni ilustraciones: se muestran el widget de llamada, el reproductor de voces y el resultado de una llamada.
5. **Los datos se ven como datos.** Etiquetas, estados, tiempos y contadores van en monoespaciada; los números, con `tabular-nums`.

## 2. Marca

- **Nombre:** Atentina, siempre con mayúscula inicial. Dominio `atentina.com.ar`.
- **Logo:** isotipo (anillo abierto a la derecha con tres barras de audio adentro) + la palabra "Atentina"
  en Bricolage Grotesque 800, `tracking-[-0.02em]`. Componente [`Logo.astro`](../landing/src/components/Logo.astro).
  - El anillo y la palabra toman el color del texto (`currentColor`); las barras, `--color-accent`.
  - Tamaño en el nav: isotipo de 26 px, palabra de 1.35rem, separación de 10 px.
  - No deformarlo, no cambiarle la tipografía, no ponerlo sobre el acento ni sobre fotos.
- **Archivos:** `docs/brand/` (logo e isotipo), `landing/public/favicon.svg` (el isotipo) y
  `landing/src/assets/og.png` (va con hash en la URL: al cambiarla, las vistas previas toman la nueva). Se generan con `scripts/brand/` (`build_atentina.py`, `og.html`; ver [`LANDING.md`](LANDING.md)).
  - Sobre claro: anillo y palabra en `ink`, barras en `accent` (azul del hub).
  - Sobre fondo `ink` (archivos `-blanco`): anillo y palabra en `cta-ink`, barras en `accent-on-dark`.
  - `og.png` (1200 × 630): fondo del hero, logo, título en Bricolage 800 y rótulo en mono con el acento. Todo centrado y dentro del cuadrado central (630 × 630): las miniaturas cuadradas recortan por el centro.

## 3. Color

Usar siempre el token (clase de Tailwind `bg-accent`, `text-muted`, `border-line`, o `var(--color-…)`).
No escribir hex en componentes ni usar la paleta por defecto de Tailwind (`blue-600`, `slate-500`).

| Token | Valor | Uso |
|---|---|---|
| `bg` | `#ffffff` | Fondo de la página |
| `bg-2` | `#f6f8fb` | Sección alterna, fondo de campos y de la transcripción |
| `surface` | `#ffffff` | Tarjetas y paneles |
| `surface-2` | `#f1f4f9` | Encabezado de un panel, avatar o ícono sin seleccionar, píldora neutra |
| `ink` | `#0b1220` | Títulos y texto principal; fondo de la sección CTA |
| `ink-2` | `#33415c` | Párrafos y texto secundario |
| `muted` | `#64748b` | Texto de apoyo, etiquetas, notas |
| `line` | `#e3e8ef` | Borde por defecto y divisores |
| `line-2` | `#cbd5e1` | Borde en hover, botón `ghost`, píldoras del nav |
| `accent` | `#2456e6` | Acción principal, seleccionado, links, énfasis |
| `accent-2` | `#1740b8` | Hover del acento |
| `accent-soft` | `#eaf0ff` | Fondo de lo seleccionado y de los íconos de check |
| `accent-ink` | `#ffffff` | Texto sobre el acento |
| `accent-on-dark` | `#9db6ff` | Acento sobre fondo `ink` |
| `ok` / `ok-soft` | `#1b9c5b` / `#e3f6ec` | Resultado logrado, disponible, checks de los planes |
| `warn` / `warn-soft` | `#b42318` / `#fef3f2` | Errores y acción destructiva (cortar) |
| `wa` / `wa-2` | `#13843f` / `#0f6b33` | Botón de WhatsApp y su hover (verde más oscuro que el de la marca de WhatsApp: blanco encima da 4,8:1) |
| `cta-ink` / `cta-muted` | `#f4f6fa` / `#b8c2d6` | Texto principal y secundario sobre fondo `ink` |

**Acento por vertical.** Cada vertical cambia solo las cuatro variables del acento con `data-theme`
(en `<html>` para la página, o en un elemento para acotarlo, como las tarjetas de `Solutions`):

| Tema | `accent` | `accent-2` | `accent-soft` | `accent-on-dark` |
|---|---|---|---|---|
| (hub) azul | `#2456e6` | `#1740b8` | `#eaf0ff` | `#9db6ff` |
| `turnos` verde azulado | `#0f766e` | `#115e59` | `#e6f4f1` | `#7dd3c7` |
| `cobranzas` violeta | `#6d28d9` | `#5b21b6` | `#f1ebfd` | `#c4b5fd` |
| `municipios` ámbar | `#b45309` | `#92400e` | `#fdf3e7` | `#fcd34d` |

- **Vertical nueva:** un bloque `[data-theme="<slug>"]` con esas cuatro variables en `global.css`. Nada más cambia de color.
- **Contraste medido:** texto blanco sobre el acento da entre 5,0:1 y 7,1:1 según el tema, y el acento
  sobre su `soft`, entre 4,6:1 y 6,1:1. Un acento nuevo tiene que dar 4,5:1 o más en los dos casos.
- `ok` sobre `ok-soft` da 3,1:1: solo para píldoras en semibold e íconos, no para párrafos.
- `muted` sobre blanco da 4,8:1 y sobre `surface-2`, 4,3:1: no usarlo en texto de menos de .78rem.

## 4. Tipografía

| Familia | Token | Pesos cargados | Uso |
|---|---|---|---|
| Bricolage Grotesque | `font-display` | 500, 700, 800 | Títulos, logo, precios, nombres destacados, iniciales en avatares |
| Figtree | `font-body` | 400, 500, 600, 700 | Todo el resto |
| IBM Plex Mono | `font-mono` | 400, 500 | Rótulos, estados, tiempos, contadores |

Se cargan de Google Fonts en [`Base.astro`](../landing/src/layouts/Base.astro). Un peso que no está en
la tabla hay que sumarlo ahí.

| Estilo | Clases |
|---|---|
| Cuerpo (base) | 17 px, interlineado 1.55, `text-ink` |
| `h1` | `clamp(2rem, 4.4vw, 3.1rem)`, 800 |
| `h2` | `clamp(1.7rem, 3.4vw, 2.4rem)`, 700 |
| `h3` | 1.15rem, 700 (en tarjetas, 1.2 a 1.4rem) |
| Bajada (después de un título) | `max-w-[62ch] text-[1.12rem] text-ink-2` |
| Texto de tarjeta | `text-[.96rem] text-ink-2` |
| Apoyo y notas | `text-[.85rem] text-muted` (hasta `.92rem`) |
| Rótulo (eyebrow) | `font-mono text-[.78rem] font-medium tracking-[.08em] text-accent uppercase` |
| Rótulo secundario | `font-mono text-[.78rem] tracking-[.04em] text-muted uppercase` |
| Dato en mono | `font-mono text-[.8rem] text-muted tabular-nums` |

- Los `h1` a `h3` ya traen familia, interlineado 1.08, `tracking-[-0.015em]` y `text-balance` desde la capa base: no repetirlo.
- Un `h1` por página. El énfasis dentro de un título o párrafo es `text-accent` (con `font-bold` en párrafos), no cursiva ni subrayado.
- Títulos en minúscula tipo oración ("Un precio por mes, en pesos"), no En Mayúsculas De Título.

## 5. Layout y espaciado

- **Contenedor:** `mx-auto max-w-[1120px] px-5`. Texto largo (legales): `max-w-[760px]`.
- **Sección:** componente [`Section.astro`](../landing/src/components/Section.astro) (`py-12 min-[901px]:py-[76px]` + contenedor: 48 px en mobile, 76 px desde 901 px; igual en `Voices` y `Cta`, que no lo usan).
  Adentro: `h2`, bajada con `mt-3` y contenido con `mt-9`.
- **Alternancia:** las secciones se separan con `border-line` (`border-t`, `border-b` o `border-y`) y, para
  cortar el ritmo, fondo `bg-bg-2`. La única sección oscura es la CTA final (`bg-ink`).
- **Hero:** `border-b border-line bg-linear-to-b from-bg-2 to-bg pt-10 pb-14 min-[901px]:pt-[72px]`; en una vertical,
  `from-accent-soft`. Dos columnas `1.2fr / .8fr`: texto a la izquierda, widget a la derecha.
  - En mobile el botón de la demo tiene que entrar en el primer pantallazo: título, una línea de apoyo
    y un solo párrafo antes del widget. El segundo párrafo de la home se muestra desde `min-[901px]`.
- **Grillas:** `gap-4` entre tarjetas, `gap-7` a `gap-12` entre columnas. Todo es una columna en mobile.

| Corte | Qué cambia |
|---|---|
| `min-[561px]` | Planes en 2 columnas |
| `max-[720px]` | El nav pasa los links a una segunda fila de píldoras |
| `min-[801px]` | Tarjetas en 2 o 3 columnas |
| `min-[901px]` | Hero y secciones de texto + panel en 2 columnas |
| `min-[1001px]` | Planes en 4 columnas |

Usar estos cortes, no los `sm`/`md`/`lg` de Tailwind. Probar en 360 px de ancho.

## 6. Forma: radios, bordes y sombras

| Elemento | Radio | Borde | Sombra |
|---|---|---|---|
| Botón | `rounded-[10px]` | 1.5 px | — |
| Campo, opción seleccionable, lista de datos, bloque interno | `rounded-xl` (12 px) | 1 px (1.5 px si es seleccionable) | — |
| Tarjeta de contenido | `rounded-2xl` (16 px) | 1 px `line` | `shadow-card` solo en hover |
| Panel o widget, plan, diálogo | `rounded-[18px]` | 1 px `line` (plan: 1.5 px) | `shadow-card` (diálogo: `shadow-dialog`) |
| Píldora, avatar, indicador | `rounded-full` | — | — |

- Solo hay dos sombras: `shadow-card` y `shadow-dialog`. No agregar otras.
- Un elemento destacado (plan más elegido) lleva `border-accent shadow-card`, no un fondo de color.

## 7. Componentes

Usar el componente; no copiar sus clases a mano.

| Componente | Para qué |
|---|---|
| `Button` | Toda acción. `primary` (una por bloque), `ghost` (secundaria), `light` (sobre fondo `ink`), `whatsapp` (verde `wa` con el logo, solo para abrir el chat). Tamaños `md` y `sm` (nav). Con `href` es un link. |
| `Section` | Toda sección de página. |
| `Icon` | Íconos (sección 9). |
| `CheckList` | Lista de características: check en círculo `accent-soft`, título en semibold y texto en `muted`. |
| `Logo`, `Nav`, `Footer` | Marco de toda página. `Nav current="home"` en `/` (integradores) y `"casos"` en `/casos-de-uso`: define qué links son del mismo documento. |
| `Cta` | Cierre de toda página comercial: sección oscura con los botones de contacto. Textos configurables (`eyebrow`, `title`, `lead`, `question`, `submit`): `/` los cambia para integradores. |
| `Solutions`, `Voices`, `Pricing` | Secciones compartidas. `Pricing free` agrega el plan Free (solo API) arriba de los planes con telefonía; solo en `/`. |
| `Platform`, `ApiSection`, `CodeTabs`, `Status` | Home de integradores. `CodeTabs`: pedidos reales a la API con su respuesta (el producto como ilustración). `Status`: píldora `disponible` / `próximamente`: no prometer sin marcarlo. |
| `Developers` | Solo en `/`, debajo de precios: **lo que viene** (`roadmap` en `site.ts`, todo `próximamente`). Al sumar algo que ya existe, pasarlo a `platform` o `apiFeatures`. |
| `CallWidget`, `SampleResult`, `TelDialog` | Demo de llamada, ejemplo de resultado y diálogo del teléfono. |
| `Legal` | Layout de las páginas legales. |

El contenido (agentes, voces, planes, verticales, contacto) vive en
[`landing/src/data/site.ts`](../landing/src/data/site.ts), no en los componentes.

Patrones que se repiten; copiar estas clases al armar algo nuevo:

| Patrón | Clases |
|---|---|
| Tarjeta | `grid content-start gap-3 rounded-2xl border border-line bg-surface p-6` |
| Tarjeta clicable | + `transition-[border-color,translate,box-shadow] duration-150 hover:-translate-y-0.5 hover:border-accent hover:shadow-card` y un "Ver … →" en `font-semibold text-accent` |
| Panel (widget) | `overflow-hidden rounded-[18px] border border-line bg-surface shadow-card` |
| Encabezado de panel | `flex items-center justify-between gap-3 border-b border-line bg-surface-2 px-4 py-3`: título en `font-display text-[1.05rem]` y estado en mono a la derecha |
| Opción seleccionable (radio) | `rounded-xl border-[1.5px] border-line bg-surface hover:border-line-2 has-checked:border-accent has-checked:bg-accent-soft`; el input va oculto (`absolute size-0 opacity-0`) y el avatar o ícono pasa a `bg-accent text-accent-ink` |
| Píldora de estado | `inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[.85rem] font-semibold`: logrado `bg-ok-soft text-ok`, neutro `bg-surface-2 text-ink-2` |
| Etiqueta sobre tarjeta | `rounded-full bg-accent px-2.5 py-1 font-mono text-[.72rem] tracking-[.06em] text-accent-ink uppercase` |
| Lista de datos (`dl`) | `grid divide-y divide-line rounded-xl border border-line`; fila `grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] items-baseline gap-3 px-3 py-2`, `dt` en `text-[.85rem] text-muted` y `dd` en `font-semibold` |
| Campo de texto | `rounded-xl border border-line bg-bg-2 px-3 py-2.5 hover:border-line-2 focus:border-accent focus:bg-surface focus:outline-none` |
| Paso numerado | Tarjeta + número en `grid size-9 place-items-center rounded-full bg-accent font-display font-extrabold text-accent-ink` |
| Burbuja de conversación | `max-w-[85%] rounded-xl px-3 py-1.5`: agente `bg-surface`, persona `justify-self-end bg-accent text-accent-ink` |
| Mensaje de error | `text-[.82rem] font-medium text-warn`, con `min-h-[1.3em]` para que no salte el layout |

## 8. Estados y movimiento

- **Hover:** el botón sube 1 px y la tarjeta clicable, 2 px. Las transiciones duran `duration-150` y listan sus propiedades (`transition-[…]`), nunca `transition-all`.
- **Foco:** el anillo global (`outline-3 outline-offset-3 outline-accent`). No quitarlo, salvo en un campo que marca el foco con `focus:border-accent`.
- **Deshabilitado:** `disabled:cursor-not-allowed disabled:opacity-60`, sin movimiento.
- **Estados de un widget:** un `data-state` en la raíz y variantes `group-data-[state=…]/nombre:` en los hijos. El script solo cambia el `data-state`; no arma clases.
- **Animaciones:** solo las tres del tema (`animate-bar`, `animate-live`, `animate-shake`) y `animate-spin` para la espera. Toda animación lleva su `motion-reduce:`.
- **Espera:** spinner `rounded-full border-3 border-line border-t-accent animate-spin`.
- **Accesibilidad:** HTML semántico (`dialog`, `dl`, `details`, radios reales), `aria-label` en botones sin texto, `aria-live="polite"` en lo que cambia solo, `aria-hidden` en lo decorativo.

## 9. Íconos

- Todos salen de [`Icon.astro`](../landing/src/components/Icon.astro): trazo de 2 px, sin relleno, puntas redondeadas, `viewBox` de 24, color `currentColor`.
- Un ícono nuevo es un path más en ese archivo, con el mismo estilo. No sumar librerías de íconos.
- Tamaños: `size-5` en botones y `size-4` en checks.
- No usar emojis como íconos.

## 10. Voz y texto

- **Español rioplatense con voseo:** "Hacé una demo", "Escribinos", "lo contratás y empieza a atender".
- **Categoría: agentes con IA que atienden a tus clientes**, no "agentes de voz". Los canales (teléfono, WhatsApp) son la prueba y la voz argentina es el diferencial, no la categoría. "Agente de voz" queda en los `metaTitle` de las verticales, porque es lo que se busca.
- **Directo y concreto:** qué hace y cuánto cuesta, con frases cortas. Sin superlativos vacíos, sin signos de exclamación y sin anglicismos que tengan palabra en español.
- **Botones:** verbo + objeto ("Iniciar llamada sin costo", "Ver más voces"). Los links de tarjeta terminan en "→".
- **Números:** pesos como `$ 29.000` (espacio y punto de miles), dólares como `USD 19`, duración como `1:42`. Siempre con `tabular-nums`.
- **Estados en mono y minúscula:** "listo", "terminada".
- **Errores:** dicen qué pasó y qué hacer, en una línea.
- `lang="es-AR"`. Cada página tiene su `title` y `description` (props de `Base.astro`). `ogDescription` es el texto de la tarjeta del link, de hasta ~70 caracteres: WhatsApp corta la descripción a las dos líneas. Hoy la tiene la home; sin ella va `description`.

## 11. Antes de entregar

- [ ] Sin hex nuevos ni colores de la paleta de Tailwind: solo tokens.
- [ ] Un solo `primary` por bloque y un solo acento por página.
- [ ] Radios, bordes y sombras según la sección 6.
- [ ] Se ve bien en 360 px y en 1280 px, y con cada `data-theme` si el componente se usa en verticales.
- [ ] Foco visible con teclado y `motion-reduce` en toda animación.
- [ ] Textos con voseo, sin exclamaciones, números con `tabular-nums`.
- [ ] `npm run build` en `landing/` sin errores.
- [ ] Si se sumó un token, componente o patrón, está en esta guía.
