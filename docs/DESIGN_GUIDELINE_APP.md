# Guía de diseño de la app (dashboard interno y de clientes)

Cómo se ve y cómo habla el dashboard (`web/`): las pantallas internas (rol `admin`), las del cliente
(rol `client`) y el login. Es la adaptación de [`DESIGN_GUIDELINE.md`](DESIGN_GUIDELINE.md) (marca y
landing) a una aplicación de trabajo: misma paleta, mismas tipografías y misma voz, con más densidad
y más estados. Leerla antes de agregar o cambiar una pantalla de `web/`.

- **Stack:** React + Mantine 8, íconos de Tabler, gráficos de `@mantine/charts`. No se suma Tailwind ni
  otra librería de componentes.
- **Fuente de verdad:** [`web/src/theme.ts`](../web/src/theme.ts) y [`web/src/styles.css`](../web/src/styles.css).
  Si esta guía y el código difieren, se corrige la guía en el mismo cambio.
- **Estado (2-oct-2026):** `web/` ya usa el tema de la sección 11 (antes, navy y ámbar con Inter y modo
  oscuro). Lo nuevo se escribe con colores por nombre, sin hex, así cambia solo si cambia el tema.
- **Regla general:** el diseño se resuelve en el tema y en los componentes compartidos
  (`web/src/components/`), no pantalla por pantalla. Antes de dar estilo a mano, buscar el componente
  de Mantine o el compartido que ya lo hace.

## 1. Principios

1. **Claro y sobrio.** Lienzo gris muy claro, tarjetas blancas, texto casi negro. Solo tema claro, como la landing: no hay modo oscuro.
2. **Un solo acento: el azul.** Marca la acción principal, lo seleccionado, los links y lo que está en curso. Los acentos de las verticales de la landing no se usan en la app.
3. **El color significa algo.** Fuera del azul, solo hay color para un estado (verde, amarillo, rojo). Lo que no es un estado va en neutro.
4. **Bordes antes que sombras.** Las tarjetas llevan borde de 1 px y nada de sombra. La sombra queda para lo que flota: menús, popovers, modales.
5. **Los datos se ven como datos.** Teléfonos, IDs, duraciones, versiones y código van en monoespaciada; todo número, con `tabular-nums`.
6. **Densa pero legible.** Se prioriza ver mucho sin scroll; nunca texto de menos de 12 px.

## 2. Interno y cliente

Es una sola app y un solo sistema visual. Cambia qué se muestra y cómo se dice:

| | Cliente (`client`) | Interno (`admin`) |
|---|---|---|
| Quién la usa | Personal de la empresa cliente, no técnico | El equipo de Atentina |
| Vocabulario | Del negocio: "plan", "conversaciones", "minutos" | Puede usar el del sistema: "tier", "motor", "loadtest" |
| Datos técnicos (IDs, latencias, JSON, códigos de error) | Plegados bajo "Detalle técnico", o no se muestran | A la vista, en mono |
| Tablas | Las columnas que le sirven para decidir (hasta 8) | Todas las necesarias, con scroll horizontal |
| Estado vacío | Explica el próximo paso y ofrece la acción | Una línea |
| Errores | Qué pasó y qué hacer, sin códigos | Puede sumar el código o el detalle en mono |

- La columna "Cliente" y los filtros por cliente solo existen para `admin`.
- En el menú, las pantallas solo de `admin` van juntas al final, bajo el rótulo "Administración".
- Lo que solo ve un `admin` dentro de una pantalla compartida lleva una píldora gris "interno".
- El rol se resuelve con `useIsAdmin()` y las guardas de `features/auth/`; no se duplica una pantalla por rol.

## 3. Color

Solo se usan cinco nombres de color de Mantine, que el tema define con la paleta de la marca. No usar
otros (`orange`, `teal`, `violet`, `pink`, `navy`, `amber`…) ni hex en los componentes.

| Nombre | Base (claro) | Qué significa | Ejemplos |
|---|---|---|---|
| `blue` (primario) | `#2456e6` | Acción, selección, en curso | Botón principal, link, ítem activo del menú, llamada en vivo |
| `green` | `#147a46` | Logrado, activo | Finalizada, objetivo cumplido, dato obtenido, activo |
| `yellow` | `#ad5008` | Atención, incompleto | Rechazada, workflow incompleto, dato pendiente, consumo ≥ 70 % |
| `red` | `#b42318` | Error, destructivo | Fallida, error de envío, borrar, consumo ≥ 90 % |
| `gray` | `#64748b` | Neutro, sin estado | Pendiente, inactivo, y toda categoría: origen, motor, rol, canal |

Superficies y texto:

| Rol | Valor | Cómo se usa |
|---|---|---|
| Lienzo de la página | `#f6f8fb` | `var(--app-canvas)` |
| Superficie (tarjeta, header, menú, modal) | `#ffffff` | Default de `Card`, `Paper`, `Modal` |
| Superficie 2 (encabezado de panel, bloque de código, fila en hover) | `#f1f4f9` | `var(--app-surface-2)`, `gray.1` |
| Texto | `#0b1220` | Default |
| Texto secundario | `#33415c` | `c="gray.7"` |
| Texto de apoyo | `#64748b` | `c="dimmed"` |
| Borde | `#e3e8ef` | `withBorder`, `var(--app-line)` |
| Borde de campo y de botón secundario | `#cbd5e1` | Default de los inputs y de `variant="default"` |
| Acento suave (seleccionado) | `#eaf0ff` | `variant="light"`, `var(--mantine-color-blue-light)` |

- **Contraste medido:** texto blanco sobre el relleno da 5,9:1 (azul), 5,4:1 (verde), 5,4:1 (amarillo) y 6,6:1 (rojo). El texto de una píldora `light` sobre su fondo da entre 4,7:1 y 5,6:1.
- El verde de la marca (`#1b9c5b`, `green.5`) da 3,5:1 sobre blanco: sirve para puntos, barras e íconos, no para texto. Para texto, `green` a secas (`green.6`).
- Un estado nunca se comunica solo con color: lleva texto (píldora) o ícono.

## 4. Tipografía

Las mismas tres familias de la marca. Se sirven desde la propia app (paquetes `@fontsource`), porque la
CSP del dashboard solo permite fuentes de `'self'`: no se pueden cargar de Google Fonts.

| Familia | Uso |
|---|---|
| Bricolage Grotesque (700, 800) | Títulos (`Title`) y números destacados |
| Figtree (400, 500, 600, 700) | Todo el resto |
| IBM Plex Mono (400, 500) | Rótulos y datos: clases `.label` y `.mono` |

| Estilo | Cómo |
|---|---|
| Título de página | `Title order={2}`: 24 px, 700 (lo pone `PageHeader`) |
| Título de sección | `Title order={3}`: 19 px |
| Título de tarjeta y de modal | `Title order={4}`: 17 px |
| Texto de interfaz (tablas, campos, botones) | 14 px (`size="sm"`, el default de esos componentes) |
| Párrafo de lectura | 16 px (`size="md"`), hasta 70 caracteres de ancho |
| Label de campo | 14 px, 600 |
| Apoyo y ayudas | `size="xs" c="dimmed"` (12 px) |
| Rótulo (encabezado de tabla, etiqueta de métrica, grupo del menú) | `.label`: mono 11,5 px, mayúsculas, `letter-spacing: .04em`, `dimmed` |
| Dato en mono (teléfono, ID, duración, versión) | `.mono`: mono 13 px, `tabular-nums` |
| Número destacado (métrica) | `.metric`: Bricolage 800, 28 px, `tabular-nums`, interlineado 1.1 |

- Los títulos llevan interlineado 1.15 y `letter-spacing: -0.015em` desde el tema: no repetirlo.
- Un solo título de página por pantalla. Títulos y labels en minúscula tipo oración ("Nueva llamada"), sin punto final.
- Énfasis con peso 600, no con color ni cursiva.

## 5. Layout y espaciado

- **Marco (`AppLayout`):** header de 60 px y menú lateral de 232 px, los dos sobre superficie y con borde;
  el contenido va sobre el lienzo. Logo `atentina-logo.svg` de 28 px de alto en el header. Debajo de `sm` el menú se pliega detrás del botón de menú.
- **Ancho:** el contenido ocupa hasta 1440 px. Formularios y texto de lectura, hasta 720 px.
- **Orden de una pantalla:** `PageHeader` (título, descripción en una línea, acciones a la derecha y el
  link de volver arriba) → filtros → contenido en tarjetas.
- **Espaciado (escala de Mantine):** `md` (16 px) entre tarjetas y como padding de la página; `lg` (20 px)
  de padding en tarjetas y modales; `xs` a `sm` (10 a 12 px) entre controles de un mismo grupo.
- **Cortes:** los de Mantine (`xs` 576, `sm` 768, `md` 992, `lg` 1200, `xl` 1408) con props responsivas
  (`cols={{ base: 1, sm: 2 }}`). No usar los cortes de la landing.
- **Mobile:** toda pantalla se usa en 360 px. Las tablas van en `Table.ScrollContainer`; no se arma una
  vista aparte.

## 6. Forma: radios, bordes y sombras

| Elemento | Radio | Borde | Sombra |
|---|---|---|---|
| Botón, campo, ítem del menú | `md` (10 px) | 1 px | — |
| Bloque interno (código, lista de datos, burbuja) | `lg` (12 px) | 1 px | — |
| Tarjeta (`Card`, `Paper`) | `xl` (16 px) | 1 px | — |
| Modal | 18 px | — | `xl` (diálogo) |
| Menú, popover, desplegable, notificación | `md` (10 px) | 1 px | `md` (tarjeta) |
| Píldora (`Badge`), avatar, punto de estado | Completo | — | — |

- Los valores salen del tema (`defaultRadius`, `defaultProps`): no pasar `radius` ni `shadow` a mano.
- Solo existen las dos sombras de la marca. Una tarjeta no lleva sombra ni cambia en hover.
- No anidar tarjetas: dentro de una tarjeta se separa con `Divider` o con un bloque de 12 px de radio.

## 7. Componentes

| Necesidad | Componente | Regla |
|---|---|---|
| Acción principal | `Button` | Relleno azul. Una por pantalla o modal. |
| Acción secundaria | `Button variant="default"` | Borde gris, fondo de superficie. |
| Acción en una fila o terciaria | `Button variant="subtle" size="compact-sm"` o `Anchor` | Sin borde. |
| Acción destructiva | `Button variant="subtle" color="red"` + `confirmAction({ danger: true })` | El relleno rojo solo aparece en el modal de confirmación. |
| Acción con solo ícono | `ActionIcon variant="default"` + `Tooltip` + `aria-label` | |
| Estado | `Badge` (`components/Badges.tsx`) | Siempre `light`, sin mayúsculas, con el color de la sección 3. Las etiquetas salen de `lib/labels.ts`. Sin `size`: el tema la deja en 12 px. |
| En curso | `LiveBadge` (`components/Badges.tsx`) | Píldora azul con el punto `.live-dot`, que pulsa (sección 8). |
| Contenedor | `Card` | Título con `Title order={4}`; acciones del bloque a la derecha del título. |
| Contenedor plegable | `CollapsibleCard` | Se pliega desde el título ("Nueva llamada", "Detalle técnico"). No usar `Accordion`. |
| Pestañas | `Tabs` | Sin `variant`: el tema las hace píldoras con acento suave. |
| Tabla | `Table` | Encabezados en `.label`; filas separadas por borde, sin rayado; hover en superficie 2; números a la derecha; la acción de la fila, en la última columna. |
| Lista de datos | Pares label y valor | Label en `xs dimmed`, valor en `sm` 600. |
| Métrica | Tarjeta con rótulo `.label` arriba y número `.metric` abajo | El número va en color de texto; toma color de estado solo si indica un problema. El dato de apoyo (%, promedio) va al lado, en `sm dimmed`. |
| Consumo contra un tope | `Progress` | Verde hasta 70 %, amarillo desde 70 % y rojo desde 90 % (`usageColor`). |
| Formulario | Inputs de Mantine + `useForm` | Una columna; label arriba; ayuda en `description`; el error, debajo del campo. |
| Formulario de límites (modal de tier) | `Modal size="xl"` + `Divider` por sección + `SimpleGrid` | Campos numéricos cortos en 2 a 4 columnas desde `sm` (una en móvil), agrupados por tema, para que entre sin scroll en un escritorio; la ayuda común ("vacío = ilimitado") va una sola vez arriba, no en cada campo. |
| Formulario largo (definición de un agente) | Una tarjeta por sección + barra `.def-toolbar` | La barra (estado, guardar, descartar) queda fija arriba desde `sm`; los errores van arriba y al hacerles click llevan al campo. Las listas editables (datos, resultados) son bloques `.def-item` plegables, con subir, bajar y quitar como `ActionIcon` con `Tooltip`. |
| Modal | `Modal`, `confirmAction` | Botones abajo a la derecha: "Cancelar" (`default`) y la acción principal al final. |
| Aviso al terminar una acción | `notifySuccess` / `notifyError` (`lib/notify.ts`) | Arriba a la derecha. |
| Error que bloquea un bloque | `ErrorAlert` (`components/QueryState.tsx`) | Con "Reintentar" si se puede. |
| Carga | `QueryState`; `Skeleton` si se conoce la forma; `loading` en el botón | Sin spinners de página entera, salvo al iniciar la app. |
| Vacío | `EmptyState` | Dice por qué está vacío y cómo se llena. |
| Valor faltante | `Dash` (`components/Badges.tsx`): `–` en `dimmed` | Nunca "null", "N/A", "sin dato" ni la celda en blanco. |
| Conversación | Burbujas (`ChatView`) | Agente: superficie 2, a la izquierda. Persona: acento suave, a la derecha. Nombre de quien habla en `.label`. |
| Código y JSON | `pre.code`, `Code`, `JsonEditor` | Mono 12 px sobre superficie 2, borde, radio de 12 px. En el editor, claves en azul y valores en neutro: el rojo queda para los errores. |

Gráficos (`@mantine/charts`):

- Hasta tres series, siempre en este orden: `var(--chart-1)` azul, `var(--chart-2)` ámbar y `var(--chart-3)`
  verde azulado. Más series se agrupan en "Otros" o se separan en otro gráfico. Paleta validada para
  daltonismo.
- Un solo eje Y. Dos medidas de distinta escala (cantidad y porcentaje) van en dos gráficos.
- Con dos o más series, leyenda siempre visible. Líneas de 2 px; barras de hasta 28 px de ancho.
- Grilla y ejes en el color del borde, textos de eje en `dimmed` de 12 px (variables en `styles.css`, no
  props: `LineChart` no acepta `textColor`). Si una serie es un estado (fallidas), usa el color de ese estado.

## 8. Estados y movimiento

- **Hover:** cambia el fondo o el borde, en 150 ms. Nada se desplaza ni crece.
- **Foco:** el anillo de Mantine (2 px, azul). No quitarlo.
- **Seleccionado:** fondo de acento suave y texto azul en 600 (ítem del menú, pestaña, opción).
- **Deshabilitado:** el estilo de Mantine; si no es obvio por qué, un `Tooltip` lo explica.
- **En vivo:** punto `.live-dot` de 8 px que pulsa. Un dato recién llegado resalta su fila con acento suave que se apaga en 4 s (`.just-set`).
- No hay otras animaciones. Las dos respetan `prefers-reduced-motion`.
- **Accesibilidad:** `aria-label` en controles sin texto, `label` en todo campo, navegación completa con teclado.

## 9. Íconos

- `@tabler/icons-react`, solo de trazo (no los `Filled`), con el trazo por defecto (2).
- Tamaños: 18 px en menú y botones, 16 px dentro de texto o píldoras, 20 px en encabezados.
- El ícono acompaña al texto; solo va sin texto en acciones conocidas (salir, copiar, cerrar), con `Tooltip`.
- Los íconos de marca (WhatsApp) identifican un canal, en gris. Sin emojis.

## 10. Voz y texto

Vale la sección 10 de la guía de marca (voseo, directo, sin exclamaciones). En la app, además:

- **Botones:** verbo en infinitivo + objeto: "Crear agente", "Guardar cambios", "Ver detalle". No "Aceptar" ni "OK".
- **Confirmaciones:** dicen qué se pierde: "¿Borrar el agente Turnos? Las conversaciones se conservan." El botón repite el verbo ("Borrar").
- **Avisos de éxito:** una frase en pasado: "Agente guardado."
- **Errores:** qué pasó y qué hacer: "No se pudo guardar. Probá de nuevo." Sin culpar a quien usa la app.
- **Placeholders:** un ejemplo ("vos@empresa.com"), no la instrucción; la instrucción va en el label o en la ayuda.
- **Formatos:** siempre con `lib/format.ts`: fecha `2/10/2026 14:05` (24 h), duración `1:42`, decimales con coma (`1,5`), pesos `$ 29.000`. Nunca una fecha ISO ni un valor crudo de la API: los estados se traducen en `lib/labels.ts`.
- **Título de la pestaña:** "<Pantalla> · Atentina" (lo pone `PageHeader`).

## 11. Tema de Mantine

Valores que tiene que tener `web/src/theme.ts`. Las escalas pisan los nombres estándar de Mantine,
así `color="green"` o `c="dimmed"` ya dan el color de la marca.

| Escala (0 a 9) | Valores |
|---|---|
| `blue` | `#eaf0ff #dbe5ff #c7d5ff #b3c6ff #9db6ff #5681f6 #2456e6 #1740b8 #12339a #0e287a` |
| `green` | `#e3f6ec #c9ecd9 #a3dcbd #74c99b #45b47b #1b9c5b #147a46 #10653a #0c502e #083b22` |
| `yellow` | `#fdf3e7 #fae3c5 #f6cd95 #f0b360 #e69a35 #cc7a14 #ad5008 #92400e #78350f #5c2a0c` |
| `red` | `#fef3f2 #fde0dc #f9c0b9 #f39a90 #ea6f62 #d6402f #b42318 #912018 #7a1b14 #5f1510` |
| `gray` | `#f6f8fb #f1f4f9 #e9edf3 #e3e8ef #cbd5e1 #94a3b8 #64748b #33415c #1c2740 #0b1220` |

| Ajuste | Valor |
|---|---|
| Esquema de color | Solo claro: `forceColorScheme="light"` en `MantineProvider` |
| `primaryColor`, `primaryShade` | `'blue'`, `6` |
| `black`, `white` | `#0b1220`, `#ffffff` |
| `fontFamily` | `'Figtree Variable', system-ui, sans-serif` |
| `headings` | `'Bricolage Grotesque Variable'`, peso 700, interlineado 1.15; `h1` 32, `h2` 24, `h3` 19, `h4` 17 px |
| `fontFamilyMonospace` | `'IBM Plex Mono', ui-monospace, monospace` |
| `radius`, `defaultRadius` | `xs` 6, `sm` 8, `md` 10, `lg` 12, `xl` 16 px; `'md'` |
| `shadows` | `xs` a `md`: `0 12px 34px rgba(11,18,32,.08)`; `lg` y `xl`: `0 24px 60px rgba(11,18,32,.25)` |
| `Card`, `Paper` | `withBorder`, `radius: 'xl'`; `Card` con `padding: 'lg'` |
| `Modal` | `centered`, `radius: 18`, fondo `#0b1220` al 45 % |
| `Badge` | `variant: 'light'`, sin mayúsculas, peso 600; 12 px y 22 px de alto en `xs` a `md` (Mantine baja a 9 a 11 px) |
| `light` con `gray` | Fondo `gray.2` y texto `gray.7` (`variantColorResolver`): el gris al 10 % de Mantine no se ve sobre una fila en hover y da 4,3:1 |
| `Table` | `verticalSpacing: 'xs'`, `highlightOnHover`; sin `striped` |
| `Tabs` | `variant: 'pills'`; seleccionada con `blue-light` de fondo y texto azul |
| `Menu`, `Popover`, `Combobox` | `shadow: 'md'` |
| `Notification` | `withBorder`, sombra de tarjeta |
| `Button` | peso 600 |
| Label de campo (`InputWrapper`) | peso 600 |
| `BarChart`, `LineChart` | `maxBarWidth: 28`, `strokeWidth: 2` |

Variables propias (`cssVariablesResolver`):

| Variable | Valor |
|---|---|
| `--app-canvas` | `gray.0` |
| `--app-surface-2` | `gray.1` |
| `--app-line` | `gray.3` |
| `--chart-1`, `--chart-2`, `--chart-3` | `#2456e6`, `#b45309`, `#0d9488` |

- Con estas escalas Mantine ya da, sin más ajustes: relleno `blue.6` con hover `blue.7`; píldora `light`
  al 10 % del color; borde de tarjeta y de tabla en `gray.3`; borde de campo en `gray.4`; `dimmed` en `gray.6`.
  El lienzo se pinta con `--app-canvas`.
- **Fuentes:** `@fontsource-variable/figtree`, `@fontsource-variable/bricolage-grotesque` y
  `@fontsource/ibm-plex-mono` (400 y 500, subconjunto latino), importadas en `main.tsx`.
- **`styles.css`:** solo lo que el tema no cubre: `.label` (también los encabezados de tabla), `.mono`,
  `.metric`, `.live-dot`, `.just-set`, `pre.code`, las burbujas, `.def-toolbar` y `.def-item`, el `letter-spacing` de los títulos, el
  ítem seleccionado del menú y de las pestañas, y las variables de los gráficos.
- **Sin modo oscuro:** `forceColorScheme="light"` y `data-mantine-color-scheme="light"` en `index.html`.
  No hay botón de tema, script de tema, `light-dark()` ni logos `-blanco` en `web/`.
- **Logos:** `web/public/atentina-logo.svg` y `atentina-mark.svg` son copia de `docs/brand/`.
- No relajar la CSP por diseño (fuentes, imágenes o estilos externos): ver `AGENTS.md`, "Dashboard público".

## 12. Antes de entregar

- [ ] Solo `blue`, `green`, `yellow`, `red` y `gray`; sin hex ni `radius` o `shadow` a mano.
- [ ] Una acción principal por pantalla o modal; lo destructivo pide confirmación.
- [ ] Cada estado lleva texto o ícono, con el color de la sección 3 y la etiqueta de `lib/labels.ts`.
- [ ] Carga, vacío y error resueltos con `QueryState`, `EmptyState` y `ErrorAlert`.
- [ ] Probado con los dos roles: el cliente no ve vocabulario interno ni datos de otros clientes.
- [ ] Se ve bien en 360 px y en 1440 px.
- [ ] Todo con teclado y con foco visible.
- [ ] Textos con voseo y formatos de `lib/format.ts`.
- [ ] `make web-check` sin errores.
- [ ] Si se sumó un componente compartido, un color o un patrón, está en esta guía.
