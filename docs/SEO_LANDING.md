# SEO de la landing (atentina.com.ar)

Revisión del 15-oct-2026 sobre `landing/` (Astro 7 + Tailwind 4, Render). Primero el diagnóstico, después
la propuesta en orden de impacto. Las reglas de texto siguen siendo las de [`DESIGN_GUIDELINE.md`](DESIGN_GUIDELINE.md),
sección 10: voseo, sin superlativos, categoría "agentes con IA que atienden a tus clientes" ("agente de voz" solo
en `metaTitle`, porque es lo que se busca).

## 1. Diagnóstico

Lo que ya está bien: un `h1` por página, `title` y `description` propios, canónica absoluta, `lang="es-AR"`,
Open Graph con imagen de 1200 × 630, `robots.txt` con sitemap, 301 de `www`, `.com` y las URL viejas de las
verticales, sin imágenes pesadas (el JS de la llamada se descarga recién al llamar), GA4 cargado `async`.

Puntos débiles, de mayor a menor peso:

| # | Problema | Dónde | Efecto |
|---|---|---|---|
| 1 | **No hay una página por capacidad.** Las páginas son por público (home, desarrolladores, casos de uso, asistentes). "Voces argentinas", "síntesis de voz", "transcripción", "WhatsApp", "telefonía" y "SIP" aparecen como frases sueltas dentro de otras páginas: ninguna URL tiene esos términos en `h1`, `title` ni slug. | `src/pages/` | No hay con qué posicionar para esas búsquedas. Es el punto principal. |
| 2 | **"SIP" no aparece en ningún lado**, y "traer tu línea" está en una sola tarjeta (`casos-de-uso`, "Número argentino"). | todo el sitio | Cero para "sip", "central telefónica", "telefonía IP". |
| 3 | **Sitemap a mano y desactualizado:** faltan `/asistentes` y `/registro`, sin `lastmod`. | `public/sitemap.xml` | Google descubre `/asistentes` solo por links. |
| 4 | **Datos estructurados mínimos:** solo `Organization`, con `og.png` como `logo` (no es el logo) y sin teléfono ni WhatsApp. Sin `FAQPage` (hay FAQ en 6 páginas), sin `Offer` (hay precios en pesos), sin `BreadcrumbList`. | `Base.astro` | Sin resultados enriquecidos ni panel de marca. |
| 5 | **Fuentes desde Google Fonts:** una hoja de estilos de terceros que bloquea el render, 3 familias y 8 variantes. | `Base.astro` | LCP y CLS (el `h1` es el LCP y cambia de fuente al cargar). Core Web Vitals pesan en el ranking. |
| 6 | **Sin `<main>`** en las páginas principales (solo en `Legal` y `docs`). | `index`, `desarrolladores`, `casos-de-uso`, `[vertical]`, `asistentes` | Accesibilidad y semántica; Lighthouse lo marca. |
| 7 | **Titles largos o sin la palabra buscada:** `/casos-de-uso` tiene 83 caracteres (Google corta en ~60). La home no nombra "voces argentinas" ni "agentes" en el `title`. `/desarrolladores/docs` dice "Documentación de la API" sin "OpenAI" ni "voz". | páginas | Se corta el `title` y pierde la palabra clave. |
| 8 | **Párrafo del hero duplicado** palabra por palabra entre `/` y `/desarrolladores`. | `index.astro:36`, `desarrolladores/index.astro:36` | Contenido duplicado entre las dos páginas más importantes. |
| 9 | **Enlazado interno pobre:** el footer no linkea `/asistentes` ni `/registro`; las verticales solo se linkean desde `/casos-de-uso`; no hay links entre capacidades. | `Footer.astro`, `Platform.astro` | Las páginas profundas reciben poca autoridad. |
| 10 | **`/registro` indexable** (página transaccional, sin contenido). Sin página `404`. Sin `og:image:alt`, sin `twitter:title/description/image` explícitos, sin `meta robots` con `max-image-preview:large`. | `registro.astro`, `Base.astro` | Menor. |
| 11 | **La sección de voces dice "Más de 30"** y el catálogo servido tiene 41 (28 mujeres, 13 hombres, `tts/finetune/voces.tsv`). El `h2` "Voces con nuestro acento." no lleva la palabra clave. | `Voices.astro`, `site.ts` | Se desaprovecha el diferencial. |

## 2. Palabras clave objetivo

Agrupadas por intención. Cada grupo tiene una página dueña (la que lleva el término en `h1` y `title`); el resto
la linkea con ese texto de ancla.

| Grupo | Términos (español, Argentina) | Página dueña |
|---|---|---|
| Voces argentinas | voces argentinas con IA, síntesis de voz con acento argentino, text to speech español rioplatense, voz artificial argentina, TTS en español, API de síntesis de voz | `/plataforma/voces-argentinas` (nueva) |
| Transcripción | transcripción de audio en español, speech to text API, reconocimiento de voz por API, transcribir llamadas | `/plataforma/transcripcion` (nueva) |
| WhatsApp | WhatsApp con IA para empresas, integración WhatsApp Business API, agente de WhatsApp con IA, bot de WhatsApp con voz, campañas por WhatsApp | `/plataforma/whatsapp` (nueva) |
| Telefonía argentina y SIP | telefonía IP para empresas Argentina, número 0800 virtual, SIP trunk Argentina, central telefónica con IA, atención telefónica automática, llamadas salientes automáticas | `/plataforma/telefonia` (nueva) |
| Agentes | agente de voz con IA, agente telefónico con inteligencia artificial, asistente virtual telefónico, automatizar atención al cliente | `/casos-de-uso` y sus verticales (existen) |
| API y LLM | API de voz, API compatible con OpenAI, LLM en servidores en Argentina, inferencia en Argentina, API de IA en pesos | `/desarrolladores` y `/desarrolladores/docs` (existen) |
| Empresas | soluciones de IA para empresas, software de atención al cliente con IA, agentes con IA para empresas | `/` (existe) |
| Agente personal | agente personal con IA, asistente por WhatsApp para mi negocio, software controlado por voz | `/asistentes` (existe) |

## 3. Propuesta

En orden de impacto. Todo vive en `landing/`; al terminar, `npm run check` y `npm run build` sin errores.

### 3.1 Cuatro páginas de capacidad bajo `/plataforma/`

Una página por grupo de la tabla anterior, del mismo estilo que las verticales (`[vertical].astro`): datos en
`site.ts` (`capabilities`), una sola plantilla `src/pages/plataforma/[slug].astro`, y un índice `/plataforma` chico
(las tres capas de `Platform` más las cuatro tarjetas). Cada página, entre 600 y 900 palabras de texto real, con:

- `h1` con el término principal, bajada, y los `facts` en mono como en los demás heros.
- Algo para probar arriba a la derecha, como en las otras páginas: `Voices` en voces y en transcripción (la
  demo de texto a voz sirve en las dos; no hay demo de transcripción en `/api/v1/demo`), `CallWidget` en telefonía
  y `AssistantChat` o el botón a WhatsApp en WhatsApp.
- "Cómo funciona" (3 pasos), "Qué incluye" (`CheckList`), un ejemplo de pedido a la API (`CodeBlock`, con los
  endpoints reales de `docs/API_INFERENCIA.md`) donde aplique, precios (`Pricing`), FAQ propia (4 a 6 preguntas)
  y `Cta`. Las verticales y las otras capacidades se linkean entre sí ("Otras capacidades").
- `BreadcrumbList` (Plataforma → capacidad) y `FAQPage` (ver 3.3).

Contenido de cada una, con lo que el producto hace hoy (no inventar capacidades):

| Slug | `h1` (propuesta) | Qué cuenta |
|---|---|---|
| `voces-argentinas` | Voces argentinas con IA, con nuestro acento | 41 voces propias (28 mujeres, 13 hombres), entrenadas en servidores propios; el catálogo completo por nombre y género desde `tts/finetune/voces.tsv` (sin WER ni car/s); demo con cualquiera de las 41; streaming PCM que empieza a sonar en ~0,5 s (dato de `LANDING.md`); `POST /audio/speech` compatible con OpenAI; para qué se usan (agentes, IVR, audios de WhatsApp, lectura de textos). |
| `transcripcion` | Transcripción de audio en español por API | `POST /audio/transcriptions`, español rioplatense, archivos y llamadas, minutos descontados a la vista en `GET /usage`; no se guarda el audio (FAQ de desarrolladores); se usa en el agente para transcribir cada llamada y nota de voz. |
| `whatsapp` | WhatsApp con IA para tu empresa | El mismo agente atiende el teléfono y WhatsApp: texto, notas de voz y llamadas de WhatsApp; campañas salientes; el número de WhatsApp se registra desde el panel (Embedded Signup: decir "desde el panel", sin prometer plazos); ruteo por contacto; link de pago al cerrar un acuerdo. |
| `telefonia` | Telefonía argentina incluida: números, 0800 y SIP | Numeración regional, 0800 y 0810, entrantes y salientes, varias a la vez, minutos incluidos en el plan; la plataforma corre sobre SIP y acepta traer la línea de siempre; "si tenés una central telefónica (PBX) o un proveedor SIP propio, consultanos" (no prometer un trunk SIP autoservicio: hoy se arma a mano); llamadas programadas y campañas. |

`site.ts` ya tiene `verticals`; agregar `capabilities` con la misma forma (`metaTitle`, `metaDescription`,
`eyebrow`, `headline`, `lead`, `steps`, `features`, `faq`, `code?`). Sin nuevos tokens ni colores: estas páginas
usan el acento por defecto (sin `data-theme`).

### 3.2 Titles, descriptions y textos de las páginas existentes

- `/`: `title` "Atentina: agentes con IA, voces argentinas y telefonía en un solo servicio" (≤ 70). `h1` queda; en
  la bajada, cambiar la frase duplicada con `/desarrolladores` (3.2 abajo) y linkear "voces con acento argentino" a
  `/plataforma/voces-argentinas` y "WhatsApp" a `/plataforma/whatsapp`.
- `/desarrolladores`: `title` "API de voz en Argentina: LLM, transcripción y síntesis compatible con OpenAI | Atentina".
  Reescribir la bajada del hero para desarrolladores (keys, SDK de OpenAI, streaming, servidores en Argentina), no
  la misma que la home.
- `/desarrolladores/docs`: `title` "Documentación de la API compatible con OpenAI: LLM, transcripción y voz | Atentina". Desde el 25-oct-2026 la API está en
  `/desarrolladores/docs/api` y `/desarrolladores/docs` es la portada (MCP y API).
- `/casos-de-uso`: `title` "Agentes con IA que atienden por teléfono y WhatsApp | Atentina" (≤ 60).
- Verticales: los `metaTitle` ya llevan "agente de voz"; agregar el rubro a la `metaDescription` donde falte.
- `Voices.astro`: `h2` "Voces argentinas, con nuestro acento"; bajada "41 voces con acento argentino, 28 femeninas
  y 13 masculinas..." y un link "Ver todas las voces →" a la página nueva. Reemplazar "Más de 30" por "41" en
  `facts` de `/` y `/desarrolladores` y en `casos-de-uso/index.astro`.
- `Platform.astro` / `site.ts`: las tarjetas "Motores por API" y "Telefonía y WhatsApp" linkean a las páginas nuevas
  además de a `/desarrolladores` y `#precios` (un segundo link de texto, o cambiar el destino: decidirlo en la
  implementación según quede mejor).

### 3.3 Datos estructurados (JSON-LD)

Centralizados en `Base.astro` con un prop `schema?: object[]` que cada página completa:

- `Organization` (todas): `logo` con el logo real (exportar `docs/brand/atentina-mark.svg` a PNG de 512 × 512 en
  `src/assets/`; `og.png` no es un logo), `contactPoint` con `telephone` "+54 800 220 1233" y `contactType`
  "sales", `email`, `areaServed` "AR", `address: { addressCountry: "AR" }`. Sin `sameAs` hasta que haya redes.
- `WebSite` (home): `name`, `url`, `inLanguage` "es-AR".
- `FAQPage` (donde hay `Faq`): generado desde los `items` del componente. Google hoy solo lo muestra en sitios de
  salud y gobierno, pero lo usan otros buscadores y los asistentes de IA.
- `Offer` dentro de un `Service` o `SoftwareApplication` (páginas con `Pricing`): los planes con `price` y
  `priceCurrency` "ARS", `priceSpecification` con `billingDuration` mensual. "A medida" sin `price`.
- `BreadcrumbList` en verticales y capacidades.
- `Service` por vertical y por capacidad (`serviceType`, `provider` Atentina, `areaServed` AR).

### 3.4 Sitemap y robots

- Reemplazar `public/sitemap.xml` por `@astrojs/sitemap` en `astro.config.mjs`, con `filter` que excluya
  `/registro` y `lastmod` automático. El sitemap pasa a ser `sitemap-index.xml`: actualizar `robots.txt` y
  recordar en `LANDING.md` que hay que reenviarlo en Search Console.
- `/registro`: `<meta name="robots" content="noindex, follow">` (nuevo prop `noindex` en `Base.astro`).
- `Base.astro`: `<meta name="robots" content="index, follow, max-image-preview:large">` por defecto,
  `og:image:alt`, `twitter:title`, `twitter:description`, `twitter:image`.
- Página `src/pages/404.astro` (Render sirve `404.html`): título, texto corto y links a las cuatro puertas.

### 3.5 Rendimiento: fuentes propias

- Sacar la hoja de Google Fonts. Instalar `@fontsource-variable/bricolage-grotesque`, `@fontsource-variable/figtree`
  y `@fontsource/ibm-plex-mono` (400 y 500), importarlas en `global.css` y `<link rel="preload">` de los woff2 de
  Bricolage y Figtree desde `Base.astro`. `font-display: swap` se mantiene.
- Los `@font-face` de `global.css` tienen que respetar los nombres de familia que usan los tokens (`font-display`,
  `font-sans`, `font-mono` de `DESIGN_GUIDELINE.md`, sección 4).
- Medir antes y después con Lighthouse (`npm run preview` y Chrome headless) y anotar LCP y CLS de `/` en este
  archivo.

### 3.6 Semántica y enlazado interno

- Envolver el contenido de cada página en `<main>` (después de `Nav`, antes de `Footer`); `Section` no cambia.
- `Footer.astro`: tres columnas con todas las páginas: Producto (Home, Casos de uso, Asistentes, Plataforma y sus
  cuatro capacidades), Desarrolladores (API, Documentación, Registro) y Legales. Debajo, "Atentina · Hecho en
  Argentina · hola@atentina.com.ar · 0800-220-1233" como texto (consistencia de datos de contacto).
- Las verticales linkean a `/plataforma/whatsapp` y `/plataforma/telefonia` desde sus `features` donde ya hablan
  de eso ("Link de pago", "Campañas programadas", "Varias llamadas a la vez").

### 3.7 Lo que queda para el usuario (no es código)

- Search Console: confirmar que la propiedad existe (`LANDING.md`, paso 10) y enviar el sitemap nuevo. Pedir la
  indexación de las cuatro páginas nuevas.
- Bing Webmaster Tools: importar desde Search Console.
- Backlinks: perfil en directorios de software argentinos y notas en medios del rubro (fuera de este plan).

## 4. Registro

| Fecha | Qué se hizo | Medido |
|---|---|---|
| 15-oct-2026 | Diagnóstico y propuesta. | — |
| 15-oct-2026 | **3.1** Cuatro páginas de capacidad (`/plataforma/voces-argentinas`, `transcripcion`, `whatsapp`, `telefonia`) desde una plantilla (`[slug].astro`) con datos en `capabilities` (`site.ts`), más el índice `/plataforma`. | Texto propio de cada una (sin catálogo, precios ni widgets): 703 a 792 palabras. `h1` único, `<main>` y canónica correcta en las cinco. |
| 15-oct-2026 | **3.2** Titles y descriptions según el plan; bajada del hero de `/desarrolladores` reescrita (keys, SDK de OpenAI, streaming, servidores en Argentina); `Voices` con "Voces argentinas, con nuestro acento" y link a la página nueva; "Más de 30" pasó a 41 en `facts`, `Voices` y `/casos-de-uso` (sale de `allVoices`, no hay otro número escrito). `Platform` linkea a las capacidades con un segundo renglón de links de texto (`more`), y la home suma "Ver toda la plataforma →". | `grep` de "30 voces" en `landing/src`: sin resultados. |
| 15-oct-2026 | **3.3** JSON-LD: prop `schema` en `Base` y helpers en `data/schema.ts`. `Organization` en todas (logo PNG 512 × 512 real, `contactPoint` con el 0800, `address` AR); `WebSite` (home); `Service` con `Offer` en ARS por mes (home, desarrolladores, casos de uso, verticales, capacidades); `FAQPage` (home, desarrolladores, casos de uso, capacidades); `BreadcrumbList` (verticales y capacidades). | Los 18 HTML de `dist/` parsean con `json.loads`. |
| 15-oct-2026 | **3.4** `@astrojs/sitemap` (sin `/registro` ni `/404`, `lastmod` = fecha del build), `public/sitemap.xml` borrado, `robots.txt` a `sitemap-index.xml`; prop `noindex` (usado en `/registro` y el 404); `robots` con `max-image-preview:large`, `og:image:alt` y `twitter:*`; `404.astro`. | `dist/sitemap-0.xml`: 16 URL, con `/asistentes` y las cinco de `/plataforma`, sin `/registro`. |
| 15-oct-2026 | **3.5** Fuentes propias con `@fontsource` (Bricolage con eje opsz, Figtree variable, Plex Mono 400 y 500), sin Google Fonts, con `preload` de Bricolage y Figtree. Los tokens usan las familias que declaran los paquetes. | Chrome headless por CDP, 3 corridas, caché apagada. **Antes** (Google Fonts), `/`: escritorio LCP 200 a 212 ms y CLS 0,125; móvil (CPU ×4, 1,6 Mbps, 150 ms) LCP 556 ms y CLS 0. **Después**, `/` y `/plataforma/voces-argentinas`: escritorio LCP 76 a 80 ms y CLS 0; móvil LCP 784 a 840 ms y CLS 0. Sin `preload` el CLS de escritorio vuelve a 0,13 a 0,17 (el cambio de fuente): el `preload` elimina el salto, pero en el móvil lento suma ~250 ms al LCP (97 KB más compitiendo con el CSS). Medición propia, no Lighthouse (no está instalado). |
| 15-oct-2026 | Revisión: los titles de `/`, `/desarrolladores` y `/desarrolladores/docs` acortados a 54, 65 y 60 caracteres (los literales del plan pasaban de 70). Los textos de SIP y WhatsApp verificados contra lo que el producto hace hoy. | Todos los titles indexables ≤ 67 caracteres. |
| 15-oct-2026 | **3.6** `<main>` en todas las páginas; `Footer` en tres columnas con todas las páginas y los datos de contacto como texto; las verticales y `/casos-de-uso` linkean a `/plataforma/whatsapp`, `/telefonia` y `/voces-argentinas` desde sus `features` (`Feature.href`). | Un `h1` por página (salvo `/registro`, que ya traía uno oculto por plan; es `noindex`). Sin scroll horizontal a 360 px en las cuatro capacidades, el índice, el 404 y una vertical. |

### Decisiones y lo que quedó fuera

- **`FAQPage`:** lo arma cada página con `faqPage(items)` y los mismos `items` que pasa a `Faq`, no el componente: el JSON-LD queda todo en `Base` y `Faq` no cambia.
- **"Algo para probar arriba a la derecha":** `Voices` es una sección ancha (lista + reproductor) y no entra en 380 px. En voces y transcripción el hero muestra a la derecha un pedido real a la API (`CodeBlock`) y `Voices` va justo debajo. En telefonía va el `CallWidget`; en WhatsApp, un panel con el botón al chat de Atentina (no `AssistantChat`, que es del agente personal de `/asistentes`).
- **Tarjetas de `Platform`:** se dejó el link principal y se sumó un renglón de links de texto a las capacidades, en vez de cambiar el destino.
- **Titles:** los de las páginas existentes son los del plan, tal cual, y algunos exceden el tope que el plan menciona: la home tiene 74 caracteres (tope 70) y `/casos-de-uso`, 62 (tope 60); `/desarrolladores` (87) y `/desarrolladores/docs` (82) son largos por el texto que dicta el plan. Los de las páginas nuevas se acortaron a 52 a 65 caracteres.
- **Footer:** se sacó "Los precios son de referencia", que contradice el texto de precios ("precio final").
- **`lastmod` del sitemap:** es la fecha del build, igual para todas. Si más adelante se quiere una fecha por página, hay que sacarla del historial de git.
- **No se hizo:** 3.7 (Search Console, Bing, backlinks), que es del usuario. Tampoco `Service` para `/asistentes`, que el plan no pide, ni `sameAs` (no hay redes). Siguen largas las `description` de `/asistentes` (216), `/desarrolladores` (183) y `/` (177), que no estaban en 3.2.
