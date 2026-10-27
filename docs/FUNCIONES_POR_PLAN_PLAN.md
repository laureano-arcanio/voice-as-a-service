# Funciones por plan: bloquear en la UI lo que el plan no incluye

Plan del 24-oct-2026. Implementado el 24-oct-2026 (migración 0025), sin desplegar: ver la sección 5.

## 1. Problema

Un cliente Free entra a **Llamadas**, elige agente y teléfono, y el botón **Llamar** está habilitado. La API
responde 429 "No quedan minutos salientes" (le pasó a `lacocinadecharli` el 24-oct-2026, tres veces) y el
cliente no entiende por qué. Lo mismo pasa con otras funciones: la UI las muestra completas y el corte llega
recién al guardar, o no llega.

Hoy solo **Campañas** avisa lo que el plan no incluye (`GET /campaigns/plan` y el texto "Tu plan (X) no
incluye…" en `CampaignsPage.tsx`), y lo hace a su manera.

## 2. Qué limita hoy el plan (relevado el 24-oct-2026)

| Función | Pantalla | Campo del tier | Free hoy | ¿Lo corta el backend? |
|---|---|---|---|---|
| Llamadas salientes | Llamadas (`/outbound`) | `outbound_minutes`, `max_phone_numbers` | 0 y 0 | Sí: 429 `outbound_minutes` |
| Campañas | Campañas | `campaign_channels`, `max_campaigns_per_month` | `["whatsapp"]`, sin tope | Sí, por canal |
| Equipo y derivaciones | Equipo; Derivación en el agente | `max_team_members` (la transferencia, además, `outbound_minutes`) | sin tope | Sí: `team_members_limit` |
| WhatsApp (cuentas, mensajes, llamadas, ruteo) | WhatsApp; secciones de WA en el agente | **ninguno** | — | **No** |
| Contactos y agenda | Contactos | `max_contacts` | sin tope | Sí |
| Link para llamar | Agente → Link para llamar | `max_call_links` | sin tope | Sí |
| Números | (los asigna el admin) | `max_phone_numbers` | 0 | Sí |
| API de inferencia | API, Uso de la API | `api_*` | incluida (262.144 tokens, 20 min) | Sí |
| BYOK (Modelos) | Modelos; Modelo de lenguaje en el agente | **ninguno** | — | No |
| Apps | Apps | ninguno (las asigna el admin) | — | — |
| Grabación, resumen por email | Agente → Voz | ninguno | — | No |

Los 3 clientes Free (`fiestaiastudio`, `lacocinadecharli`, `Laureano QA`) no tienen cuentas de WhatsApp,
campañas, equipo, contactos, links ni BYOK: cerrar estas funciones no rompe nada en uso.

Desfasajes con la landing (`landing/src/data/site.ts`): Free dice "20 minutos, llamadas web, plataforma
web, API". El tier Free, en cambio, deja campañas de WhatsApp, equipo, contactos y links sin tope, y
WhatsApp sin control. "Llamadas programadas" figura solo en Sucursal, pero en la base los cuatro tiers
tienen las mismas `campaign_channels`.

## 3. Propuesta

### 3.1 Una sola fuente: las funciones del plan

`app/services/features.py`: a partir de `effective_limits` (ya respeta los ajustes por cliente) y de los
números asignados, calcula cada función del catálogo con su estado:

```python
FEATURES = ("outbound_calls", "campaigns_voice", "campaigns_whatsapp", "team", "whatsapp",
            "contacts", "call_links", "byok", "api")

@dataclass
class Feature:
    key: str
    enabled: bool
    reason: str | None   # por qué no, en lenguaje del cliente
    code: str | None     # outbound_minutes, no_phone_numbers, not_in_plan...
```

- `outbound_calls`: `outbound_minutes != 0` y al menos un número asignado al cliente.
- `team`: `max_team_members != 0`. `contacts`, `call_links`: `!= 0`. Campañas: canal en `campaign_channels`.
- `whatsapp` y `byok`: **campo nuevo** en el tier (sección 3.2).

El mismo módulo lo usan la API (para la UI) y los servicios (para el corte), así la UI y el backend no se
contradicen. Nada de "if tier == 'Free'": todo sale de los campos del tier, así un plan pago sin
números se comporta igual.

### 3.2 Base: lo que falta en el tier (migración 0025)

- `tiers.features` (JSON, lista de banderas sin número): `["whatsapp", "byok"]`. Default: todas
  (no cambia nada para Mostrador, Sucursal, Central ni Interno; Central se borró el 26-oct-2026).
- Free: `features = []`, `campaign_channels = []`, `max_team_members = 0`, `max_contacts = 0` y
  `max_call_links` según la decisión 4.3.
- Se edita en la pantalla Tiers (admin), con checkboxes.

### 3.3 API

- `GET /api/v1/plan/features` (cliente; el admin con `client_id`): `tier_name`, `free` (precio 0)
  y la lista de funciones con su estado. Reemplaza a `GET /campaigns/plan` para el bloqueo (ese endpoint
  sigue para los contadores de campañas).
- Corte en el backend donde hoy falta, con 403 `feature_not_in_plan`: alta de cuenta de WhatsApp y
  Embedded Signup, respuesta del agente a mensajes y llamadas de WA de un cliente sin la función, y alta
  de conexiones BYOK. El 429 de las llamadas queda como respaldo.

### 3.4 UI

- **`usePlanFeatures()`** (`web/src/features/billing/`): consulta una vez por sesión, con caché de
  TanStack Query; para el admin, todo habilitado.
- **`<PlanGate feature="outbound_calls">`** (`web/src/components/PlanGate.tsx`), el mecanismo de todas
  las pantallas:
  - **Arriba, un aviso compacto con borde amarillo**, sin relleno (24-oct-2026: el relleno era demasiado):
    "**Tu plan Free no incluye llamadas salientes.** Disponible en los planes Mostrador y Sucursal,
    con números asignados." y el botón **Mejorar mi plan** → `/plan`. Los planes salen de los tiers que
    incluyen la función (todos menos el suyo, los gratis y el interno; los que se venden primero); si
    ninguno, "Escribinos y la sumamos a tu plan".
  - **Debajo, el panel deshabilitado entero**: `<fieldset disabled>` (desactiva inputs, selects y
    botones de una vez) con opacidad reducida. Se ve qué haría la función, pero no se puede usar.
- **Dónde va:**

  | Pantalla | Qué se bloquea |
  |---|---|
  | Llamadas (`/outbound`) | El panel Nueva llamada entero (`NewCallForm`). La lista de llamadas pasadas, no. |
  | Campañas | Botón Nueva campaña y el modal, por canal (reemplaza el bloqueo actual) |
  | Equipo | Toda la pantalla; en el agente, la sección Derivación |
  | WhatsApp | Toda la pantalla; en el agente, ruteo y ventana de WhatsApp |
  | Contactos | Alta e importación (bloqueados y bajas siguen visibles) |
  | Agente → Link para llamar | Según 4.3 |
  | Modelos (BYOK) | Alta de conexión; en el agente, "Mis proveedores, por etapas" |

- **Navegación** (`components/nav.ts`, `AppShell`): con plan Free, `Badge` "Free" al lado del ítem
  **Plan**, para que se sepa en qué plan está el cliente. En cada ítem no incluido en el plan, un
  candado gris chico; el ítem sigue entrando a la pantalla, que muestra el alert. Así se ve de una pasada
  qué se puede usar.
- La prueba por navegador **no** se pierde: queda en Agente → Probar (`NewCallForm` con `fixedAgent`, solo
  modo prueba) y por el link para llamar. El alert de Llamadas lo dice: "Para probar tu agente,
  usá la pestaña Probar del agente".

### 3.5 Pruebas

- Backend: `tests/test_features.py` (cada función por tier y con ajuste por cliente) y el corte 403 de
  WhatsApp y BYOK.
- Web: `PlanGate.test.tsx` (alert y fieldset deshabilitado) y un test por pantalla con plan Free
  (`make web-check`).
- Capturas con plan Free y con Mostrador (`scratch/shots/shoot.mjs`, backend dev en :8111).

### 3.6 Despliegue

`make migrate-test`, `make migrate`, `make calls-active && make up-agent`. Al día: `GUIA_UI.md`
(qué ve un cliente Free), `DESIGN_GUIDELINE_APP.md` (componente `PlanGate`, candado de la navegación) y la
landing, si cambia lo que dice cada plan.

## 4. Decisiones (24-oct-2026)

1. WhatsApp en Free: bloqueado entero (cuentas, mensajes y llamadas). Bandera `tiers.whatsapp`.
2. Contactos y Equipo: configurables en el tier (`max_contacts`, `max_team_members`); 0 en Free. Los
   números bloqueados siguen disponibles (otra tabla).
3. Link para llamar: 1 en Free (`max_call_links`).
4. BYOK (Modelos): no se cierra; no lleva bandera.
5. Mostrador: sin campañas (`campaign_channels = []`).

## 5. Lo hecho y cómo desplegar

- Migración 0025: `tiers.whatsapp` (true en los existentes); Free queda con `whatsapp=false`, sin canales
  de campañas, `max_contacts=0`, `max_team_members=0` y `max_call_links=1`; Mostrador, sin campañas.
- `app/services/features.py` y `GET /api/v1/plan/features`. Corte de WhatsApp (`limits.check_whatsapp`,
  429 `whatsapp_not_in_plan`): alta manual y Embedded Signup; los mensajes de un plan sin WhatsApp quedan
  `ignored` ("plan sin WhatsApp") y la llamada de WhatsApp, rechazada.
- Desvío: una saliente sin número propio **no** se corta en la API (las campañas de voz y muchos tests
  marcan sin número; sale con `ANURA_DID`). Solo la UI la bloquea; el Free igual tiene 0 minutos salientes.
- UI: `PlanGate`/`PlanAlert`, `useFeatureLock`, candados y "Free" en la navegación, casilla WhatsApp en
  Tiers. Pantallas: Llamadas (panel entero), Campañas, Equipo, WhatsApp, Contactos; Inicio y Probar del
  agente, fijos en modo prueba.
- Falta: secciones de WhatsApp y Derivación dentro del editor del agente (se pueden editar, pero no tienen
  efecto sin la función).
- Desplegar: `make migrate-test`, `make migrate`, `make calls-active && make up-agent` (recrea `app` y
  `agent`; la UI se compila en la imagen de `app`).

## 6. Campañas de llamadas, contactos y equipo por plan (24-oct-2026)

Hasta acá ningún tier tenía `voice` en `campaign_channels`: una campaña de llamadas daba 429
`campaign_channel_not_in_plan` en todos, y la landing prometía "Llamadas programadas" en Sucursal y Red.
Decisión del usuario, en la migración 0026 (por nombre, sin CAP con Gemma todavía: concurrencia baja):

| Tier | Campañas | `max_campaign_concurrency` | `max_contacts` | `max_team_members` |
|---|---|---|---|---|
| Free | — | — | 0 | 0 |
| Mostrador | — | — | 500 | 1 |
| Sucursal | WhatsApp y llamadas | 1 | 5.000 | 2 (5 en la 0026; bajado a 2 por la API el 24-oct-2026) |
| Interno | WhatsApp y llamadas | sin tope | sin tope | sin tope |

- **26-oct-2026: el tier Central (Red en la landing; 5.000 minutos, 10 llamadas, campañas hasta 3, contactos y
  equipo sin tope) se borró de la base.** Quedan Free, Mostrador y Sucursal (públicos) e Interno. **Red** sigue
  en la landing como plan a medida: una instancia propia que cotiza un asesor, sin tier (todo y sin tope en las
  tablas de `/docs/api` y `/docs/mcp`). Sucursal pasó a incluir el agente propio y las herramientas (HTTP, 10,
  y código); la marca blanca queda solo en Interno (y Red, a medida).
- Las áreas de derivación no tienen tope por plan (decisión): sin personas en el equipo no se transfiere.
- Landing: `/desarrolladores/docs` suma "Qué incluye cada plan" (con `GET /plan/features` y los 429),
  "Cortar y bloquear", "Equipo y derivaciones" y "Eventos"; las tarjetas de `landing/src/data/site.ts`
  listan WhatsApp, campañas, contactos y derivación. Al cambiar un tier, cambiar las dos.
- Desplegar: `make migrate-test`, `make migrate` (solo datos: no hace falta recrear servicios) y publicar
  la landing.
