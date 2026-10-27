> **Histórico.** Las apps por cliente y el motor `assistant` se quitaron el 26-oct-2026 (migración 0033); ver [`../LIMPIEZA_PLAN.md`](../LIMPIEZA_PLAN.md). Este documento describe lo que había y no se mantiene.

# Plan: apps por cliente (contenedores con API, MCP y vistas)

> **Lo vigente está en [`APPS.md`](APPS.md).** Este documento es el diseño, las decisiones y la historia
> de las pruebas. Las secciones 2 a 6 son la propuesta original; donde difieren de lo implementado
> (una herramienta `abrir_vista` y no una por vista, jobs con `hora`/`dias` y no `cron`, sin PIN,
> hasta 20 herramientas), vale `APPS.md`.

Diseño (12-oct-2026). **Estado (12-oct-2026): MVP desplegado. SUGYM completo (contrato v1.1)
probado con los casos de uso, 38/38; falta desplegar la v1.1 en `app`** (sección 11). Primer caso: SUGYM (gimnasio, #270 de
[`mercado/seguimiento.md`](../mercado/seguimiento.md)): alumnos y asistencias; cuotas y pagos después.
**15-oct-2026: datos reales en producción.** Se borró la seed de `app-sugym-gestion` (backup previo en
`~/atentina-backups/apps/sugym-gestion/app-20261015-170828.db`) y se cargó la planilla de alumnos del
dueño: 2.616 alumnos (de 2.636 filas: 4 de gastos y 16 nombres repetidos unidos), todos activos, sin
teléfono, plan ni pagos, alta el 15-oct, con las notas de la planilla en `observaciones` ("fila N" para
ubicarlos). La planilla es histórica (2019 a 2026, los más nuevos arriba, y el monto es la última
cuota que pagó cada uno): el mismo día se borraron los de la fila 202 en adelante (montos de 2025 y
anteriores) y quedaron los 200 primeros (filas 2 a 201, cuotas de $55.000 a $125.000: precios de 2026).
Quién sigue viniendo lo define el dueño. Los precios volvieron a los de la migración 0003 (la seed había agregado precios
viejos falsos). Scripts de una sola vez en `scratch/sugym-alumnos/` del repo de Atentina (no
versionados); `seed.py` sigue siendo solo de prueba.

## 0. Idea

Un asistente personal para el dueño de un negocio chico, por WhatsApp (número compartido de
Atentina; se identifica al usuario por su `wa_id`). Lo propio de cada negocio vive en una **app**:
un contenedor generado desde una plantilla común y modificado para ese cliente por un agente de
código (modelo de terceros, solo al construir). La app guarda los datos, expone herramientas por MCP
al asistente y muestra vistas web que el dueño abre con un link.

```text
dueño ──WhatsApp──► app de Atentina ──MCP (red interna)──► contenedor de la app del cliente
                       │  asistente: LLM local + herramientas      ├─ /api    API propia (FastAPI)
                       │                                           ├─ /mcp    herramientas para el asistente
                       │                                           ├─ /views  vistas HTML (datos en vivo)
                       │                                           └─ SQLite en /data
dueño ◄── link ── apps.atentina.com.ar/{cliente}/{app}/{vista}/ ── gateway en Atentina ──┘
```

## 1. Decisiones

| Tema | Decisión | Por qué |
|---|---|---|
| Plantilla | **Núcleo como librería** (`atentina_app_core`) en una imagen base versionada; la app del cliente tiene solo su dominio | Si la plantilla se copia, cada app diverge y un arreglo de seguridad hay que hacerlo N veces. Con la librería, actualizar el núcleo es subir la versión de la imagen base |
| Base | SQLite en `/data/app.db` (volumen por app), WAL | Un archivo por cliente: backup trivial. Con 150 alumnos son miles de filas por mes |
| Exposición | **Los contenedores nunca son públicos.** Red interna sin salida a internet; solo `app` los ve | El código lo escribe un agente: se trata como no confiable |
| Vistas | **Páginas ya programadas en la app** (Jinja), que leen los datos al abrirse. No se genera HTML por pedido | Generar cada vez cuesta tokens y tiempo, y el LLM puede inventar filas |
| Link | Lo arma una **herramienta de la plataforma** (`abrir_vista`), no la app. El gateway de Atentina valida el token y hace de proxy | Revocación, vencimiento y auditoría en un solo lugar; la app no maneja secretos públicos |
| URL | `https://apps.atentina.com.ar/{cliente}/{app}/{vista}/`, no `atentina.com.ar/apps/...` | `atentina.com.ar` es la landing en Render ([`LANDING.md`](../LANDING.md)); el subdominio sale por el túnel como `app.` |
| Registro | El script de deploy registra la app por la API de Atentina; Atentina lee su `/manifest` | `app` **no** monta el socket de Docker (equivale a root en el host) |
| Modelo | Inventario como los números: una app existe, se asigna a un cliente y sus herramientas se eligen en el agente | Mismo patrón que `phone_numbers` (libre → cliente → agente) |
| Confirmación | Cada herramienta declara `read`, `write` o `send`; la plataforma decide qué confirmar | No depende de que el LLM se acuerde de preguntar |

## 2. La app (contenedor)

### Estructura del repositorio de una app

```text
atentina.yaml           manifest (sección 3)
app/models.py           tablas (SQLAlchemy)          ← agente de código
app/services.py         lógica del negocio           ← agente de código
app/api.py              rutas REST                   ← agente de código
app/tools.py            herramientas MCP             ← agente de código
app/views/*.html        vistas (Jinja)               ← agente de código
migrations/             Alembic                      ← agente de código
seed.py                 datos de prueba (nunca reales)
tests/                  tests propios (obligatorios)
Dockerfile              FROM atentina/app-base:<versión>; no se toca salvo el perfil react
```

El núcleo (`atentina_app_core`, en la imagen base) trae y el agente no toca: arranque de FastAPI,
auth de la plataforma, `/health`, `/manifest`, montaje de `/mcp`, motor SQLite (WAL, `foreign_keys`),
`alembic upgrade head` al arrancar, backup, logs en JSON, layout y CSS base de las vistas, y los
tests de contrato.

### Endpoints

| Ruta | Quién la usa | Qué hace |
|---|---|---|
| `GET /health` | Atentina, cada minuto | `{"ok": true, "version": "…", "db": "ok"}` |
| `GET /manifest` | Atentina, al registrar y en cada versión | El `atentina.yaml` validado, con la lista de herramientas |
| `POST /mcp` | Asistente | MCP por Streamable HTTP, sin estado (`stateless_http`) |
| `/api/...` | Herramientas, vistas, futuro frontend React | API propia; OpenAPI en `/api/openapi.json` |
| `GET /views/{vista}` | Gateway | HTML de la vista con datos del momento; parámetros por query |
| `GET /static/...` | Gateway | CSS, imágenes y JS del núcleo o de la app |
| `POST /jobs/{nombre}` | Scheduler de Atentina | Corre un aviso programado (sección 5) |
| `POST /_platform/backup` | Cron de backup | `VACUUM INTO /data/backups/app-<fecha>.db` |

**Auth:** todo pedido trae `Authorization: Bearer <APP_TOKEN>` (secreto por app, generado al
registrarla, guardado cifrado en Atentina e inyectado como variable de entorno). Además viajan
`X-Atentina-Actor` (quién: `user:<id>`, `wa:<wa_id>`, `link:<id>`, `job:<nombre>`) para que la app lo
guarde en su auditoría, y `X-Forwarded-Prefix` (`/{cliente}/{app}`) para que las vistas armen URLs
relativas.

### Herramientas (MCP)

Se declaran con el decorador del núcleo sobre funciones de `services.py`, no sobre rutas HTTP: una
sola implementación, que usan la API y las herramientas.

```python
@tool(kind="read")
def buscar_alumno(texto: str) -> list[AlumnoCandidato]:
    """Busca alumnos por nombre aproximado. Devuelve candidatos con un puntaje; si hay más de uno
    parecido, el asistente pregunta cuál."""

@tool(kind="write")
def registrar_asistencias(fecha: date, ingresos: list[Ingreso]) -> Resultado: ...
```

- `kind` se traduce a las anotaciones de MCP: `read` → `readOnlyHint`; `write` →
  `destructiveHint=false`/`true` según el caso; `send` → `openWorldHint` (llega a terceros).
- **Límites del contrato:** hasta 20 herramientas por app y descripciones de hasta 400 caracteres.
  El LLM corre con 16.384 tokens por pedido y las herramientas van en cada uno.
- Respuestas en JSON chico: listas paginadas (tope 50 ítems) y totales calculados por la app, nunca
  por el LLM.
- Errores con un código y un mensaje para el usuario (`ambiguo`, `no_encontrado`, `invalido`).

### Vistas

- **Perfil `basic` (por defecto):** Jinja renderizado en el servidor, con el layout y el CSS del
  núcleo (mobile primero, sin CDN, sin JS obligatorio). Solo lectura en la v1: cambiar datos se hace
  hablando con el asistente.
- **Perfil `react` (más adelante):** el `Dockerfile` agrega un paso de build (Vite) que deja el
  build en `/app/ui`; el núcleo lo sirve en `/ui/` y las vistas del manifest apuntan a rutas del
  front. La API ya existe; el gateway y los links no cambian.

### Contenedor

- Usuario sin privilegios, `read_only: true`, `tmpfs: /tmp`, volumen solo en `/data`,
  `cap_drop: [ALL]`, `no-new-privileges`.
- Topes por defecto: 192 MB de RAM, 0,5 CPU, 128 procesos. Se cambian en el manifest.
- Red `atentina-apps` (`internal: true`): solo `app` y las apps. Sin internet, sin `db`, sin
  inferencia.
- Un worker de uvicorn.
- Estimado de RAM sin carga: ~60–90 MB por app, sin medir. Medido el 11-oct-2026 en este host: un
  Postgres sin carga ocupa 54–59 MB, y la `app` de Atentina 156 MB.

## 3. Manifest (`atentina.yaml`)

```yaml
spec: 1                        # versión de esta especificación
slug: sugym-gestion            # único; nombre del contenedor y del volumen
name: Gestión SUGYM
version: 0.3.0                 # = tag de la imagen
core: 1.2.0                    # versión de atentina_app_core
profile: basic                 # basic | react
description: Alumnos, asistencias, cuotas y pagos del gimnasio.
views:
  - name: asistencias-hoy
    title: Asistencias de hoy
    params: {fecha: {type: date, default: today}}
  - name: vencimientos
    title: Cuotas por vencer
    params: {dias: {type: integer, default: 7, max: 60}}
  - name: alumno
    title: Ficha del alumno
    params: {id: {type: integer, required: true}}
    access: pin                # link + PIN (datos sensibles)
jobs:
  - name: resumen-vencimientos
    cron: "0 8 * * 1-6"        # zona: BILLING_TIMEZONE
    notify: owner              # el resultado va por WhatsApp al dueño
resources: {memory: 192m, cpus: 0.5}
egress: []                     # dominios permitidos hacia internet (v1: ninguno)
```

Las herramientas no van en el manifest: `/manifest` las agrega leyéndolas del registro de MCP, así
nunca se desincronizan.

## 4. Lado de Atentina

### Tablas nuevas

| Tabla | Claves y reglas |
|---|---|
| `apps` | `slug` único, `client_id` (NULL = inventario), `base_url` (`http://app-<slug>:8000`), `token_enc` (cifrado, como `wa_accounts`), `version`, `manifest` (JSONB, copia del último leído), `status` (`ok`, `down`, `invalid`), `last_health_at` |
| `app_versions` | `(app_id, version)`, manifest, fecha y quién la publicó. Para auditar y volver atrás |
| `app_links` | `token_hash` único (SHA-256), `app_id`, `scope` (`view` o `app`), `view` (NULL si es la app entera), `params`, `expires_at`, `revoked_at`, `pin_hash` (si la vista es `access: pin`), `created_by` (`wa:`/`user:`), `opens`, `last_opened_at` |

**Agente:** la definición suma `tools: [{"app": "sugym-gestion", "tools": ["buscar_alumno", ...]}]`.
Al guardar se valida contra el manifest. Al publicar una versión de la app que saca una herramienta
usada por un agente, el registro falla (o pide forzar).

### API y UI (admin)

- `POST /api/v1/apps` (registro, lo llama el deploy con una key de admin): Atentina lee `/health` y
  `/manifest`, valida el contrato y guarda o actualiza la app y su versión.
- `GET /api/v1/apps` y una pantalla de listado: estado, versión, cliente, vistas y herramientas.
- `PATCH /api/v1/apps/{id}` para asignarla a un cliente o devolverla al inventario.
- En el formulario del agente, una sección **Herramientas**, con las herramientas de las apps del
  cliente.
- `GET/DELETE /api/v1/apps/{id}/links` para ver y revocar links.

### Herramientas de la plataforma

Se suman a las de las apps; no las escribe nadie por cliente.

| Herramienta | Tipo | Qué hace |
|---|---|---|
| `abrir_vista(app, vista, params)` | read | Crea un `app_links` y devuelve la URL. El esquema se arma desde el manifest (`vista` es un enum) |
| `preparar_mensaje(destinatarios, texto)` | send | Deja el envío pendiente; sale con el "sí" del usuario (fase posterior) |

### Bucle del asistente (requisito previo, se diseña aparte)

Identidad (`wa_id` → usuario → cliente → agente) y modo operador; el LLM local pide herramientas
(nativo con `--tool-call-parser gemma4` o con el `json_schema` actual, según un eval); tope de pasos
por turno; prioridad baja en vLLM. Política de confirmación por `kind`:
- `read` se ejecuta;
- `write` se ejecuta y se informa (deshacer, si la app lo soporta);
- `send` queda pendiente.

## 5. Links, gateway y avisos

### Link

1. `abrir_vista` genera 32 bytes aleatorios, guarda su hash y devuelve
   `https://apps.atentina.com.ar/{cliente}/{app}/{vista}/?k=<token>`. Vence a los 7 días por
   defecto (el manifest puede acortarlo); un link `scope: app` (el "panel") puede durar más.
2. Primer pedido con `k`: el gateway lo valida (hash, cliente, app y vista, vencido y revocado).
   Pone una cookie `ak` (HttpOnly, Secure, SameSite=Lax, `Path=/{cliente}/{app}/`, vida = lo que le
   queda al link) y redirige (303) a la misma URL sin `k`. Así el token no queda en el historial ni
   en el `Referer`.
3. Con `access: pin`, antes de la cookie pide el PIN (5 intentos y bloqueo).
4. Los pedidos siguientes (otra fecha, `/static`) usan la cookie.

¿"Público para quien tiene la URL"? Es lo mismo que un token, pero sin vencimiento ni revocación.
La propuesta es esa idea con vencimiento, revocación y PIN opcional.

### Gateway

- Ruta de `app` solo para el host `apps.atentina.com.ar`: con ese host no responde el panel ni la API.
- Solo GET y HEAD en la v1.
- Proxy con `httpx` a `base_url` + `/views/{vista}` o `/static/...`, con `APP_TOKEN`,
  `X-Atentina-Actor: link:<id>` y `X-Forwarded-Prefix`.
- Headers que **pone el gateway** (no confía en la app):
  - `Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`;
  - `Referrer-Policy: no-referrer`, `X-Robots-Tag: noindex`, `Cache-Control: private, no-store`.
- Túnel: ruta `apps.atentina.com.ar` → `http://localhost:8011`, que la crea el usuario, como las
  demás ([`LANDING.md`](../LANDING.md)).
- **Mismo sitio que el panel:** `apps.` y `app.` son "same-site". La cookie de sesión del panel
  es host-only y con `path=/api`, así que no viaja a `apps.`. Un POST desde `apps.` al panel lo
  corta el chequeo de `Origin` (`app/api/http.py`). Alcanza para la v1. Si las apps pasan a tener
  JS propio con formularios, mover el gateway a un dominio aparte (como hace Google con
  `googleusercontent.com`).

### Avisos programados

El scheduler de Atentina (en el lifespan de `app`, como el barrido de WhatsApp) corre los `jobs` del
manifest:
- `POST /jobs/{nombre}` → `{"message": "...", "view": {"name": "vencimientos", "params": {...}}}`;
- Atentina se lo manda al dueño por WhatsApp, con un link si trae vista;
- fuera de la ventana de 24 h, por plantilla (Utilidad).

La app nunca manda mensajes ni sale a internet.

## 6. Ciclo de vida

### Crear o cambiar una app (agente de código)

1. El pedido del cliente queda escrito (lo arma el asistente o el admin).
2. El agente de código (modelo de terceros, p. ej. Claude Code) trabaja en un contenedor de build:
   - parte del repositorio de la app, o de la plantilla si es nueva;
   - lee `SPEC.md` (esta especificación, versión para el agente) y el `CLAUDE.md` de la plantilla;
   - **nunca ve datos reales:** usa `seed.py`. A terceros va el código y el pedido, no los datos
     del cliente.
3. Puerta automática, `make check`:
   - lint y tests propios;
   - tests de contrato del núcleo: manifest válido, `/health`, herramientas dentro de los límites y
     con `kind`, cada vista renderiza con la seed, migraciones de ida y vuelta, cada job responde.
4. **Revisión del admin** del diff y de las capturas de las vistas (al principio, siempre).
5. Deploy:
   - `make app-deploy APP=<slug>`: build de la imagen con tag de versión;
   - backup de `/data`;
   - parar la versión vieja y arrancar la nueva (las migraciones corren al arrancar);
   - si `/health` no da ok en 30 s, volver a la imagen y al backup anteriores;
   - por último, `POST /api/v1/apps` (registro).
   - Unos segundos sin servicio: aceptable por WhatsApp.

### Operación

- **Salud:** Atentina pide `/health` cada minuto; con 3 fallas, `status=down` y aviso en el chequeo
  de `scripts/ops/healthcheck.sh`.
- **Backup:** el cron diario (03:30) llama a `/_platform/backup` de cada app y copia `/data/backups`
  a `~/atentina-backups/apps/<slug>/`.
- **Actualizar el núcleo:** subir `atentina/app-base`, rebuild de cada app, `make check` y deploy.
  Lo hace un script, app por app.
- **Baja:** se desactiva y se archiva el volumen; no se borra.

## 7. Fases

| Fase | Contenido | Resultado |
|---|---|---|
| 0. Plantilla | `atentina_app_core`, imagen base, tests de contrato, `SPEC.md`; la app de SUGYM **a mano** (alumnos, asistencias, 3 vistas) | La especificación probada con un caso real |
| 1. Registro | Tablas, red `atentina-apps`, `app-deploy`, `POST/GET/PATCH /apps`, salud, listado en la UI | Las apps aparecen y se asignan |
| 2. Asistente | Bucle con herramientas MCP, modo operador por `wa_id`, confirmación por `kind`, eval de llamados con Gemma | El dueño registra y consulta por WhatsApp |
| 3. Vistas | Gateway, `app_links`, `abrir_vista`, PIN, túnel `apps.` | El dueño abre "vencimientos" desde un link |
| 4. Avisos y backup | Scheduler de `jobs`, cron de backup | Resumen diario por WhatsApp |
| 5. Agente de código | Contenedor de build, flujo pedido → diff → revisión → deploy | La segunda app sale de la plantilla |
| 6. Perfil `react` | Build de Vite en la imagen, `/ui/` | Solo cuando un cliente lo necesite |

## 8. Decisiones del usuario (12-oct-2026)

- **Un solo repositorio para todas las apps**, con `make` por app (build, levantar, etc.). Va aparte
  de este repo (`/home/laureano/atentina-apps`), para que el agente de código no vea el `.env` ni el
  código de Atentina.
- **MVP sin cobro.**
- **Alcance del MVP:**
  - la integración completa;
  - la imagen base con la plantilla y una vista diaria tipo minuta (los alumnos que vinieron en el
    día);
  - la API y el MCP de la app de SUGYM;
  - la integración con el agente de Atentina.
  - Quedan afuera: PIN, `jobs`, `app_versions`, perfil `react`, agente de código automático, pagos y
    cuotas.

## 9. Contrato v1 (MVP)

Lo implementan las dos partes; si cambia, se cambia acá primero.

### App (puerto 8000 del contenedor)

Todo pedido trae `Authorization: Bearer <APP_TOKEN>`; si no, 401 (también `/health`).

| Ruta | Respuesta |
|---|---|
| `GET /health` | `{"ok": true, "version": "0.1.0", "core": "0.1.0"}` |
| `GET /manifest` | `{"spec": 1, "slug", "client", "name", "version", "core", "description", "views": [{"name", "title", "description", "params": {"<p>": {"type", "default", "description"}}}], "tools": [{"name", "description", "kind", "input_schema"}]}` |
| `POST /mcp` | MCP por Streamable HTTP, `stateless_http` y `json_response` (respuesta JSON, no SSE). Herramientas con anotaciones |
| `GET /views/{vista}?<params>` | `text/html`. Las URLs internas se arman con `X-Forwarded-Prefix` (`{prefix}/{vista}/?fecha=…`, `{prefix}/static/…`); sin el header, prefijo vacío |
| `GET /static/{archivo}` | CSS e imágenes |

- **`kind` → anotaciones de MCP:**
  - `read`: `readOnlyHint=true`;
  - `write`: `readOnlyHint=false`, `destructiveHint=false`;
  - `destructive`: `destructiveHint=true`;
  - `send`: `openWorldHint=true`.
- **Qué hace Atentina con cada `kind`:** `read` y `write` se ejecutan; `destructive` y `send` se
  confirman con el usuario antes.
- **Resultado de una herramienta:** JSON en `structuredContent` (y el mismo JSON como texto). Un
  error de negocio va con `isError: true` y un texto para el usuario.
- **Headers de Atentina:** `X-Atentina-Actor` (`wa:<wa_id>`, `link:<id>`, `admin`), que la app guarda
  en sus registros.

### Repositorio `atentina-apps`

```text
core/                  paquete atentina_app_core (FastAPI, auth, SQLite, MCP, vistas, contrato)
base/Dockerfile        imagen atentina/app-base:<versión del core>
skeleton/              app nueva (make new)
clients/<cliente>/<app>/
  atentina.yaml        slug, client, name, version, description, views
  app/ ...             modelos, servicios, herramientas, vistas, migraciones, tests
secrets/<slug>.env     APP_TOKEN (no versionado)
SPEC.md                la especificación para el agente de código
Makefile               make <target> A=<cliente>/<app>
```

Targets: `new`, `base`, `build`, `test`, `up`, `down`, `logs`, `sh`, `backup`, `register` y `deploy`
(test + build + backup + up + salud + register). `dev` levanta la app en el host con datos de
prueba, para desarrollo.

El contenedor se llama `app-<slug>`, en la red `atentina-apps` (`internal`, externa a los dos compose:
la crea `make network` de cada repo). Datos en el volumen `app-<slug>-data`.

### Atentina

| Pieza | Detalle |
|---|---|
| Tablas | `apps` (slug, client_id NULL = inventario, base_url, token_enc con `WA_TOKEN_KEY`, version, manifest, status, last_health_at, last_error); `app_links` (token_hash, app_id, view, params, expires_at, revoked_at, created_by, opens, last_opened_at); `wa_operators` (account_id + wa_id únicos, client_id, agent_id, name, active) |
| API | `POST /apps` (registro: admin, o `APPS_DEPLOY_TOKEN` desde `make register`, porque las API keys son siempre de un cliente): Atentina pide `/health` y `/manifest` con el token y guarda. `GET /apps`, `GET /apps/{id}`, `PATCH /apps/{id}` (cliente o inventario), `POST /apps/{id}/refresh`; `GET/POST/PATCH/DELETE /wa-operators` |
| Agente | Motor nuevo `assistant` (sin datos a extraer): `tools: [{"app": "<slug>", "tools": ["*"]}]`. El LLM responde en `json_schema` con una de: `reply`, `call` (herramienta + argumentos según su esquema), `confirm` y `cancel` (de la acción pendiente). Hasta 6 pasos por turno |
| Plataforma | Herramienta `abrir_vista(app, vista, params)` → `https://<APPS_PUBLIC_HOST>/{cliente}/{app}/{vista}/?k=<token>`. Vence a los 7 días (`APPS_LINK_TTL_DAYS`) |
| WhatsApp | Si el `wa_id` del que escribe está en `wa_operators` para ese número, la conversación usa el cliente y el agente del operador. Si no, el agente del número, como siempre |
| Gateway | `APPS_PUBLIC_HOST` (`apps.atentina.com.ar`): con ese Host, `app` atiende solo el gateway (sección 5). Solo GET; con el token del link pone una cookie con path y redirige |

### Contrato v1.1 (12-oct-2026: SUGYM completo, sin Mercado Pago ni cobro automático)

Se suma a la v1; las apps 0.1 siguen andando.

- **Mensajes a terceros (outbox).** La app no manda nada. Una herramienta `send` (se confirma antes)
  deja los mensajes en el outbox del núcleo y devuelve
  `{"outbox": [{"ref", "to", "text", "tipo"}], ...}`. Atentina los entrega y avisa el resultado con
  `POST /outbox/{ref}` `{"estado": "enviado" | "simulado" | "error", "detalle", "wamid"}`.
  - Modo `APPS_OUTBOX_MODE`: `simulate` por defecto (no sale nada, se registra como simulado) o
    `whatsapp` (texto por el número del chat del operador; fuera de la ventana de 24 h, Meta lo
    rechaza: plantillas, después).
- **Avisos programados (jobs).** En el manifest:
  `"jobs": [{"name", "title", "hora": "HH:MM", "dias": [1..7]}]` (ISO, 1 = lunes; sin `dias`,
  todos). A esa hora (zona `ASSISTANT_TIMEZONE`), Atentina hace `POST /jobs/{name}` →
  `{"message": str | null, "view": {"name", "params"} | null}`.
  - Si hay `message`, se lo manda a los operadores activos del cliente, con el link de la vista si
    viene, en el mismo modo que el outbox.
  - Una corrida por día y job (`app_job_runs`). El admin la puede disparar a mano.
- **Exportar.** `GET /views/{vista}?formato=csv` puede devolver `text/csv` (UTF-8 con BOM, separador
  `;`, para Excel) con `Content-Disposition: attachment`; el gateway lo deja pasar.
- **Archivos (solo Atentina).** Una imagen o PDF que manda un operador a un agente `assistant` se
  baja, se pasa por OCR (tesseract `spa`, en la CPU de `app`) y entra al turno como
  `[archivo recibido · sha256 <hex>]` + el texto leído. Qué significa lo decide la app. SUGYM lo
  trata como comprobante y recibe el hash en `comprobante_hash` para detectar duplicados. Leer un comprobante no confirma el pago: queda
  `por_verificar` hasta que el dueño lo confirma.
- **Vistas en el catálogo:** una sola herramienta de plataforma por app, `abrir_vista` (vista
  como enum + parámetros), en lugar de una por vista: menos tokens en cada paso.
- **Ambigüedad.** Una herramienta de consulta puede devolver `"ambiguo": true` (por ejemplo,
  `buscar_alumno("Juan")`). En ese turno Atentina no deja escribir nada: el asistente tiene que
  preguntar.
- **Links de vistas.** El LLM no ve la URL de `abrir_vista`, ve una marca `[[linkN]]` que Atentina
  cambia en la respuesta (y la agrega al final si el LLM no la puso).

### Contrato v1.2 (12-oct-2026: planes y precios de SUGYM)

- **Formularios.** Una vista con `form: true` en el manifest recibe `POST /views/{vista}` (urlencoded,
  hasta 64 KB) y responde `303` a la vista (`guardado=1`) o la vista con el error. Es para la
  configuración que no tiene sentido dictar: en SUGYM, los planes y precios (el dueño los cambia
  algunos meses). El gateway reenvía el POST solo con la cookie del link de esa vista y con `Origin`
  del gateway; el resto de las vistas sigue siendo de solo lectura.

### Contrato v1.3 (12-oct-2026: perfil del alumno en SUGYM)

- **Link desde una herramienta.** El resultado de una herramienta de la app puede traer
  `"view": {"name", "params"}`, como la respuesta de un job. Atentina crea el link firmado con el actor
  del turno (solo con los parámetros que la vista declara) y el LLM ve la marca `[[linkN]]`. Así "mostrame
  el perfil de Carlos" es una sola herramienta (`perfil_alumno`, con `editar` para abrirla en edición):
  un resumen corto que escribe la app y el link, en vez de buscar el `alumno_id` y después `abrir_vista`.

### Contrato v1.4 (13-oct-2026: SUGYM navegable)

- **App navegable.** `navigation: true` en el manifest: la cookie del link abre todas las vistas de la
  app, no solo la del link, y el núcleo pone una barra con la marca y el menú de secciones (drawer;
  las vistas sin parámetros obligatorios), el "Volver" (`data-back`) y las filas que llevan a otra vista (`tr[data-href]`), con
  `static/core.js` (la CSP no deja scripts en línea). En SUGYM, la lista de alumnos busca por nombre y
  cada fila abre el perfil. Un link vale para toda la app, así que solo va a los operadores.

## 11. Implementación del MVP (12-oct-2026)

**atentina-apps** (`/home/laureano/atentina-apps`, `git init` sin commits):
- núcleo `atentina_app_core` 0.1.0 (FastAPI, SQLite, `mcp==1.30.0` con FastMCP; la 2.x cambia la
  API);
- imagen `atentina/app-base:0.1.0` (`python:3.12.15-slim`), `skeleton/` y
  `clients/sugym/gestion/` (10 herramientas y la vista `minuta`);
- tests: 22 dentro de la imagen (12 de la app y 10 de contrato).
- Medido: el contenedor usa 78 MB de RAM sin carga.
- Desvíos del contrato:
  - los parámetros de vista traen además `required`, `min` y `max`;
  - `/{vista}/` sirve lo mismo que `/views/{vista}` (para desarrollo);
  - `make dev` publica `127.0.0.1:18001` y por eso arranca en `bridge` (con internet) antes de unirse
    a `atentina-apps`; `make up` usa solo la red interna.

**Atentina:**
- migración 0013 y API: `/apps`, `/wa-operators`;
- motor `assistant` (`app/conversation/assistant.py`), `app/apps/`, gateway y ruteo de operadores en
  WhatsApp;
- red `atentina-apps` en el compose (`make apps-network`, `deploy/boot.sh`) y panel (Apps,
  Operadores, motor y herramientas en el agente);
- tests: `tests/test_apps.py` y `test_migration_0013.py`.

**Prueba de punta a punta** (`scratch/apps_e2e.py`): base SQLite propia, la app real en `make dev` y
Gemma 4 26B real. 8 turnos de WhatsApp de un dueño:

| Pedido | Resultado | Tiempo |
|---|---|---|
| Registrar 3 ingresos con hora | Una llamada a `registrar_asistencias` con los 3 nombres | 3,1 s |
| ¿Quiénes vinieron hoy después de las 8? | `asistencias_del_dia` y listado | 2,1–2,4 s |
| "Juan, el que hace musculación, a las 9:40" | `buscar_alumno` → Juan Pérez (no Pereyra) → registro | 1,1 s |
| Veces de María este mes y última | `resumen_alumno` | 0,8 s |
| ¿Quiénes no vienen hace más de 10 días? | `ausentes` | 1,0 s |
| Pasame la minuta | `vista_minuta` → link; el gateway sirve el HTML (200, con CSP) | 1,2 s |
| Dar de baja a Carlos Gómez, y "sí" | Busca, queda pendiente, confirma y ejecuta | 1,3 s y 0,5 s |

Antes de los controles de la plataforma, Gemma tuvo dos fallas graves:
- inventó un link (`gym-management.com/...`) en vez de pedir la vista;
- mandó la baja con `alumno_id` 3 (María López) mientras le preguntaba al usuario por Carlos Gómez,
  así que el "sí" habría dado de baja a otra persona.

Los dos controles de `assistant.py` (sección 4 del motor en
[`ARQUITECTURA.md`](../ARQUITECTURA.md)) los corrigen sin depender del prompt. Con 8 turnos no hay tasa
de error: falta un eval con más casos (nombres mal transcriptos, audios, ambigüedad).

### Para desplegar (confirmar antes: recrea `app`)

1. `.env` de Atentina (diff enmascarado antes de reiniciar):
   - `APPS_PUBLIC_HOST=apps.atentina.com.ar`;
   - `APPS_DEPLOY_TOKEN` (`openssl rand -hex 32`);
   - `WA_TOKEN_KEY`, que ya está.
2. `make up-app`: crea la red, corre la migración 0013 y recrea `app`. Corta los turnos de WhatsApp
   en curso; las llamadas no, porque no toca `agent`.
3. En atentina-apps:
   - `.env` con `ATENTINA_URL=http://127.0.0.1:8011` y `ATENTINA_DEPLOY_TOKEN`;
   - `make down A=sugym/gestion` (el de desarrollo tiene el puerto publicado y la seed);
   - borrar su volumen;
   - `make deploy A=sugym/gestion`.
4. Lo hace el usuario: ruta del túnel `apps.atentina.com.ar` → `http://localhost:8011` (como
   `app.`).
5. En el panel:
   - cliente SUGYM; asignarle la app;
   - agente con motor `assistant` y la app en Herramientas;
   - operador: el número de WhatsApp de Atentina, el `wa_id` del dueño y ese agente.
6. Carga inicial de los alumnos reales: falta (hoy, de a uno por el asistente). Próximo paso: importar
   desde la planilla del gimnasio.

### SUGYM completo (contrato v1.1, 12-oct-2026)

App 0.2.0 (núcleo 0.2.0):
- 15 herramientas: alumnos, asistencias, ficha única, seguimiento, cuotas y períodos (el
  vencimiento separado del fin), pagos en efectivo y por transferencia con duplicados y verificación,
  caja, y mensajes por el outbox;
- 6 vistas, 4 con CSV;
- el job `resumen_diario`;
- seed de 130 alumnos y 8 semanas;
- 39 tests.

En Atentina:
- outbox (`app/apps/outbox.py`, simulado por defecto) y jobs (`app/apps/jobs.py`, migración 0014);
- OCR de archivos (`app/apps/attachments.py`, tesseract en la imagen de `app`);
- CSV por el gateway;
- una sola `abrir_vista`;
- los `anyOf` con null aplanados: las herramientas pasan de 11.400 a 6.500 caracteres en el prompt.

**Casos de uso** (runner genérico `scripts/apps/casos.py`; los casos son de la app, en
`atentina-apps/clients/sugym/gestion/casos/casos.yaml` con sus archivos de prueba; se corren con
`make casos A=sugym/gestion` desde atentina-apps): 37 conversaciones con los pedidos del cliente, más
el aviso diario, contra Gemma 4 26B, la app con la seed y el OCR. Comprobantes sintéticos de Mercado
Pago y Galicia, y uno repetido.

| Corrida | Resultado | Qué se corrigió |
|---|---|---|
| 1 | 34/38 | 2 chequeos mal escritos. En 5.4 el LLM inventó los `alumno_id` de los mensajes (el control lo frenó) y preguntó en texto antes de usar la herramienta. 4.4 no encontró el pago a verificar. 2.1 dijo "ya le mandé" un envío simulado |
| 2 | **38/38**, 0,6–4,1 s por turno (5.4: 8,4 s, 7 mensajes) | La respuesta anterior lleva los resultados de sus herramientas. Los envíos van directo a la herramienta (confirma el sistema). Se aclara cuando algo es simulado. Fechas en dd/mm. `verificar_pago` acepta el alumno |

| 3 (prueba del usuario por WhatsApp, con audio) | — | "Vino Juan a las diez" registró a Juan Pérez sin preguntar. Las horas dichas en palabras no llegaban a `hora` (registraba la de ese momento y ponía "vino a las diez" en la observación). Inventó la observación "Ingreso por nota de voz". "Mariel López" listaba candidatos lejanos |
| 4 (+2 casos de audio) | 38/40 | 1.3c registró **a los dos Juanes**. 6.3 copió mal el token del link (el control lo frenó: "link no disponible") |
| 5 | **40/40** | Control de ambigüedad y marcas `[[linkN]]` en la plataforma. Reglas de nombres, horas en palabras y observaciones en el prompt. Candidatos cercanos al mejor (`NEAR` 0,15) y horas más flexibles en la app (`10`, `8.05`, `8 y 5`) |

| 6 (prueba del usuario) | — | "Pablo Acosta pagó la cuota en efectivo" (sin importe): no registró el pago; **cambió su cuota a $15.000 inventados** con `editar_alumno` y dijo que lo había registrado. "Anotá… problema en la espalda": cambió su frecuencia a 1 (inventado) y pisó las observaciones |
| 7 (+2 casos) | **41/41** | `registrar_pago` sin importe usa el saldo de la cuota. `agregar_nota` aparte (16 herramientas, nuevo tope). `editar_alumno` pasa a `destructive`: se confirma mostrando qué cambia. Regla: nunca cambiar datos que el usuario no pidió |

| 8 (prueba del usuario) | — | "Pagó 25.000, no 47.000": no había forma de corregir y registró un segundo pago (adelanto de noviembre); octubre quedó como pagado |
| 9 (+1 caso) | 41/42 | Con `corregir_pago` (`destructive`; tope de 20 herramientas) armó bien la corrección, pero ante "Sí" volvía a pedir la herramienta en vez de `confirm`, y seguía preguntando aunque el usuario cambiara de tema |
| 10 | **42/42** | Un "sí" o "no" claro a una acción pendiente lo resuelve la plataforma (regex), no el LLM; con cualquier otra cosa decide el LLM |

| 11 (prueba del usuario) | — | Un pago iba a la cuota impaga más vieja (agosto) sin decirlo. "Es de septiembre": `corregir_pago` no podía cambiar la cuota y el asistente **dijo que lo había corregido**. En el celular la vista de cuotas escondía el saldo y mostraba el importe de la cuota ("sigue figurando 47.000"). Le llegó un `[[link1]]` literal. "¿Confirmás que quiero…?" |
| 12 (+3 casos y la vista `pagos`) | **46/46** | `corregir_pago` con `periodo` y sin cambios da error. `registrar_pago` devuelve `aplicado_a`. Filtro `deudores` (con saldo y vencida o que vence hoy). Saldo visible en el celular. Marca sin vista: el sistema pide la vista. Un "sí" es cualquier respuesta hecha solo de palabras de aceptación ("dale, mandalo"). Reglas: no afirmar lo que el resultado no muestra, hablar de vos, link si lo pide "en el celular" |

Las reglas del prompt solas no alcanzaron: lo que importa (quién es la persona y el link) lo
controla la plataforma.

**Cuotas por clases (SUGYM 0.3.0, 12-oct-2026, pedido del cliente).** No hay abono fijo: cada plan
(Nivel 1 y 2, de clase suelta a pase libre) da clases por mes, en cualquier día y horario. El mes va
de fecha a fecha o hasta la última clase; las que sobran pasan un mes si renueva antes de que
termine; quien viene sin mes pagado entra y queda debiendo. Todo se calcula desde las asistencias y
los pagos. Los planes y precios están en la base, con historial: un precio nuevo vale para los meses
que se abren después (quien debe meses viejos los paga al precio de entonces). Los casos de uso
pasaron a 50 (planes, renovaciones, plan ambiguo, vino sin pagar); falta correrlos. Falta repetirla (N=5) para tener una tasa, y probar con audios reales y
comprobantes fotografiados, no sintéticos.

**Alcance mínimo (SUGYM 0.4.0, 16-oct-2026, sin desplegar).** El primer día con el padrón real
(conversación `0c9dbde8`, por audios), el dueño cargó asistencias y planes de alumnos importados sin plan:
- los planes no se guardaron: 10 de 11 `editar_alumno` sin `plan`, con `dias_para_pagar` y
  `fecha_nacimiento` inventados, y el asistente decía "listo";
- confirmaciones en bucle;
- un alumno duplicado (`alta_alumno` con `forzar`);
- un pago que nadie pidió.

Reproducido con los casos 8.x (sus mensajes, con 11 alumnos sin plan en la seed) y repetido 5 veces:

| Config (Gemma 4 26B) | Casos 8.x OK | Guardado al terminar | Altas mal usadas | Duplicados | Turno p50 / p90 |
|---|---|---|---|---|---|
| 20 herramientas, razonamiento, temp. 1.0 | 4/40 | 19/70 planes | 27 | 3 | 6,2 / 10,9 s |
| Sin razonamiento, temp. 1.0 | 1/40 | 14/70 | 34 | 9 | 1,6 / 2,9 s |
| Sin razonamiento, temp. 0.2 | 4/40 | 12/70 | 43 | 11 | 1,5 / 2,5 s |
| 12 herramientas | 7/40 | 23/70 | 0 | 0 | 5,6 / 10,3 s |
| **7 herramientas, el plan y el alta por link** | **49/50** | **64/65 asistencias** | 0 | 0 | 4,5 / 9,0 s |

- Bajar la temperatura no ayuda: vuelve constante el error ("asignar plan" = `alta_alumno`). Google
  recomienda 1.0 para todo (ficha de Gemma 4) y el razonamiento mejora las llamadas.
- Diseño nuevo (`agente.yaml` de la app):
  - el asistente solo escribe asistencias, notas y pagos;
  - el plan, los datos y la baja los edita el dueño en el perfil, y el alta en la vista `alta`
    (formulario nuevo), con el link que le da el asistente;
  - `registrar_asistencias` registra aunque no haya plan y trae el link al perfil;
  - `perfil_alumno` reemplaza a `ficha_alumno`: los datos y siempre el link editable;
  - `registrar_pago` queda con alumno, medio, importe y fecha: confirmado y sin `forzar`, porque con
    `forzar` "ese pago es de septiembre" registraba un segundo pago (caso 2.5).
- Suite completa adaptada: 57/59 (7 casos omitidos: recibos, comprobantes, verificar, mensajes). Las 2
  fallas dependen de la hora (la seed trae asistencias de hoy).
- Queda en la plataforma:
  - con un nombre ambiguo en el turno, el control bloquea también los claros (8.5, 1 de 5);
  - un control que frena una llamada no impide que el LLM diga "registré" (8.5 y 2.3);
  - a veces el link al perfil sale de `abrir_vista` y no de `perfil_alumno`: falta poder elegir qué
    vistas ofrece cada agente.
- Desplegar: `make deploy A=sugym/gestion` (0.4.0) y la lista de herramientas de `agente.yaml` en el
  agente de producción, que hoy tiene `"*"`.

## 12. A decidir

1. ¿Una app por cliente o varias (por ejemplo, gestión y turnos)? El modelo permite varias; empezar
   con una.
2. ¿Quién paga el agente de código? El MVP no se cobra; después, ¿por pedido de cambio o abono?
   (Tokens de terceros, no la API de inferencia propia.)
3. Salida a internet (`egress`) para integraciones (Mercado Pago, Google): un proxy con lista de
   dominios permitidos, o las integraciones del lado de Atentina.
4. Vistas con formularios (escribir desde la web): necesitan CSRF y probablemente el dominio
   aparte; no en la v1.
