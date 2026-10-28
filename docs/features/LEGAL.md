# Condiciones, privacidad y pedidos de baja

Condiciones y política de privacidad con versión, aceptación expresa registrada de cada usuario, y botones de
arrepentimiento y de baja. Estado: en producción desde el 26-oct-2026; versión vigente `2026-10-28` publicada el
27-oct-2026. Plan: todos.

## Marco legal (resumen)

Lo que se exige es poder **probar** la aceptación (un clic es firma electrónica: Ley 25.506). El registro está
abierto a cualquiera y un comercio chico suele tratarse como consumidor: se cumple como si lo fueran.

| Norma | Cómo se cumple |
|---|---|
| CCyC 985, Res. SCI 270/2020 | Casilla desmarcada con link a la versión exacta; resumen de lo importante arriba del texto; versión inmutable por URL |
| CCyC 1106-1108 | Mail de confirmación con documento, versión, fecha, huella (SHA-256) y link permanente |
| CCyC 1110-1111, Ley 24.240 art. 34 | Arrepentimiento en 10 días corridos: cláusula, botón y formulario |
| Disp. 954/2025 (y DNDC 3/2026) | `/arrepentimiento` y `/baja` a la vista y sin cuenta; código de trámite al instante; atención 8 h en días hábiles (lunes a viernes, 9 a 13 y 14 a 18) |
| Ley 24.240 art. 37, Res. 53/2003 | Cambios con 30 días de aviso y baja sin costo; topes de responsabilidad "en la medida que la ley lo permita" |
| Ley 25.326 arts. 5, 6 y 25 | Aceptación de la política; Atentina como encargada del tratamiento de las conversaciones |
| CCyC 2560 | Aceptaciones y pedidos se conservan al menos 5 años después del fin de la relación |

No es asesoramiento legal: los textos los revisa un abogado (la versión `2026-10-28`, revisada el 28-oct-2026, con el aviso a los clientes hecho).

## Textos y versiones

- `app/legal/texts/<doc>/<AAAA-MM-DD>.md` (`terminos`, `privacidad`); la versión es la fecha de publicación.
  `app/legal` calcula el SHA-256 y sabe cuál es la vigente.
- Hoy: `terminos` 2026-10-01, 2026-10-25 y 2026-10-28; `privacidad` 2026-10-25 y 2026-10-28.
- **Una versión publicada no se edita:** un cambio es un archivo nuevo. `tests/test_legal.py::PUBLISHED` tiene el hash
  de cada una y falla si cambia o si aparece una sin hash.
- `make legal-sync` (`app/legal/sync.py`) copia los textos a `landing/src/data/legal/` (con `index.json`: versiones y
  hashes), porque Render solo ve `landing/`. Un test falla si la copia quedó vieja.
- Landing: `/terminos` y `/privacidad` muestran la vigente; `/terminos/<versión>` y `/privacidad/<versión>`, cada
  una (`LegalDoc.astro`), con `noindex`, fuera del sitemap y sin lista en la página: se llega por el link permanente
  de los mails de aceptación (CCyC 1106-1108), que no se puede romper. Mostrar el historial no es obligatorio.
- Panel del admin: **Legales** (`/admin/legal`, `web/src/features/legal/`) lista cada versión con su huella y sus
  aceptaciones, y abre el texto exacto.

## Modelo de datos (migración 0031)

| Tabla | Columnas clave |
|---|---|
| `legal_acceptances` | solo de alta: `user_id`, `client_id`, `email` y `client_name` del momento, `document`, `version`, `sha256`, `statement` (texto de la casilla), `channel` (`signup`, `panel`), `ip` real, `user_agent`, `created_at` |
| `consumer_requests` | `kind` (`revocation`, `cancellation`), `code` (`ARR-…`/`BAJ-…`, único), `name`, `email`, `company`, `message`, `ip`, `client_id`, `status` (`open`, `done`, `rejected`), `resolution`, `resolved_at`, `email_status` |

- **Sin claves foráneas:** la prueba sobrevive a que se borre el usuario o el cliente. Ni la purga de registros sin
  activar ni la baja del cliente las borran; van en el backup diario de la base.

## API

| Ruta | Quién | Qué hace |
|---|---|---|
| `GET /api/v1/demo/legal` | público | versiones vigentes (las usa el formulario de registro) |
| `POST /api/v1/demo/signup` | público | `accept_terms`, `terms_version`, `privacy_version`: sin casilla 422 `terms_required`; versiones viejas 409 `terms_outdated` |
| `GET /api/v1/auth/me` | usuario | `legal_pending`: documentos vigentes que no aceptó |
| `POST /api/v1/auth/me/legal` | usuario | acepta los pendientes (409 `terms_outdated` si salió otra versión) |
| `POST /api/v1/demo/consumer-requests` | público, Turnstile | crea el pedido de arrepentimiento o baja |
| `GET /api/v1/consumer-requests`, `PATCH /api/v1/consumer-requests/{id}` | admin | lista y resuelve (`status`, `resolution`) |
| `GET /api/v1/legal/versions` | admin | cada versión publicada, la más nueva primero: huella, link, `current` y `acceptances` |
| `GET /api/v1/legal/versions/{document}/{version}` | admin | la versión con su `text` exacto (404 `legal_version_not_found`) |

## Flujo

- **Registro:** la casilla manda las versiones que mostró; la aceptación se guarda en la misma transacción que la
  cuenta (`signup.create_account` → `services/legal.py`): sin aceptación no hay cuenta. El mail de bienvenida es la
  confirmación. Ver [`COBROS.md`](COBROS.md).
- **Panel:** `web/src/features/auth/LegalModal.tsx`, un modal que no se cierra mientras haya `legal_pending`. Cubre a
  invitados por un admin, a clientes anteriores y a cada versión nueva. Guarda su propio texto más las versiones
  (`legal.panel_text`) y valida solo los documentos pendientes. Al aceptar sale un mail con documento, versión,
  fecha, huella y link. Solo usuarios de cliente; las API keys no se frenan (el aviso de cambios va por mail).
  Links legales al pie del menú (`AppLayout.tsx`).
- **Botones:** `/arrepentimiento` y `/baja` en el pie de la landing (`ConsumerRequest.astro`): formulario sin cuenta.
  Guarda el pedido, manda el código al email del que pide y avisa a `CONTACT_TO`. El admin lo resuelve (baja en la
  ficha del cliente, devolución si es arrepentimiento) y lo marca por la API. Con cuenta, la baja también es
  inmediata en Plan.

### Corte por aceptación (`app/services/legal_gate.py`)

- Sin `MIN_DIRECT_CALLS_VERSION` (`2026-10-28`) o una posterior aceptada, de cada documento, por **algún usuario del
  cliente** (`legal_acceptances.client_id`): `POST /direct-calls`, `POST /direct-calls/{id}/answer` y poner un número
  en `answer_mode=team` dan 403 `terms_pending`, y las entrantes de un número del equipo van al agente.
- Alcanza con un usuario porque la aceptación es en nombre de la empresa, la entrante no tiene usuario y las API keys
  no ven el modal. El modal igual se la pide a cada usuario.
- Una versión nueva no corta el teléfono del equipo (si exigiera la vigente, cada cambio lo apagaría hasta que alguien
  entre al panel). Si una versión nueva cambia algo de las llamadas directas, subir `MIN_DIRECT_CALLS_VERSION`.

## Publicar una versión nueva

1. Archivo nuevo `app/legal/texts/<doc>/<AAAA-MM-DD>.md` (sin tocar los anteriores) y su hash en
   `tests/test_legal.py::PUBLISHED`.
2. `make legal-sync`.
3. Si es un cambio importante: aviso por mail a los clientes con 30 días (punto 17 de las condiciones); la versión
   rige ese día.
4. El día que rige: **primero la landing** (push a `main`, Render) y después `app` (`make calls-active &&
   make up-agent`). Al revés, el formulario de la landing manda versiones viejas y el registro da 409.
5. Los usuarios aceptan al entrar al panel (modal).

## Desplegar y probar

- Tests: `tests/test_legal.py` (hashes, sincronía con la landing, registro, modal, pedidos),
  `tests/test_migration_0031.py`, `web/src/features/auth/LegalModal.test.tsx`, y en `tests/test_direct_calls.py` los
  del corte por aceptación.
- Prueba manual: un registro de punta a punta (filas en `legal_acceptances`, mail con versiones y huellas), un pedido
  en `/baja` (código en pantalla y por mail, aviso a `CONTACT_TO`) y entrar al panel con un cliente existente (modal).

## Pendientes

- Prueba de punta a punta del registro, `/baja` y el modal en producción.
