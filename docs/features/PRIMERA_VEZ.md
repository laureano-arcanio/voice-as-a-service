# Primera vez: asistente, Inicio y llamada de prueba al celular

Para que un cliente nuevo escuche a **su** agente en menos de un minuto. Un usuario del cliente sin agentes ve el
asistente de primera vez en vez del panel: elige el rubro (y el sitio, opcional) y una de seis voces con retrato,
y el agente sale de la plantilla del rubro con el nombre de la empresa y la voz. Después entra a **Inicio**, con
sus agentes y dos accesos: hablarle desde el navegador o que lo llame a su celular verificado. Estado: hecho el
30-oct-2026, sin desplegar. El código por WhatsApp necesita una plantilla de autenticación aprobada por Meta.

Motivo: de los 13 registros Free (al 30-oct-2026) casi ninguno creó un agente ni lo probó. Entraban a Reportes
vacío, había una sola plantilla y probar por voz era un desvío al link para llamar.

## Modelo de datos

| Columna | Qué es | Migración |
|---|---|---|
| `clients.industry` | Rubro elegido en el asistente (`salud`, `gimnasio`, `inmobiliaria`, `gastronomia`, `cobranzas`, `otro`); `""` si no eligió | 0044 |
| `clients.website` | Sitio que cargó en el asistente, con `https://` | 0044 |
| `users.phone` | Celular en E.164: el del registro (sin verificar) o el verificado | 0044 |
| `users.phone_verified_at` | Cuándo lo verificó con el código por WhatsApp | 0044 |

- `CallMode.celular`: llamada de prueba al celular verificado. No está en `MINUTE_MODES`: **no gasta minutos del
  plan** ni cuenta en los topes de llamadas. Ocupa un canal de Anura (`ANURA_MODES`). En Reportes se suma a
  "prueba".
- El código no tiene tabla: como el del perfil, la API devuelve un desafío firmado
  (`security.create_account_code_token`, propósito `phone`, el celular en `new`) y se manda de vuelta con el código.

## Plantillas por rubro

`app/agents/templates/<id>.json`: `asistente` (el de "otro rubro"), `salud`, `gimnasio`, `inmobiliaria`,
`gastronomia` y `cobranzas`. Funcionan sin editarlas, con datos de ejemplo en la base de conocimiento (horarios,
precios, turnos) para que la prueba tenga sentido; el cliente los reemplaza por los suyos. Llevan `[EMPRESA]` y
`[AGENTE]`, que `fill_template` completa al crear el agente con el nombre del cliente y el de la voz (Sofía, Tomás).
Las ofrece también "Nuevo agente" (`GET /agent-templates`), con voz opcional (`AgentCreate.voice`).

## API

| Ruta | Qué hace |
|---|---|
| `GET /onboarding` | `has_agents` (sin archivar), rubro, sitio, celular del usuario y si está verificado, `verify_available` y las llamadas de prueba usadas (`trial`) |
| `GET /onboarding/industries` | Los rubros, en orden, con su plantilla |
| `POST /onboarding/agent` | `{industry, voice, website}`: guarda rubro y sitio y crea el agente "<voz> · <rubro>" (slug único) |
| `POST /onboarding/phone/code` | `{phone}`: manda el código por WhatsApp; devuelve el desafío. 503 `phone_verify_unavailable` sin la plantilla configurada |
| `POST /onboarding/phone/verify` | `{challenge, code}`: deja el celular verificado; 422 `invalid_code` |
| `POST /onboarding/call-me` | `{agent_id}`: el agente llama al celular verificado. 409 `phone_not_verified`, 429 `trial_calls` o `no_channel` |
| `POST /demo/signup` | Suma `phone` (opcional en la API, obligatorio en el formulario); 422 `invalid_phone` |

El código y la llamada son solo para un usuario del cliente (un admin en soporte da 403 `support_read_only`).

## Flujo

1. **Registro** (`landing/src/pages/registro.astro`): se suma "Celular". Queda en `users.phone`, sin verificar.
2. **Asistente** (`web/src/features/onboarding/OnboardingWizard.tsx`): `AppLayout` lo muestra a pantalla completa
   mientras `GET /onboarding` dice `has_agents: false`, salvo en `/plan` y `/profile` (pagar el plan elegido en el
   registro). Un admin que entró como el cliente ve el panel. Reemplaza al pop-up de bienvenida (lo marca visto).
   - Paso 1: rubro (tarjetas con ícono) y sitio.
   - Paso 2: seis voces (`FEATURED_VOICES`: sofia, paula, valentina, gonzalo, lucas, tomas) con retrato
     (`web/public/voces/<voz>.svg`, los mismos de la landing; `make voces-retratos`) y ▶ que dice la apertura con
     el nombre de la empresa (`POST /tts/preview`).
3. **Inicio** (`/inicio`, la pantalla de entrada del cliente; antes era Reportes): una tarjeta por agente con
   retrato, "Hablarle ahora", "Llamame" y "Editar"; "Crear otro agente"; próximos pasos (crear, hablarle, cargar la
   información del negocio, compartir el link) y las últimas cinco conversaciones. Con `?nuevo=<id>`, el aviso
   "¡Tu agente ya está listo!".
4. **Hablarle ahora** (`VoiceCallModal`): llamada de prueba por el navegador (`POST /calls` sin teléfono +
   `/calls/{id}/join`) con LiveKit, subtítulos en vivo y link a la conversación. No necesita el link para llamar.
5. **Llamame** (`CallMeModal`): si el celular no está verificado, manda el código por WhatsApp y lo verifica; después
   `POST /onboarding/call-me`. El worker marca con `trial` en la metadata y la llamada queda en modo `celular`.

## Reglas y trampas

- **Cupo de prueba por cliente, en total (no por mes):** `TRIAL_CALLS` (3) llamadas y `TRIAL_CALL_SECONDS` (300)
  segundos; cada llamada dura como máximo lo que queda. Con menos de 30 s, 429.
- **Solo al celular verificado:** sin verificación, cualquiera podría usar la plataforma para llamar a terceros.
  La verificación usa los topes del perfil (`ACCOUNT_CODE_SENDS_PER_HOUR`, `ACCOUNT_CODE_ATTEMPTS_15M`).
- **Caller ID:** el del primer número del cliente, o ninguno; Asterisk lo pisa con `ANURA_DID`.
- **Navegar antes de refrescar:** al crear el agente, el asistente navega a `/inicio?nuevo=` y recién después
  invalida `GET /onboarding`. Al revés, el panel aparece en `/` y su redirección a `/inicio` pisa la del asistente.
- Las plantillas son por rubro, no de un cliente (AGENTS.md): todo lo propio de la empresa lo completa
  `fill_template` o lo edita el cliente.

## Desplegar y probar

1. Pedir a Meta la plantilla de autenticación en la WABA de Atentina (categoría `AUTHENTICATION`, idioma `es_AR`,
   botón "Copiar código"). Con la aprobación, en `.env`: `PHONE_VERIFY_WA_NUMBER_ID` (el phone_number_id que la
   manda) y `PHONE_VERIFY_WA_TEMPLATE` (el nombre). Sin esas dos, el asistente funciona y "Llamame" avisa que se
   habilita en unos días.
2. `make migrate` (0044).
3. `make calls-active && make up-agent` (el worker reconoce `trial`) y recrear `app` y la web.
4. Desplegar la landing (campo de celular en `/registro`).
5. Probar: registrarse con un mail nuevo → asistente → Inicio → "Hablarle ahora" y "Llamame".

Tests: `tests/test_onboarding.py` y `web/src/features/onboarding/Onboarding.test.tsx`.

## Pendientes

- Armar el borrador del agente desde el sitio que cargó (`clients.website`): base de conocimiento, apertura y
  datos sacados del sitio, con protección SSRF como las herramientas.
- Mails según lo que haya hecho: sin agente a las 24 h, con agente pero sin hablarle, y uno personal al día 5.
- Medir la activación (habló por voz con su agente al menos 1 minuto en las primeras 24 h) en Reportes ›
  Plataforma.
