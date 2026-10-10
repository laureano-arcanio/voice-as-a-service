# Plan: registro autoservicio y cobro de planes

Diseño (9-oct-2026). Cubre cómo se registra un cliente desde la landing y cómo paga su plan: por
transferencia bancaria aprobada a mano o con Mercado Pago (suscripción con débito automático). No
confundir con [`MERCADOPAGO_PLAN.md`](MERCADOPAGO_PLAN.md), que trata de verificar los pagos que
reciben nuestros clientes: es otra cuenta y otra app de MP.

**Estado (9-oct-2026):**

| Fase | Estado |
|---|---|
| 1. Registro y "olvidé mi clave" | **Desplegado el 10-oct-2026** (migración 0012, `app` y `agent` recreados) |
| 2. Cobro por transferencia | **Desplegado el 10-oct-2026** |
| 0. Spike de MP en sandbox | Hecho el 10-oct-2026 (sección 6.2), salvo el `init_point` con otro email y las notificaciones |
| 3. Mercado Pago y registro con clave | **Desplegado el 10-oct-2026** con las credenciales de producción (sección 7); falta la primera compra real |
| 4. Puesta en marcha | Sin empezar (sección 5) |

## 0. Qué se reusa

| Pieza | Dónde | Para qué |
|---|---|---|
| Link de crear la clave (JWT de un uso, 72 h) | `services/security.py`, `/set-password` | Activar la cuenta (verifica el email) y recuperar la clave |
| Mail de alta | `mail/notify.py` (`invite`) | Mail de activación del registro |
| Turnstile y límite por IP | `services/demo.py` (`verify_turnstile`), `services/ratelimit.py` | Proteger el registro |
| Ruta pública del túnel | `api.atentina.com.ar` → `^/api/v1/demo/` | El registro va en `/api/v1/demo/signup`: sin ruta nueva ni cambio de CORS |
| Túnel del dashboard | `app.atentina.com.ar` → todo `app` | Webhook de MP y `back_url` (fase 3): sin ruta nueva |
| Webhook firmado | `whatsapp/webhook.py` | Mismo patrón para `/mp/billing/webhook` (fase 3) |
| Loop en el lifespan | `main.py` (como `sweep_loop`) | Vencimientos, gracia, recordatorios y registros sin activar |
| Límites efectivos | `services/limits.py` | El cobro solo cambia `client.tier_id`; los límites salen de ahí como siempre |

## 1. Decisiones

Confirmadas con el usuario el 9-oct-2026, salvo las marcadas como propuestas.

| Decisión | Elección |
|---|---|
| Free | **Los límites del tier en la base**, como dice la landing (20 min/mes, llamadas web, API). El tier del registro es el **público con precio 0** |
| Monto | `tiers.price_ars` es **el precio final**: Atentina es monotributista (factura C), no se discrimina IVA. La landing ya no dice "sin IVA" |
| Factura (ARCA) | **Manual**: la app guarda los datos fiscales del cliente y cada pago, con marca de facturado (vista Cobros) |
| Pago por transferencia | **Mensual, por adelantado.** El cliente pide el plan y ve los datos bancarios; **el comprobante lo manda por email**. El tier se activa cuando el admin registra el pago |
| Plan vencido sin pagar | **7 días de gracia** con el tier pago y avisos, después **Free**. Los números que sobran quedan **suspendidos 30 días** (asignados, sin atender) y después vuelven al inventario |
| Cambio de plan con uno activo | Propuesta: se aplica **con el próximo pago** (`pending_tier_id`), tanto subida como bajada. En transferencia, el admin puede registrar una subida antes |
| Flujo del registro (10-oct-2026) | **Registrarse → si el plan es pago, pagarlo en el momento.** La clave se elige en el formulario y la sesión se abre sin esperar un mail |
| Pago obligatorio en el registro (10-oct-2026) | Con un plan pago y MP, el pago es el **paso 2 del formulario de la landing**, con su diseño y sin otras opciones (ni transferencia ni seguir gratis). **La cuenta se crea solo si MP aprueba la tarjeta.** Después, al inicio del panel. Los datos de factura se piden después, en Plan |
| Checkout de MP (fase 3) | **Card Payment Brick** en `/plan/pagar` (tarjeta tokenizada por MP, `card_token_id`, suscripción `authorized`): no hace falta cuenta de MP y una tarjeta rechazada avisa en el acto. Antes se había elegido el `init_point`; se cambió después del spike. La CSP se relaja solo en esa ruta |
| Transferencia | Sigue como alternativa en Plan, aprobada a mano |
| Subida de plan en MP (fase 3) | **Cambio inmediato**; el monto nuevo rige desde el próximo débito (`PUT /preapproval`). Sin prorrateo. La bajada, con el próximo débito |
| Minuto extra | **No se vende** (10-oct-2026): la cuota corta al llegar al tope. Se sacó de la landing; más minutos para un mes se dan con un ajuste de límites del cliente |

## 2. Flujos

### 2.1 Registro

1. En la landing, "Empezar gratis" (nav, `/desarrolladores`, plan Free) lleva a `/registro`; los planes
   pagos, a `/registro?plan=<tier>`. "A medida" sigue yendo al contacto.
2. `/registro` pide empresa, nombre, email y **clave** (dos veces, 10 caracteres o más). Con `?plan=` de un
   plan pago, la página lee `GET /api/v1/demo/plans` (precios de la base y `mp_public_key`) y muestra a la
   izquierda lo que incluye ese plan.
   - **Free, o plan pago sin MP:** un paso. `POST /api/v1/demo/signup` (con Turnstile) crea el `Client`
     (tier Free) y el usuario; sin MP, `next` es `/plan?tier=<nombre>` para pagarlo por transferencia.
   - **Plan pago con MP:** "Continuar al pago" verifica el email (`POST /demo/signup/check`: 409
     `email_taken`, 422 descartable, 30 por hora por IP) y muestra el **paso 2**: plan, precio y el Card
     Payment Brick (`landing/src/scripts/mercadopago.ts`, con los tokens de color de la landing). "Pagar y
     crear mi cuenta" manda todo junto con `card_token_id`: el backend crea cliente y usuario, la suscripción
     en MP (`subscribe_card`) y recién ahí hace commit. Tarjeta rechazada: 422 `card_rejected` en el paso 2,
     sin crear nada (MP deja una suscripción `pending` que cancela sola a los segundos). Si el commit falla
     después de crearla en MP, se cancela en MP.
   - Responde 201 con `continue_url`: `APP_URL/welcome?token=…&next=…`, un link de **un solo uso, 10 min**
     (JWT con `sv`; al usarlo sube `session_version`). Le llega "Tu cuenta de Atentina está lista" (con el
     plan) y, si pagó, "Recibimos tu pago".
   - Un email que ya tiene cuenta da **409 `email_taken`** (con la clave en el formulario, quien se registra
     necesita saberlo).
3. La landing muestra la pantalla final en el mismo panel: check verde, "Pago aprobado" ("Tu plan X ya está
   activo…") o "Cuenta creada" (Free), el botón "Entrar al panel" y una cuenta regresiva de 5 s que redirige
   sola a `continue_url`. `/welcome` (`WelcomePage`) hace `POST /auth/handoff`, que abre la
   sesión, y sigue a `next` (el inicio, con el plan ya activo si pagó).
4. Defensa:
   - 3 registros por hora y 10 por día por IP (`SIGNUP_IP_PER_HOUR`, `SIGNUP_IP_PER_DAY`);
   - lista corta de dominios descartables y trampa para bots (`website`);
   - `SIGNUP_ENABLED`; sin Turnstile o sin tier Free, 503 `signup_unavailable`.
   - El loop borra los registros en los que nadie entró a las `PASSWORD_SETUP_HOURS` (72): ningún usuario
     con `last_login_at` (el handoff lo marca) y sin conversaciones.
5. **Olvidé mi clave** (`POST /auth/password-reset`, pantalla `/forgot-password`, link en el login):
   - responde 202 siempre; tope de 5 por hora por IP y 3 por hora por email;
   - sin Turnstile, para no relajar la CSP del dashboard: solo manda mails a usuarios que existen;
   - reusa el link de crear la clave.

### 2.2 Pago por transferencia (fase 2)

1. En `/plan` el cliente completa los datos para la factura (razón social, CUIT, condición frente al
   IVA) si faltan, y elige el plan. `POST /clients/{id}/billing/subscribe {tier_id, method: "transfer"}`:
   - sin plan pago: crea una `subscription` en `pending` (el cliente sigue en Free);
   - con uno activo: queda pedido en `pending_tier_id`;
   - al cliente le llega un mail con los datos (`BANK_TRANSFER_INFO`) y el monto; al admin
     (`BILLING_NOTIFY_TO`, o `SUPPORT_EMAIL`), el aviso con el link a la ficha.
2. El admin, en la ficha del cliente (tarjeta "Plan pago"):
   - **Registrar pago** (tier, monto, fecha, nota): pasa a `active`, cambia el `tier_id` y fija
     `current_period_end` un mes después del vencimiento vigente (o de hoy, si no tenía). Reactiva los
     números suspendidos que entran. Al cliente le llega un mail.
   - **Rechazar pedido** (pendiente) o **Pasar al gratuito** (activo): baja ya al Free (2.4).
3. Renovación: `BILLING_REMINDER_DAYS` (5) antes de `current_period_end` sale un mail con los datos y
   el monto (uno por período). El admin registra el pago del mes siguiente igual que el primero.
4. Baja pedida por el cliente: una pendiente se cancela; una activa sigue hasta `current_period_end` y
   después pasa al Free, sin gracia.
5. Vista **Cobros** (`/billing`, admin): planes pagos y pedidos abiertos, y pagos con los datos para
   facturar y "Marcar facturado".

### 2.3 Pago con tarjeta: Mercado Pago (fase 3)

Solo con `MP_BILLING_ACCESS_TOKEN` y `MP_BILLING_PUBLIC_KEY` (si faltan, Plan ofrece solo transferencia).

1. En el registro, es el paso 2 de la landing (2.1). Con la cuenta creada, desde Plan → "Elegir este
   plan" → "Pagar con tarjeta", el cliente llega a `/plan/pagar?tier=<id>` (`CheckoutPage`, en el panel). Si
   faltan los datos de factura, los pide primero.
2. El **Card Payment Brick** (SDK `sdk.mercadopago.com/js/v2`, `web/src/features/billing/mercadopago.ts`)
   tokeniza la tarjeta y la página hace `POST /clients/{id}/billing/subscribe {tier_id, method:
   "mercadopago", card_token_id}` → `service.subscribe_card`:
   - `POST /preapproval` con `status: authorized`, `external_reference` = id de nuestra suscripción,
     `payer_email` (en sandbox, `MP_BILLING_TEST_PAYER_EMAIL`) y el monto del tier;
   - MP cobra el primer mes en el momento. El cobro aparece un instante después: hasta 4 reintentos de
     1,5 s; con el pago aprobado, `active` hasta `next_payment_date`;
   - tarjeta rechazada: 422 `card_rejected`, no queda nada; un pedido por transferencia pendiente se reemplaza;
   - si algo falla **después** de crearla en MP, la suscripción se guarda igual como pendiente: si se
     deshiciera, MP seguiría debitando una suscripción que no conocemos (pasó en la prueba, sección 6.2).
3. `service.sync` aplica lo que diga MP: registra cada cuota una vez (`mp_payment_id`); con un pago aprobado
   activa o renueva hasta `next_payment_date` y aplica una bajada pedida; `cancelled` en MP deja el plan
   hasta el fin del período. Lo llaman:
   - el **webhook** `POST /mp/billing/webhook` (`app/billing/webhook.py`): valida `x-signature` (HMAC-SHA256
     de `id:<data.id>;request-id:<x-request-id>;ts:<ts>;` con `MP_BILLING_WEBHOOK_SECRET`; si no, 401),
     responde 200 y procesa aparte; vuelve a pedir el recurso a MP (`subscription_preapproval`,
     `subscription_authorized_payment`, `payment` con `subscription_id`);
   - la **conciliación** en el barrido (`service.reconcile`, antes de `tick`): las suscripciones con débito
     que esperan un pago (pendientes, vencidas o que vencen hoy o antes).
4. **Cambio de plan** (con débito activo, sin tarjeta): `PUT` del monto; subida ya, bajada con el próximo
   débito. **Baja:** `PUT status: cancelled`; el tier dura hasta `current_period_end`.
5. Cobro rechazado: `tick` lo pasa a `past_due` con gracia (MP reintenta); al terminar la gracia, Free y
   cancelación en MP.

### 2.4 Vencimiento y caída a Free

- `current_period_end` pasado sin pago: `past_due`, con `grace_until = current_period_end +
  BILLING_GRACE_DAYS` (7). Sale el mail "No registramos el pago".
- Si llega un pago durante la gracia, vuelve a `active` y el período sigue desde el vencimiento.
- Al pasar `grace_until` (o el fin del período de una baja pedida por el cliente):
  1. `canceled`, y el cliente pasa al tier Free (sin Free cargado, queda inactivo y se loguea un error).
  2. Los números que no entran en el Free se marcan `suspended_at` (`billing.service.fit_numbers`); esta
     bajada no pasa por `check_tier_fits`.
  3. Al cliente le llega "Tu cuenta pasó al plan Free", con los números suspendidos.
- Número suspendido: `calls.start_inbound` rechaza la entrante con `number_suspended` (queda como
  rechazada). A los `BILLING_NUMBER_HOLD_DAYS` (30) vuelve al inventario. Si el cliente paga antes, se
  reactivan los que entran en el plan.

## 3. Modelo de datos (migración `0012`)

| Tabla | Cambios |
|---|---|
| `tiers` | `price_ars` int nulo (nulo = no se vende por el dashboard; 0 = gratis), `public` bool, `sort` int |
| `clients` | `created_via` (`admin`/`signup`), `legal_name`, `tax_id` (CUIT, 11 dígitos), `tax_condition` (`ri`/`monotributo`/`exento`/`cf`) |
| `subscriptions` (nueva) | `client_id`, `tier_id`, `method` (`transfer`/`mercadopago`), `status` (`pending`/`active`/`past_due`/`canceled`), `pending_tier_id`, `current_period_end`, `grace_until`, `cancel_at_period_end`, `canceled_at`, `reminded_for`, `mp_preapproval_id` único, `payer_email` |
| `billing_payments` (nueva) | `client_id`, `subscription_id`, `tier_id`, `method`, `status` (`approved`/`rejected`/`refunded`), `amount_ars`, `paid_on`, `period_end`, `mp_payment_id` único, `recorded_by`, `note`, `raw`, `invoiced_at` |
| `phone_numbers` | `suspended_at` |

- "Una suscripción abierta por cliente" y "un solo Free" no son índices: los cuida el servicio (lock
  de la fila del cliente; el Free es el primero por `sort`).
- Test de migración: `tests/test_migration_0012.py`.

## 4. Código

| Dónde | Qué |
|---|---|
| `app/billing/service.py` | Máquina de estados: pedido, pago, baja, caída al Free, números (`fit_numbers`), Mercado Pago (`subscribe_card`, `change_card_plan`, `sync`, `reconcile`) y el barrido (`tick`) |
| `app/billing/mp.py` | Cliente de la API de MP (preapproval, cuotas, pagos) y la firma del webhook |
| `app/billing/webhook.py` | `POST /mp/billing/webhook`, fuera de `/api/v1` |
| `app/billing/loop.py` | En el lifespan, cada `BILLING_TICK_SECONDS` (900): conciliación con MP, `tick` y borrar registros sin activar |
| `app/services/signup.py` | Registro con clave, `continue_url` y "olvidé mi clave" |
| `app/api/http.py` | CSP con el SDK y los iframes de MP solo en `MP_PAGES` (`/plan/pagar`) |
| `app/api/routers/billing.py` | `GET /clients/{id}/billing`, `POST .../billing/subscribe`, `.../cancel`, `PUT .../fiscal`. Admin: `POST .../billing/payments`, `.../suspend`, `GET /billing/subscriptions`, `GET /billing/payments`, `PATCH /billing/payments/{id}` |
| `app/api/routers/demo.py`, `auth.py` | `POST /demo/signup`, `POST /auth/handoff`, `POST /auth/password-reset` |
| `app/mail/messages.py` | Clave nueva, cómo pagar, aviso al admin, pago recibido, renovación, plan vencido, paso al Free |
| `app/services/calls.py` | Rechazo de entrantes a números suspendidos |
| `web/src/features/billing/` | `/plan` y `/plan/pagar` (cliente), tarjeta "Plan pago" de la ficha y vista Cobros (admin). Precio, público y orden en el formulario de tiers; `/forgot-password` y `/welcome` en `features/auth/` |
| `landing/src/pages/registro.astro` | Registro; botones de `Pricing`, `Nav` y `/desarrolladores` hacia `/registro`. Los precios de `site.ts` se mantienen a mano iguales a `price_ars` |
| `tests/test_billing.py`, `tests/test_billing_mp.py`, `web/src/features/billing/PlanPage.test.tsx` | Registro, handoff, pedido, pago, vencimiento, gracia, Free, números, permisos; MP con un cliente falso (alta, rechazo, cambio, baja, cuotas una vez, webhook firmado, conciliación) |

Variables nuevas (`app/config.py`, `.env.example`): `SIGNUP_ENABLED`, `SIGNUP_IP_PER_HOUR`,
`SIGNUP_IP_PER_DAY`, `PASSWORD_RESET_IP_PER_HOUR`, `PASSWORD_RESET_EMAIL_PER_HOUR`,
`BANK_TRANSFER_INFO`, `BILLING_NOTIFY_TO`, `BILLING_GRACE_DAYS`, `BILLING_NUMBER_HOLD_DAYS`,
`BILLING_REMINDER_DAYS`, `BILLING_TICK_SECONDS`. Fase 3: `MP_BILLING_ACCESS_TOKEN`,
`MP_BILLING_PUBLIC_KEY`, `MP_BILLING_WEBHOOK_SECRET` y, solo en sandbox, `MP_BILLING_TEST_PAYER_EMAIL` (el
prefijo no choca con las de `MERCADOPAGO_PLAN.md`).

## 5. Puesta en marcha de las fases 1 y 2

Hecha el 10-oct-2026:
- Tiers públicos: **Free** ($ 0, 20 min entrantes, 1 llamada, 0 números, API con 10 pedidos/min),
  **Mostrador** ($ 29.000) y **Sucursal** ($ 99.000, 3 llamadas a la vez), con los límites de API del
  Free. Central e Interno siguen sin precio (no se venden por el dashboard).
- Mindosoftware (en Free, con 1 número) tiene un ajuste permanente de +1 número para no perderlo.
- `BANK_TRANSFER_INFO` con la cuenta de Mercado Pago (CVU y alias); backup del `.env` en
  `~/atentina-backups/env/`.

Pasos, para repetirlos en otro server:

1. Cargar en Tiers el **Free** (público, precio 0, 20 min, 0 números) y los pagos (**Mostrador**
   $ 29.000, **Sucursal** $ 99.000, públicos), con los límites de la landing.
2. `.env`: `BANK_TRANSFER_INFO` (una línea por dato, `Titular: ...\nCBU: ...`) y, si hace falta,
   `BILLING_NOTIFY_TO`. Diff enmascarado contra el backup antes de reiniciar.
3. Rebuild y recrear `app` (corre la migración 0012). Confirmar antes: el stack está en vivo.
4. Desplegar la landing (Render, con el push a `landing/`).
5. Probar de punta a punta: registro con un email propio, activación, pedido de plan, pago registrado
   y mail de renovación.

## 6. Configurar Mercado Pago (lo hace el usuario)

Pasos en el panel de MP Developers (<https://www.mercadopago.com.ar/developers/panel/app>), con la
cuenta de MP de Atentina (la que recibe la plata). Revisados contra la documentación de MP el
10-oct-2026; lo marcado *(sin confirmar)* puede verse distinto en el panel.

### 6.1 Sandbox (para la fase 0)

**Atajo: MCP de Mercado Pago** ([docs](https://www.mercadopago.com.ar/developers/es/docs/mcp-server/overview.md)).
Con el MCP conectado a la cuenta de Atentina, el agente hace los pasos 1 a 4 de abajo con sus
herramientas: `create_application` (producto `subscription`), `create_test_user` (`site_id: MLA`,
`seller`/`buyer`) y `add_money_test_user`, `get_credentials`, y `save_webhook` (`callback_sandbox`,
`topics`). `notifications_history_diagnostics` muestra si llegan las notificaciones. Conectarlo lo
hace el usuario:

```
claude mcp add --transport http mercadopago https://mcp.mercadopago.com/mcp
```

Después, en Claude Code, `/mcp` → `mercadopago` → autenticar (elegir Argentina y aprobar los permisos
con la cuenta de MP de Atentina). Crear la app y leer credenciales solo anda con esa autenticación
(OAuth). Las credenciales que devuelve van a `scratch/mp-sandbox.env`, no al chat.

A mano, desde el panel:

1. **Crear la aplicación.** En **Tus integraciones → Crear aplicación**:
   - Nombre: "Atentina Suscripciones" (es otra app que la de `MERCADOPAGO_PLAN.md`).
   - Solución: **Pagos online**, producto **Suscripciones**; sin plataforma de e-commerce.
2. **Cuentas de prueba.** Dentro de la app, **Cuentas de prueba → + Crear cuenta de prueba**, país
   **Argentina** (no se cambia después), aceptar los términos. Crear:
   - un **Vendedor** ("Vendedor - Atentina");
   - dos **Compradores** ("Comprador 1", "Comprador 2"), con algo de dinero ficticio.

   La tabla muestra usuario, contraseña y **código de verificación** de cada una: si MP pide un
   código por mail al entrar con una cuenta de prueba, es ese. No se pueden borrar (máximo 15).
3. **Credenciales de prueba.** En la app, **Pruebas → Credenciales de prueba**, copiar el
   **Access Token**:
   - Si empieza con `APP_USR-`, ya es el del vendedor de prueba: usar ese.
   - Si empieza con `TEST-`: abrir una ventana de incógnito, entrar a MP con el **vendedor de
     prueba**, crear ahí una aplicación igual y copiar su Access Token de **producción**
     (`APP_USR-…`); al ser de una cuenta de prueba, cobra en sandbox. *(sin confirmar cuál de los
     dos casos aparece hoy para Suscripciones)*
4. **Webhook.** En la app, **Webhooks → Configurar notificaciones**:
   - **URL modo pruebas:** `https://app.atentina.com.ar/mp/billing/webhook`.
   - Eventos: **Planes y suscripciones** (vinculación de una suscripción, pago recurrente) y **Pagos**.
   - **Guardar**, y en la misma pantalla revelar la **clave secreta**.
   - El endpoint todavía no existe en `app`: MP va a recibir 404 hasta la fase 3. La fase 0 consulta
     la API en vez de esperar notificaciones. La documentación de MP no deja claro si este panel aplica
     a Suscripciones: es una de las cosas que confirma el spike.
5. **Pasar los datos** sin pegarlos en el chat: en `scratch/mp-sandbox.env` (no se versiona):
   ```
   MP_BILLING_ACCESS_TOKEN=APP_USR-...
   MP_BILLING_WEBHOOK_SECRET=...
   MP_TEST_SELLER=usuario / contraseña
   MP_TEST_BUYER1=usuario / contraseña / código
   MP_TEST_BUYER2=usuario / contraseña / código
   ```

**Tarjetas de prueba** (vencimiento 11/30, CVV 123, DNI 12345678): Mastercard 5031 7557 3453 0604,
Visa 4509 9535 6623 3704, Visa débito 4002 7686 9439 5619. El nombre del titular fija el
resultado: `APRO` aprobado, `OTHE` rechazado, `FUND` sin fondos, `CONT` pendiente.

**Hecho el 10-oct-2026 con el MCP** (datos en `scratch/mp-sandbox.env`):
- App "atentina suscripciones" (`2008768571289284`), creada en el panel. Las credenciales de prueba
  (`APP_USR-…`) son de un **vendedor de prueba automático** (`3754973510`): no hace falta crear uno
  ni entrar con él.
- MP crea también un **comprador de prueba automático** (`3754973512`, con $ 50.000 cargados);
  `create_test_user` devuelve ese mismo, así que el segundo comprador se crea a mano en el panel.
- Webhook de pruebas guardado por API con `subscription_preapproval`, `subscription_authorized_payment`
  y `payment`: **la configuración de Suscripciones por la app sí se acepta**. La clave secreta está en el
  panel: Webhooks → **Configurar notificaciones** → abajo de los eventos, "Clave secreta" (el ojo la
  muestra; el botón de al lado la **restablece**, no tocarlo).
- Prueba de humo: `POST /preapproval` con `status: pending` y `payer_email` del comprador de prueba
  (`test_user_<nickname sin TESTUSER>@testuser.com`) devuelve `init_point` y resuelve `payer_id`.

### 6.2 Spike (fase 0): resultados del 10-oct-2026

Script `scratch/mp_spike/spike.py` (respuestas crudas en esa carpeta), contra el sandbox, con las
credenciales de 6.1. Sin entrar a MP como comprador: tarjeta tokenizada por API (`/v1/card_tokens` con
la public key de prueba) y `POST /preapproval` con `card_token_id` y `status: authorized`.

| Qué | Resultado |
|---|---|
| Suscripción autorizada con tarjeta (`APRO`) | `authorized` al instante; **cobra el primer mes en el momento** (pago `approved`, `accredited`) y fija `next_payment_date` un mes después. Es lo que ve el usuario como "pago hasta" |
| Tarjeta de débito (Visa débito de prueba, 10-oct-2026) | Igual que la de crédito: `authorized`, cobro aprobado, pago `debit_card` / `debvisa`. El Brick acepta crédito y débito (solo se limitaron las cuotas a 1); el saldo de la cuenta de MP no se ofrece en este flujo |
| Tarjeta rechazada (`OTHE`) | **Falla al crear la suscripción**: 400 `CC_VAL_433 Credit card validation has failed`. No queda una suscripción a medias |
| Pagos de la suscripción | `GET /authorized_payments/search?preapproval_id=…`: `status: processed`, `payment.status: approved`, `retry_attempt`, `debit_date` |
| Atar el pago a la suscripción | El pago (`/v1/payments/{id}`) trae `external_reference` (el de la suscripción) y `point_of_interaction.transaction_data.subscription_id` con `subscription_sequence.number` |
| Comisión y acreditación (cuenta por defecto) | $ 1.189 sobre $ 29.000 (4,10 % = 3,39 % + IVA) y `money_release_date` a 18 días |
| Cambio de monto (`PUT auto_recurring.transaction_amount`) | 200, sin cobro en el momento; `next_payment_date` igual: rige desde el próximo débito, como se esperaba |
| Pausa y reactivación | `paused` ↔ `authorized` funciona; mantiene `next_payment_date` |
| Cancelación | La grafía es **`cancelled`**. Es final: reactivarla da 400 `Invalid transition from cancelled to authorized` |
| `payer_email` | MP resuelve `payer_id` del email del comprador de prueba (`test_user_<n>@testuser.com`), pero después lo devuelve vacío: guardar el nuestro |
| Notificaciones | No llegó ninguna. Con credenciales de prueba, MP las manda según el webhook **de la cuenta del vendedor de prueba**: hay que entrar a Developers con ese usuario y configurarlo en modo productivo ahí (lo hace el usuario: pide su contraseña). La firma `x-signature` queda sin verificar hasta la fase 3, con el endpoint desplegado |

Pendiente (lo hace el usuario, porque pide entrar a MP como comprador): pagar por el `init_point` de
una suscripción `pending` con un comprador cuyo email no es el `payer_email`, para saber si la
redirección sirve sola.

**Prueba de punta a punta (10-oct-2026, backend de desarrollo + build de la UI + sandbox):** registro con
plan → `/welcome` → `/plan/pagar` → datos de factura → Brick con la Mastercard de prueba (`APRO`) → "Pago
aprobado", plan activo y próximo débito a un mes. También subida de plan (monto nuevo en MP) y baja
(`cancelled` en MP). Sin errores de CSP con los dominios de `MP_HOSTS`. Dos hallazgos, corregidos:
- `GET /authorized_payments/search` con `limit=50` da 400 (`Invalid value for limit`): sin `limit`.
- El primer cobro aparece en la búsqueda un instante después del alta: reintentos cortos en `subscribe_card`.

**Pago en el registro desde la landing (10-oct-2026, landing local + backend de desarrollo + sandbox):**
`/registro?plan=Mostrador` → datos → paso 2 → Mastercard `APRO` → inicio del panel con Mostrador activo y el
pago registrado. Con `OTHE` en Sucursal: "La tarjeta fue rechazada" en el paso 2 y ni cliente ni usuario.
`GET /preapproval/search?external_reference=…` no filtra (devuelve todas): no sirve para buscar una.

**Consecuencia para la fase 3:** el flujo con tarjeta tokenizada (`authorized`) anduvo completo sin
pasar por la cuenta de MP del comprador, y una tarjeta mala falla en el acto. Si el `init_point` falla con
emails distintos, el camino es el **Card Payment Brick** en una página propia (relajar la CSP solo ahí).

## 7. Puesta en marcha de la fase 3

Hecha el 10-oct-2026: credenciales de producción y webhook (`callback` y `callback_sandbox` a
`/mp/billing/webhook`) con el MCP; la clave secreta del webhook es la misma de la app. `app` y `agent`
recreados y landing publicada (commit `f6924d8`). Pendiente: la primera compra real y ver llegar el webhook.


1. **El usuario** activa las credenciales de producción de la app "atentina suscripciones" (6.3, paso 1)
   y elige el plazo de acreditación (6.3, paso 3).
2. Con el MCP: `get_credentials` de producción y `save_webhook` con `callback` (URL de producción) y los
   tópicos de suscripciones y pagos; la clave secreta, del panel.
3. `.env`: `MP_BILLING_ACCESS_TOKEN`, `MP_BILLING_PUBLIC_KEY`, `MP_BILLING_WEBHOOK_SECRET` de producción
   (sin `MP_BILLING_TEST_PAYER_EMAIL`). Diff enmascarado contra el backup.
4. Build, recrear `app` (y `agent`, mismo código), **después** push de la landing: el formulario nuevo manda
   la clave, usa `/demo/plans` y `/demo/signup/check`, y espera `continue_url`; el backend viejo no los tiene.
5. Prueba real: registro con plan Mostrador y una tarjeta propia; baja desde Plan.

Sin las credenciales de MP se puede desplegar igual (registro con clave y transferencia): la tarjeta no se
ofrece hasta cargarlas.

### 6.3 Producción (después de la fase 3)

1. **Activar las credenciales de producción.** En la app, **Producción → Credenciales de
   producción**: industria (software / servicios), sitio web `https://atentina.com.ar`, aceptar los
   términos y **Activar credenciales de producción**. Copiar el Access Token (`APP_USR-…`).
2. **Webhook de producción.** **Webhooks → Configurar notificaciones**, **URL modo producción**
   `https://app.atentina.com.ar/mp/billing/webhook`, mismos eventos. Copiar la clave secreta (se puede
   renovar con **Restablecer**; si se renueva, actualizar `.env`).
3. **Plazo de acreditación.** En la cuenta de MP (costos del negocio), elegir cuándo se libera la plata
   de los cobros: define la comisión (suscripciones, sin IVA: 6,99 % en el momento, 4,49 % a 10 días,
   3,39 % a 18 días, 1,49 % a 35 días; más retenciones de IIBB). *(menú sin confirmar)*
4. **`.env` del server:** `MP_BILLING_ACCESS_TOKEN` y `MP_BILLING_WEBHOOK_SECRET` de producción. Diff
   enmascarado contra el backup antes de recrear `app`.
5. **Prueba real:** un plan con un monto bajo, pagado con una tarjeta propia; cancelarlo después
   desde `/plan`.

No hace falta tocar el túnel ni el router: `app.atentina.com.ar` ya llega a `app` entero.
