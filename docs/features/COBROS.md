# Registro y cobros

Registro autoservicio desde la landing y cobro de los planes: tarjeta con Mercado Pago (suscripción con débito
automático) o transferencia que aprueba el admin; vencimientos, gracia y caída al Free. Estado: en producción
desde el 10-oct-2026 (registro y transferencia) y el 11-oct-2026 (Mercado Pago, primera compra real). Plan: los
tiers públicos con `price_ars`.

No confundir con verificar los pagos que reciben los clientes (otra cuenta y otra app de MP, sin integración).

## Reglas de negocio

| Tema | Regla |
|---|---|
| Free | Los límites del tier en la base. El tier del registro es el primero público con precio 0 (por `sort`) |
| Precio | `tiers.price_ars` es el precio final (monotributo, factura C, sin IVA discriminado). Nulo = no se vende por el panel; 0 = gratis |
| Factura (ARCA) | Manual: la app guarda los datos fiscales y cada pago, con marca de facturado (vista Cobros) |
| Transferencia | Mensual, por adelantado. El comprobante llega por mail; el tier se activa cuando el admin registra el pago |
| Tarjeta en el registro | Con un plan pago y MP, el pago es el paso 2 del formulario de la landing, sin otras opciones. La cuenta se crea solo si MP aprueba la tarjeta |
| Vencido sin pagar | `BILLING_GRACE_DAYS` (7) de gracia con el tier pago y avisos; después, Free |
| Números que sobran | Suspendidos `BILLING_NUMBER_HOLD_DAYS` (30): asignados, sin atender; después vuelven al inventario |
| Cambio de plan (transferencia) | Con el próximo pago (`pending_tier_id`); el admin puede registrar una subida antes |
| Cambio de plan (tarjeta) | Subida inmediata; el monto nuevo rige desde el próximo débito, sin prorrateo. Bajada con el próximo débito |
| Entrantes a 0800 / 0810 | Descuentan ×2 / ×1,5 de los minutos entrantes (`quota.INBOUND_MINUTE_FACTORS`, por prefijo del número marcado; condiciones punto 7). Las salientes, normal |
| Minuto extra | No se vende: la cuota corta al tope. Más minutos para un mes = ajuste de límites del cliente |
| Red (a medida) | No es un tier: lo cotiza un asesor |

## Modelo de datos (migración 0012)

| Tabla | Columnas |
|---|---|
| `tiers` | `price_ars` (int nulo), `public` (bool), `sort` (int) |
| `clients` | `created_via` (`admin`/`signup`), `legal_name`, `tax_id` (CUIT, 11 dígitos), `tax_condition` (`ri`/`monotributo`/`exento`/`cf`) |
| `subscriptions` | `client_id`, `tier_id`, `method` (`transfer`/`mercadopago`), `status` (`pending`/`active`/`past_due`/`canceled`), `pending_tier_id`, `current_period_end`, `grace_until`, `cancel_at_period_end`, `canceled_at`, `reminded_for`, `mp_preapproval_id` (único), `payer_email` |
| `billing_payments` | `client_id`, `subscription_id`, `tier_id`, `method`, `status` (`approved`/`rejected`/`refunded`), `amount_ars`, `paid_on`, `period_end`, `mp_payment_id` (único), `recorded_by`, `note`, `raw`, `invoiced_at` |
| `phone_numbers` | `suspended_at` |

- "Una suscripción abierta por cliente" y "un solo Free" no son índices: los cuida el servicio (lock de la fila del
  cliente).
- La aceptación de las condiciones en el registro queda en `legal_acceptances` (ver [`LEGAL.md`](LEGAL.md)).

## API

| Ruta | Quién | Qué hace |
|---|---|---|
| `GET /api/v1/demo/plans` | público | precios de la base y `mp_public_key` para la landing |
| `POST /api/v1/demo/signup/check` | público | verifica el email antes del paso 2 (409 `email_taken`, 422 descartable; 30/h por IP) |
| `POST /api/v1/demo/signup` | público, Turnstile | crea cliente y usuario (y la suscripción si paga con tarjeta); 201 con `continue_url` |
| `POST /api/v1/auth/handoff` | link de un uso | abre la sesión desde `/welcome` |
| `POST /api/v1/auth/password-reset` | público | "Olvidé mi clave": 202 siempre |
| `GET /clients/{id}/billing` | cliente | plan, suscripción y pagos |
| `POST /clients/{id}/billing/subscribe` | cliente | `{tier_id, method: transfer|mercadopago, card_token_id?}`: pide plan, paga con tarjeta o cambia el plan del débito |
| `POST /clients/{id}/billing/cancel` | cliente | baja: la pendiente se cancela; la activa sigue hasta `current_period_end` |
| `PUT /clients/{id}/billing/fiscal` | cliente | datos para la factura |
| `POST /clients/{id}/billing/payments` | admin | registra un pago por transferencia |
| `POST /clients/{id}/billing/suspend` | admin | rechaza el pedido o pasa al Free ya |
| `GET /billing/subscriptions`, `GET /billing/payments`, `PATCH /billing/payments/{id}` | admin | vista Cobros; marcar facturado |
| `POST /mp/billing/webhook` | Mercado Pago | notificaciones firmadas (fuera de `/api/v1`) |

Un admin en "ver como cliente" no toca el plan ni los cobros: 403 `support_read_only`.

## Flujo

### Registro

1. Landing: "Empezar gratis" lleva a `/registro`; los planes pagos a `/registro?plan=<tier>`
   (`landing/src/pages/registro.astro`). Pide empresa, nombre, email, clave (dos veces, 10+ caracteres) y la casilla
   de condiciones.
2. Free, o plan pago sin MP configurado: un paso. `POST /demo/signup` crea el `Client` (tier Free, `created_via
   signup`) y el usuario; sin MP, `next` es `/plan?tier=<nombre>` para pagar por transferencia.
3. Plan pago con MP: "Continuar al pago" llama a `/demo/signup/check` y muestra el paso 2 con los campos seguros de MP
   (`landing/src/scripts/mercadopago.ts`). "Pagar y crear mi cuenta" manda todo con `card_token_id`: el backend crea
   cliente, usuario y suscripción en MP (`subscribe_card`) y recién ahí hace commit.
   - Tarjeta rechazada: 422 `card_rejected` en el paso 2, sin crear nada.
   - Si el commit falla después de crearla en MP, se cancela en MP.
4. 201 con `continue_url` = `APP_URL/welcome?token=…&next=…`: JWT de un solo uso y 10 min (con `sv`; al usarlo sube
   `session_version`). `/welcome` hace `POST /auth/handoff` y sigue a `next`. Mails: "Tu cuenta de Atentina está
   lista" y, si pagó, "Recibimos tu pago".
5. Aceptación: sin `accept_terms` → 422 `terms_required`; si `terms_version`/`privacy_version` no son las vigentes →
   409 `terms_outdated` (la página quedó abierta mientras se publicaba otra).
6. Defensa: 3 registros por hora y 10 por día por IP, dominios descartables, trampa para bots (`website`),
   `SIGNUP_ENABLED`; sin Turnstile o sin tier Free, 503 `signup_unavailable`. El loop borra los registros en los
   que nadie entró en `PASSWORD_SETUP_HOURS` (72) y sin conversaciones.
7. Olvidé mi clave: 5 por hora por IP y 3 por hora por email, sin Turnstile (no relaja la CSP del panel); solo manda
   mail a usuarios que existen y reusa el link de crear la clave.

### Pago por transferencia

1. En `/plan` el cliente completa los datos de factura si faltan y elige el plan
   (`subscribe {method: "transfer"}`): sin plan pago, `subscription` en `pending` (sigue en Free); con uno activo,
   `pending_tier_id`. Mail al cliente con `BANK_TRANSFER_INFO` y el monto; aviso al admin (`BILLING_NOTIFY_TO` o
   `SUPPORT_EMAIL`) con link a la ficha.
2. El admin, en la ficha del cliente (tarjeta "Plan pago"): **Registrar pago** (tier, monto, fecha, nota) → `active`,
   cambia `tier_id`, `current_period_end` un mes después del vencimiento vigente (o de hoy) y reactiva los números
   suspendidos que entran. **Rechazar pedido** o **Pasar al gratuito**: Free ya.
3. Renovación: `BILLING_REMINDER_DAYS` (5) antes del vencimiento sale un mail con los datos (uno por período).
4. Vista **Cobros** (`/admin/billing`): planes pagos, pedidos abiertos y pagos con los datos para facturar y "Marcar
   facturado".

### Pago con tarjeta (Mercado Pago)

Solo con `MP_BILLING_ACCESS_TOKEN` y `MP_BILLING_PUBLIC_KEY`; si faltan, Plan ofrece solo transferencia.

1. Con la cuenta creada: Plan → "Pagar con tarjeta" → `/plan/pagar?tier=<id>` (`CheckoutPage`); pide antes los
   datos de factura si faltan.
2. Campos seguros de MP (SDK `sdk.mercadopago.com/js/v2`, `web/src/features/billing/mercadopago.ts`; número,
   vencimiento y código en iframes de MP, **código de seguridad siempre obligatorio**) tokenizan la tarjeta →
   `subscribe {method: "mercadopago", card_token_id}` → `service.subscribe_card`:
   - `POST /preapproval` con `status: authorized`, `external_reference` = id de nuestra suscripción, `payer_email` y
     el monto del tier. MP cobra el primer mes en el momento; el cobro aparece un instante después (hasta 4
     reintentos de 1,5 s); con el pago aprobado, `active` hasta `next_payment_date`.
   - Un pedido por transferencia pendiente se reemplaza.
   - Si algo falla después de crearla en MP, la suscripción se guarda igual como pendiente: si se deshiciera, MP
     seguiría debitando una suscripción desconocida.
3. `service.sync` aplica lo que diga MP: registra cada cuota una vez (`mp_payment_id`), activa o renueva hasta
   `next_payment_date` y aplica una bajada pedida; `cancelled` en MP deja el plan hasta el fin del período. Lo
   llaman el webhook y la conciliación (`service.reconcile`, en el barrido, para las suscripciones con débito que
   esperan un pago).
4. Cambio de plan con débito activo: `PUT` del monto (`change_card_plan`). Baja: `PUT status: cancelled`; el tier
   dura hasta `current_period_end`.
5. Cobro rechazado: `tick` lo pasa a `past_due` con gracia (MP reintenta); al terminar la gracia, Free y
   cancelación en MP.

### Vencimiento y caída al Free

- `current_period_end` pasado sin pago: `past_due`, `grace_until = current_period_end + BILLING_GRACE_DAYS`, mail
  "No registramos el pago". Un pago durante la gracia vuelve a `active` y el período sigue desde el vencimiento.
- Al pasar `grace_until` (o el fin del período de una baja pedida, sin gracia):
  1. `canceled` y tier Free (sin Free cargado, queda inactivo y se loguea un error).
  2. Los números que no entran se marcan `suspended_at` (`billing.service.fit_numbers`); esta bajada no pasa por
     `check_tier_fits`.
  3. Mail "Tu cuenta pasó al plan Free", con los números suspendidos.
- Número suspendido: `calls.start_inbound` rechaza la entrante con `number_suspended`. Si el cliente paga antes de
  los 30 días, se reactivan los que entran en el plan.

### Webhook

`app/billing/webhook.py`: valida `x-signature` (HMAC-SHA256 de `id:<data.id>;request-id:<x-request-id>;ts:<ts>;`
con `MP_BILLING_WEBHOOK_SECRET`; sin secreto o firma mala, 401), responde 200 y procesa aparte. Vuelve a pedir el
recurso a MP (`subscription_preapproval`, `subscription_authorized_payment`, `payment` con `subscription_id`) con
reintentos a los 0, 5 y 30 s (`RETRY_DELAYS`). URL de producción y sandbox:
`https://app.atentina.com.ar/mp/billing/webhook` (sale por el túnel de `app.`, sin ruta nueva).

## Código

| Dónde | Qué |
|---|---|
| `app/billing/service.py` | Máquina de estados: pedido, pago, baja, caída al Free, `fit_numbers`, `subscribe_card`, `change_card_plan`, `sync`, `reconcile`, `tick` |
| `app/billing/mp.py` | Cliente de la API de MP (preapproval, cuotas, pagos), errores (`card_rejected`, `card_cvv_required`) y firma |
| `app/billing/webhook.py` | `POST /mp/billing/webhook` |
| `app/billing/loop.py` | En el lifespan, cada `BILLING_TICK_SECONDS` (900): conciliación, `tick` y borrar registros sin activar |
| `app/services/signup.py` | Registro con clave, aceptación de condiciones, `continue_url`, "olvidé mi clave" |
| `app/api/routers/billing.py`, `demo.py`, `auth.py` | Rutas de la tabla de API |
| `app/api/http.py` | CSP con el SDK y los iframes de MP solo en `MP_PAGES` (`/plan/pagar`) |
| `app/mail/messages.py` | Cómo pagar, aviso al admin, pago recibido, renovación, plan vencido, paso al Free |
| `web/src/features/billing/` | `/plan`, `/plan/pagar`, tarjeta "Plan pago" de la ficha, vista Cobros; `/welcome` y `/forgot-password` en `features/auth/` |
| `landing/src/pages/registro.astro`, `landing/src/scripts/mercadopago.ts` | Registro y paso 2 con tarjeta |

## Variables (`.env`, `app/config.py`)

| Variable | Default | Qué |
|---|---|---|
| `SIGNUP_ENABLED` | true | registro abierto |
| `SIGNUP_IP_PER_HOUR` / `SIGNUP_IP_PER_DAY` / `SIGNUP_CHECK_IP_PER_HOUR` | 3 / 10 / 30 | topes por IP |
| `PASSWORD_RESET_IP_PER_HOUR` / `PASSWORD_RESET_EMAIL_PER_HOUR` | 5 / 3 | topes de "olvidé mi clave" |
| `PASSWORD_SETUP_HOURS` | 72 | registros sin activar se borran después |
| `BANK_TRANSFER_INFO` | — | datos bancarios (una línea por dato, `Titular: ...\nCBU: ...`) |
| `BILLING_NOTIFY_TO` | `SUPPORT_EMAIL` | aviso de pedidos al admin |
| `BILLING_GRACE_DAYS` / `BILLING_NUMBER_HOLD_DAYS` / `BILLING_REMINDER_DAYS` | 7 / 30 / 5 | gracia, números suspendidos, recordatorio |
| `BILLING_TICK_SECONDS` | 900 | período del barrido |
| `BILLING_TIMEZONE` | America/Argentina/Buenos_Aires | días de facturación |
| `MP_BILLING_ACCESS_TOKEN`, `MP_BILLING_PUBLIC_KEY` | — | sin ellas no se ofrece tarjeta |
| `MP_BILLING_WEBHOOK_SECRET` | — | firma `x-signature`; vacío = el webhook rechaza todo |
| `MP_BILLING_TEST_PAYER_EMAIL` | — | solo en sandbox |

Al editar `.env`: diff enmascarado contra el backup antes de recrear `app`.

## Reglas y trampas de Mercado Pago

- **Código de seguridad:** MP lo marca opcional en Mastercard, Mastercard Prepaid (la de MP) y Naranja, pero
  `POST /preapproval` con un token sin código da 400 (`Card token was generated without cvv validation`). Por eso los
  campos seguros lo piden siempre; el error se traduce a `card_cvv_required`. El Card Payment Brick no lo pedía.
- **`cancelled` es final:** reactivar da 400 `Invalid transition from cancelled to authorized`. La grafía es con
  dos l.
- `GET /authorized_payments/search` con `limit=50` da 400 (`Invalid value for limit`): se pide sin `limit` (trae las
  12 últimas).
- El primer cobro aparece en la búsqueda un instante después del alta: reintentos cortos en `subscribe_card`.
- Las notificaciones pueden llegar antes de que el recurso exista en la API de MP (404) o antes de que se guarde la
  cuenta: reintentos del webhook a 0, 5 y 30 s.
- Tarjeta rechazada: falla al crear la suscripción (400 `CC_VAL_433`); MP deja una `pending` que cancela solo.
- `payer_email`: MP lo devuelve vacío después; se guarda el nuestro.
- `GET /preapproval/search?external_reference=…` no filtra: no sirve para buscar una suscripción.
- Débito y crédito andan igual; el saldo de la cuenta de MP no se ofrece en este flujo.
- Comisión: depende del plazo de acreditación elegido en la cuenta de MP (8 % en el momento medido en la primera
  compra; ~4,1 % a 18 días).
- Los precios de la landing (`landing/src/data/site.ts`) se mantienen a mano iguales a `price_ars`.

## Desplegar y probar

- Tests: `tests/test_billing.py` (registro, handoff, pedido, pago, vencimiento, gracia, Free, números, permisos),
  `tests/test_billing_mp.py` (MP con un cliente falso: alta, rechazo, cambio, baja, cuotas una vez, webhook firmado,
  conciliación), `tests/test_migration_0012.py`, `web/src/features/billing/PlanPage.test.tsx`.
- Credenciales, cuentas de prueba y webhook de MP: con el MCP de Mercado Pago
  (`claude mcp add --transport http mercadopago https://mcp.mercadopago.com/mcp`, autenticado con la cuenta de MP de
  Atentina): `create_application`, `create_test_user`, `get_credentials`, `save_webhook` (`callback` y
  `callback_sandbox`, tópicos `subscription_preapproval`, `subscription_authorized_payment` y `payment`),
  `notifications_history`. La clave secreta del webhook está en el panel de MP (Webhooks → Configurar
  notificaciones); "Restablecer" la cambia y hay que actualizar `.env`.
- Cambios en backend: `make calls-active && make up-agent`. Si el formulario de la landing cambia de contrato,
  desplegar primero `app` y después la landing.
