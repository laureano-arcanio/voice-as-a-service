# Marca blanca del panel — plan

Que un cliente muestre el dashboard (`web/`, rol `client`) con **su logo y sus colores** en vez de los de
Atentina, para que lo use su propia gente o sus propios clientes como si fuera suyo. Lo configura un
admin desde la ficha del cliente: sube un logo y elige hasta **3 colores**. Nada más se personaliza.

- **Estado (26-oct-2026):** fase 1 implementada (sección 6), **sin desplegar**; probada en el backend de desarrollo con el theme de [Yoizen](marca-blanca/yoizen/README.md) (login con `?c=yoizen`, panel del cliente y pestaña del admin). Código: migración 0034, `app/services/branding.py`, `app/api/routers/branding.py`, `web/src/branding/`, `web/src/features/clients/BrandingTab.tsx`; tests en `tests/test_branding.py`, `tests/test_migration_0034.py` y `web/src/branding/color.test.ts`. Lo que difiere de lo planeado está en la sección 11.
- **Guía de diseño:** [`DESIGN_GUIDELINE_APP.md`](DESIGN_GUIDELINE_APP.md); el tema vive en [`web/src/theme.ts`](../web/src/theme.ts). Al implementar, se le agrega a la guía una sección "Marca blanca" con lo de la sección 5 de acá.

## 1. Qué hay hoy

Medido en `web/src` (26-oct-2026):

| Qué | Dónde | Cuántos |
|---|---|---|
| Logo de Atentina (`/atentina-logo.svg`) | Header del panel, login, bienvenida, crear clave, consentimiento OAuth (los otros 3 usos son del CRM interno) | 8 |
| Título de pestaña con "· Atentina" | `PageHeader` (todas las pantallas) y 6 páginas sueltas | 7 |
| Azul por nombre (`color="blue"`, `blue.6`, `--mantine-color-blue-*`) | Componentes y `styles.css` | 29 |
| Favicon | `web/index.html` → `/atentina-mark.svg` | 1 |
| Textos que dicen "Atentina" al cliente | Pop-up de bienvenida (videos de Atentina), editor del agente (BYOK, agente externo, resumen por mail), consentimiento OAuth | ~10 |

- El tema es uno solo, estático (`createTheme` en `theme.ts`, `MantineProvider` en `App.tsx`), solo claro.
- El azul no es solo "la marca": es **el color de la acción** (botón principal, link, ítem activo, pestaña, en curso). Verde, amarillo, rojo y gris son estados y categorías (guía, sección 3).
- Ya existe un patrón de **imagen subida por cliente**: la del link para llamar (`app/services/call_links.py`: Pillow, recorte y recodificación, `storage/call-links/`, URL pública con `?v=`). Se reutiliza.
- Ya existe el patrón de **función por plan**: un booleano en `tiers` + una clave en `services/features.TIER_HAS` + candado en la UI (`docs/FUNCIONES_POR_PLAN_PLAN.md`; último ejemplo, `external_agent`, migración 0030).

## 2. Decisiones

1. **Tres colores, con un rol cada uno.** No una paleta libre:
   - **Primario**: la acción. Botón principal, links, ítem activo del menú, pestañas, foco, punto "en vivo", primera serie de los gráficos. Reemplaza al azul de Atentina en todo el panel.
   - **Encabezado**: fondo de la barra superior. El color del texto y los íconos de la barra lo calcula la app (blanco o tinta, según contraste). Permite un header oscuro, que es lo que distingue a simple vista un panel de otro.
   - **Acento**: segunda serie de los gráficos y detalles decorativos (avatar de iniciales, línea bajo el header). Nunca significa un estado.
2. **Lo que no cambia:** verde, amarillo, rojo y gris (estados), tipografías (se sirven desde la app por la CSP: `font-src 'self'`), lienzo, bordes, radios, densidad, layout, textos. Un cliente con marca blanca ve el mismo panel con otro logo y otro color de acción.
3. **La escala del primario pisa a `blue`.** Mantine resuelve `color="blue"` por nombre: si el tema del cliente define `colors.blue` con la escala generada desde su primario, los 29 usos existentes y `styles.css` siguen andando sin tocar un componente. No se agrega un color `brand` ni se migran componentes.
4. **Lo configura el admin.** El cliente lo ve; no lo edita (fase 3, si hace falta). Es una función del plan (`tiers.white_label`): si el plan no la incluye, lo guardado queda pero no se aplica.
5. **"Con tecnología de Atentina"**: una línea chica al pie del menú, prendida por default (`powered_by`); el admin la apaga. Los links de Condiciones, Privacidad, Arrepentimiento y Baja **siguen** (Disp. 954/2025, `docs/TERMINOS_PLAN.md`): el contrato es con Atentina.
6. **El admin sigue viendo Atentina.** La marca aplica a los usuarios `client` de ese cliente. El admin tiene una vista previa en la ficha.
7. **Antes del login no hay cliente.** Se resuelve con `/login?c=<slug>` (los mails de alta y de clave ya llevan `?email=`; se les suma `c=`), y el panel recuerda el último slug con marca en `localStorage` para los logins siguientes. Dominio propio por cliente (`panel.cliente.com`): fase 3, fuera de este plan (túnel, CSP, `APP_ORIGINS`, cookies y certificado por host).
8. **Favicon:** con marca activa, un ícono neutro gris (`/panel-mark.svg`); no se deriva del logo (un logo horizontal a 16 px no se lee). Un ícono cuadrado propio, fase 2.
9. **Mails:** los que recibe el usuario del cliente (alta, clave, bienvenida, resumen de llamada) salen con la plantilla de Atentina (`app/mail/layout.py`). Fase 2: nombre, logo y color del cliente en la plantilla. Hasta entonces, un cliente con marca blanca recibe mails de Atentina: avisarlo al venderlo.

## 3. Backend

### 3.1 Modelo (migración 0034)

```
client_branding
  client_id       varchar(36) PK, FK clients.id ON DELETE CASCADE
  enabled         bool, default false        -- el admin la prende cuando está lista
  logo            varchar(80) null           -- archivo en storage/branding/<client_id>/<sha256[:16]>.<ext>
  logo_ratio      float null                 -- ancho/alto, para reservar el lugar sin salto de layout
  color_primary   char(7), default '#2456e6'
  color_header    char(7), default '#ffffff'
  color_accent    char(7), default '#b45309' -- el --chart-2 de hoy
  powered_by      bool, default true
  updated_at, updated_by (FK users.id, SET NULL)

tiers.white_label  bool, default false       -- como external_agent; true para Central e Interno (a confirmar)
```

- Tabla aparte y no columnas en `clients`: el logo y sus validaciones no tienen que ver con la facturación ni con el tier, y queda 1:1 con `client_id` como PK (sin fila = sin marca).
- `TIER_HAS["white_label"] = lambda t: bool(t.white_label)`; aparece en `GET /plan/features` y en el editor de tiers (checkbox como el de "Agente externo").

### 3.2 Logo (`app/services/branding.py`)

Mismo esquema que la imagen del link para llamar, con un formato más:

| Formato | Qué se hace | Tope |
|---|---|---|
| PNG, JPG, WebP | Pillow: `exif_transpose`, se achica para entrar en 480 × 120 px manteniendo la proporción (nunca se agranda), se recodifica a PNG si tiene alfa o a JPEG 90 si no | 2 MB de entrada; mínimo 24 px de alto |
| SVG | Se parsea con `defusedxml`; se rechaza si tiene `<script>`, `<foreignObject>`, atributos `on*`, `javascript:`, `@import` o `url(` en `<style>`, o `href`/`xlink:href` que no empiecen con `#` (se permiten `<style>` y `<defs>`: el de Yoizen los usa). Se guarda tal cual | 200 KB |

- Nombre de archivo `<sha256 del contenido>[:16].<ext>`: subir el mismo logo no cambia nada, y la URL lleva `?v=<sha[:8]>` para cachear un año (`Cache-Control: public, max-age=31536000, immutable`).
- El SVG se sirve con `Content-Type: image/svg+xml`, `X-Content-Type-Options: nosniff` y `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'`: como `<img>` no ejecuta nada, y abierto en una pestaña tampoco.
- `storage/branding/` se suma a `scripts/ops/backup.sh` (como `storage/call-links/` el 21-oct-2026).
- Al cambiar o borrar el logo se borra el archivo anterior.

### 3.3 Colores

- Formato `#rrggbb` en minúscula (regex en el schema; la API normaliza mayúsculas).
- **Primario:** contraste con blanco ≥ 4,5:1 (va con texto blanco en los botones y como texto de link sobre blanco). Si no llega, 422 `color_contrast` con `suggested`: el mismo matiz oscurecido de a 5 % hacia negro hasta que pase. Ejemplo: el naranja de Yoizen `#fd6421` da 2,99:1 y se rechaza; su azul `#0068fd` da 4,77:1 y pasa.
- **Encabezado:** libre. La app elige el texto: blanco si contrasta ≥ 4,5:1, si no, tinta `#0b1220`.
- **Acento:** libre (nunca lleva texto encima).
- La función de contraste (WCAG 2.1, luminancia relativa) está en Python (`services/branding.contrast`) y en TypeScript (`web/src/branding/color.ts`); un test de cada lado verifica estos valores (medidos con `scratch/marca-blanca/paleta.py`):

| Color | Sobre blanco | Sobre tinta `#0b1220` |
|---|---|---|
| `#2456e6` (Atentina) | 5,92:1 | 3,16:1 |
| `#0068fd` | 4,77:1 | 3,92:1 |
| `#272a35` | 14,30:1 | 1,31:1 |
| `#4d39c3` | 7,81:1 | 2,40:1 |
| `#fd6421` | 2,99:1 | 6,26:1 |

### 3.4 API

| Método y ruta | Quién | Qué |
|---|---|---|
| `GET /api/v1/clients/{id}/branding` | admin | Lo guardado + `available` (si el tier la incluye) + `logo_url` |
| `PUT /api/v1/clients/{id}/branding` | admin | `enabled`, `color_primary`, `color_header`, `color_accent`, `powered_by` (todo el objeto; 422 `color_contrast` con `suggested`) |
| `PUT /api/v1/clients/{id}/branding/logo` | admin | multipart, un archivo (422 `logo_format`, `logo_too_large`, `logo_invalid`, `logo_unsafe`) |
| `DELETE /api/v1/clients/{id}/branding/logo` | admin | Saca el logo (la marca queda; sin logo se muestra el nombre del cliente en texto) |
| `GET /api/v1/auth/me` | todos | Suma `branding: BrandingPublic \| null`: resuelto (fila con `enabled` + tier con `white_label` + rol `client`), si no `null` |
| `GET /api/v1/public/branding/{slug}` | público | `BrandingPublic` para el login; 404 si no está activa o el plan no la incluye (no revela si el cliente existe) |
| `GET /api/v1/public/branding/{slug}/logo?v=` | público | El archivo, con los headers de 3.2 |

- `BrandingPublic`: `{name, logo_url, logo_ratio, color_primary, color_header, color_accent, powered_by}`.
- Los dos endpoints públicos van con el mismo límite por IP de los otros públicos (`services/ratelimit.py`) y entran en `CallLinkHostMiddleware.ALLOWED_PREFIXES` solo cuando el link para llamar use la marca (fase 2).
- Los mails de alta de usuario y de clave olvidada (`app/mail/messages.py`) arman `/login?email=...&c=<slug>` cuando el cliente tiene la marca resuelta.
- MCP: `admin_get_branding` y `admin_update_branding` en `app/mcp/catalog.py`, toolset `admin` (`make mcp-docs`). Opcional, después de la fase 1.

## 4. Frontend

### 4.1 De dónde sale el tema

```
web/src/branding/
  color.ts      contrast(a, b), fgOn(bg), scale(hex)   -- escala de 10 tonos, el hex en el tono 6
  theme.ts      brandTheme(base, branding) -> MantineTheme ; brandCssVariables(branding)
  Provider.tsx  <BrandingProvider>: lee me.branding (o la pública del login) y arma el tema con useMemo
  useBranding() -> BrandingPublic | null ; usePageTitle(title)
```

- `scale(hex)`: tonos 0–5 mezclando hacia blanco (91,4, 85,2, 77, 68,8, 59,8 y 27 %), tono 6 el color, tonos 7–9 hacia negro (22,1, 35,3 y 48,8 %); mezclas ajustadas con `scratch/marca-blanca/fit_scale.py`. Con `#2456e6` reproduce la escala `blue` de `theme.ts` con un error máximo de 10 puntos por canal (tono 4; la escala del tema no es una mezcla lineal). Sin marca no se usa: el tema es el de siempre.
- `brandTheme`: `createTheme({ ...theme, colors: { ...theme.colors, blue: scale(primary) } })`. `primaryColor` sigue siendo `'blue'`.
- `brandCssVariables`: las de hoy más `--app-header-bg`, `--app-header-fg`, `--chart-1` (= primario), `--chart-2` (= acento), `--brand-accent`.
- `App.tsx`: `MantineProvider` recibe el tema del provider, no el estático. Sin marca, es exactamente el de hoy.
- Orden al cargar: el tema de Atentina se ve hasta que llega `/auth/me` (ya pasa hoy con el nombre del cliente). Para que el cliente no vea un parpadeo azul en cada carga, el provider guarda la última marca resuelta en `localStorage` (`branding:last`) y arranca con esa; `/auth/me` la confirma o la pisa.

### 4.2 Dónde entra

| Lugar | Hoy | Con marca |
|---|---|---|
| `AppLayout` header | Logo Atentina, fondo blanco | Logo del cliente (`alt` = nombre), `background: var(--app-header-bg)`, texto e íconos con `--app-header-fg` (los `ActionIcon` pasan a `variant="subtle"` con ese color) |
| `AppLayout` pie del menú | Email y links legales | Igual, más "Con tecnología de Atentina" si `powered_by` |
| `PageHeader` y las 6 páginas con título | "X · Atentina" | `usePageTitle('X')` → "X · <nombre del cliente>" (reemplaza los 7 `useDocumentTitle`) |
| Favicon | `/atentina-mark.svg` | `/panel-mark.svg` (neutro), cambiado desde el provider |
| `LoginPage`, `SetPasswordPage`, `ForgotPasswordPage`, `WelcomePage` | Logo Atentina + "Agentes de voz telefónicos" | Logo del cliente (por `?c=` o el último de `localStorage`) sobre una pastilla del color del encabezado (`AuthLogo`: un logotipo para header oscuro también se ve sobre el lienzo claro), sin la bajada; el link "Creá una gratis" se oculta |
| `WelcomeModal` | Videos y texto de Atentina | No se muestra (se marca visto igual) |
| Gráficos | `--chart-1` azul, `--chart-2` ámbar | Primario y acento |
| `OAuthConsentPage` | "usar tu cuenta de Atentina" | Se deja: lo ve quien conecta un agente de IA, es técnico y el consentimiento nombra a quien da el acceso |

- Textos del editor del agente que dicen "Atentina" (BYOK, agente externo, resumen por mail): se dejan. Son explicaciones de dónde corre el modelo y quién manda el mail; cambiarlos por marca haría mentir a la política de privacidad.

### 4.3 Pantalla del admin

Pestaña **"Marca blanca"** en la ficha del cliente (`ClientDetailPage`, junto a "API keys"). Con el plan sin la función, el aviso amarillo de `PlanGate` como en las demás pantallas.

```
┌ Marca blanca ──────────────────────────────────────────────┐
│ [ ] Mostrar el panel con la marca del cliente               │
│                                                             │
│ Logo            [ arrastrá o elegí un archivo ]  PNG, JPG,  │
│                 WebP o SVG, hasta 2 MB (SVG 200 KB)         │
│                 ┌────────┐ ┌────────┐                       │
│                 │ fondo  │ │ fondo  │  vista sobre blanco   │
│                 │ blanco │ │ header │  y sobre el header    │
│                 └────────┘ └────────┘       [Quitar logo]   │
│                                                             │
│ Colores                                                     │
│   Primario      [■ #0068fd ▾]  Botones, links y selección.  │
│                 Contraste con blanco: 4,8:1 ✓               │
│   Encabezado    [■ #272a35 ▾]  Barra superior. Texto: blanco│
│   Acento        [■ #4d39c3 ▾]  Segunda serie de gráficos.   │
│                                                             │
│ [x] Mostrar "Con tecnología de Atentina" al pie del menú    │
│                                                             │
│ Vista previa                                                │
│ ┌─ header con logo ─────────────────────────────────────┐   │
│ │ menú │ Título   [Botón principal] [Secundario] link    │   │
│ │ ■act │ ● Finalizada ● Pendiente ● Fallida   ▂▅▃ ▂▆▂   │   │
│ └───────────────────────────────────────────────────────┘   │
│                                  [Ver el panel como cliente] │
│                                              [Guardar]       │
└─────────────────────────────────────────────────────────────┘
```

- `ColorInput` de Mantine con `swatches` (los de la marca de Atentina; los sacados del logo, fase 2). Debajo, el contraste calculado en vivo con `color.ts`; si no llega a 4,5:1, el mensaje y un botón "Usar `#xxxxxx`" con el `suggested` del server.
- La vista previa es un componente (`BrandPreview`) que arma el tema con `brandTheme` dentro de un `MantineProvider` propio, así muestra los componentes reales (botón, badge, link, mini gráfico) y no una imitación.
- "Ver el panel como cliente": guarda la marca en `sessionStorage` (`branding:preview`) y abre el panel en otra pestaña; el provider la aplica para el admin hasta cerrar la pestaña. No cambia nada en el server.
- Guardar hace `PUT .../branding`; el logo se sube al soltarlo (`PUT .../logo`), con su propio spinner, como la imagen del link para llamar.

## 5. Para la guía de diseño (resumen)

- Con marca activa, `blue` es el primario del cliente. Todo lo demás de la sección 3 de la guía sigue igual.
- El header puede ser oscuro: nada de lo que va en el header puede depender de que el fondo sea blanco (hoy: logo, nombre, email, dos `ActionIcon`).
- El acento solo en `--chart-2` y decorativo. No se usa para texto ni para estados.
- Ningún componente nuevo nombra a Atentina en un texto que ve el cliente, salvo que explique dónde corre el modelo o quién manda un mail.

## 6. Fases

| Fase | Qué | Tamaño |
|---|---|---|
| **1** (hecha el 26-oct-2026) | Migración 0034, servicio y API (3.2 a 3.4), `me.branding`, endpoints públicos, provider y tema en `web/`, header, títulos, favicon, login por `?c=`, pestaña del admin con vista previa y "Ver el panel como el cliente", `white_label` en el editor de tiers, `c=` en los mails de alta, clave y número asignado, backup, tests | ~2 días |
| 2 | Mails con la marca (`layout.py` con nombre, logo absoluto y primario; remitente "Panel de <Cliente>"), ícono cuadrado para el favicon, link para llamar con la marca del cliente, "Copiar la marca de otro cliente" (un partner con varios clientes), swatches sacadas del logo, MCP `admin_*_branding` | ~1,5 días |
| 3 | El cliente edita su marca en Mi cuenta (mismos endpoints bajo `/plan`), dominio propio por cliente | a definir |

## 7. Pruebas

- `tests/test_branding.py`: PNG se achica y recodifica; SVG limpio se guarda tal cual; SVG con `<script>` u `onload` → 422 `logo_unsafe`; 3 MB → 422; `#fd6421` → 422 con `suggested`; `me.branding` es `null` sin `enabled`, sin tier o para un admin; público 404 sin `enabled`; headers de cache y CSP del logo; borrar el cliente borra la fila y el archivo.
- `web/`: `color.test.ts` (la tabla de 3.3 y la escala contra `blue` de `theme.ts`), `AppLayout.test.tsx` (logo con `alt` del cliente, header con el color, "Con tecnología de Atentina" según `powered_by`), `LoginPage.test.tsx` (con `?c=` muestra el logo del cliente; sin marca, el de Atentina). `make web-check`.
- A mano: capturas con `scratch/shots/shoot.mjs` (backend dev en :8111) con un cliente con la marca de Yoizen, en escritorio y a 390 px.

## 8. Cómo desplegar

1. `make migrate-test` con la 0034 contra una copia del backup; `make migrate`.
2. `make calls-active && make up-agent` (recrea `app` y `agent`).
3. Verificar que `storage/branding/` quedó en `scripts/ops/backup.sh`.
4. Prender `white_label` en los tiers que la incluyen (editor de tiers) y actualizar la landing (`/desarrolladores/docs/api`: qué incluye cada plan).
5. Cargar el primer theme (sección 9) desde la ficha del cliente y probar el login con `?c=yoizen`.

## 9. Primer theme: Yoizen

[`docs/marca-blanca/yoizen/`](marca-blanca/yoizen/README.md): `theme.json` (el cuerpo del `PUT .../branding`), `logo-claro.svg` (el logotipo de su sitio con la tinta en blanco, el que se sube; pasa el filtro de 3.2) y `preview.html` (el panel con esa marca, estático). Primario `#0068fd` (4,77:1 sobre blanco), encabezado `#272a35` (la tinta de su logotipo, texto blanco a 14,3:1) y acento `#4d39c3` (el violeta del logo). El naranja `#fd6421` del logo no se usa: no contrasta con blanco y se confunde con el amarillo de "atención". Cargado y probado en el backend de desarrollo (`scratch/marca-blanca/seed_yoizen.sh`); en producción se carga desde la ficha del cliente.

## 10. Pendientes y riesgos

- **Desplegar** (sección 8) y cargar la marca de Yoizen cuando se cierre con ellos. Si se cobra aparte, es un tier.
- **Un partner con varios clientes** (el caso de Yoizen si revende): en la fase 1 se carga la misma marca en cada cliente; la fase 2 la copia con un botón. Si se vuelve común, una tabla `brands` compartida en vez de 1:1.
- **Mails con la marca de Atentina** hasta la fase 2.
- **Acento mal elegido**: un acento verde o rojo se confunde con un estado en los gráficos. El admin lo ve en la vista previa; no se valida.
- **`localStorage` con la marca**: si un cliente pierde la función, el login la sigue mostrando hasta el próximo `/auth/me` (segundos). Aceptable.

## 11. Qué quedó distinto de lo planeado (26-oct-2026)

- **`white_label` en los tiers:** se edita en el editor de tiers (switch "Marca blanca", como "Agente propio"); la migración lo prende en Central e Interno y el seed lo prende en Interno. Decisión del usuario, con ese default.
- **Yoizen va con la variante A** (encabezado `#272a35`): el logo que se sube es la versión clara del logotipo. Para que ese logo se vea también en el login, `AuthLogo` lo pone sobre una pastilla del color del encabezado (en el plan, el login tenía el logo suelto sobre el lienzo). La regla queda simple: un solo logo, que se lea sobre el encabezado elegido; la vista previa del admin lo muestra sobre blanco y sobre el encabezado.
- **`BrandingPublic` lleva `slug`:** el provider lo guarda en `localStorage` (`branding:last`) para recordar la última marca y arrancar sin parpadeo.
- **`BodyLimitMiddleware`:** el logo pasa por el mismo tope que la imagen del link para llamar (`IMAGE_UPLOAD_PATH`, 5 MB + 64 KB); el servicio corta en 2 MB (`logo_too_large`).
- **La escala del primario** se desvía hasta 10 puntos por canal de la escala `blue` del tema (no 1 a 3 como decía el plan); se usa solo con marca, así que el panel de Atentina no cambia.
- **`color_contrast`:** el color sugerido viene en `errors[0].suggested` (los `details` de `ServiceError`); la UI muestra el contraste en vivo y el botón "Usar #xxxxxx" cuando la API lo rechaza.
- **`WelcomeModal`:** con marca no se muestra y se marca visto en cuanto aparece la sesión (el modal legal sigue, es obligatorio).
- **El 404 del público** también para un cliente inactivo.
- **Sin MCP ni ratelimit propio** en los endpoints públicos de la marca (son dos GET cacheables; queda para la fase 2 si hace falta).
