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
| 3. Mercado Pago | Sin empezar |
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
| Checkout de MP (fase 3) | **Redirección al `init_point`**: preapproval sin plan, `status: pending`. La CSP del dashboard no cambia |
| Subida de plan en MP (fase 3) | **Cambio inmediato**; el monto nuevo rige desde el próximo débito (`PUT /preapproval`). Sin prorrateo |
| Minuto extra | **No se vende** (10-oct-2026): la cuota corta al llegar al tope. Se sacó de la landing; más minutos para un mes se dan con un ajuste de límites del cliente |

## 2. Flujos

### 2.1 Registro (Free)

1. En la landing, "Empezar gratis" (nav, `/desarrolladores`, plan Free) lleva a `/registro`; los planes
   pagos, a `/registro?plan=<tier>`. "A medida" sigue yendo al contacto.
2. `/registro` pide empresa, nombre y email, con Turnstile, y hace `POST /api/v1/demo/signup`
   (`app/services/signup.py`). **Responde 202 siempre**, para no revelar qué emails existen:
   - Email nuevo: crea el `Client` (tier Free, `created_via='signup'`) y el usuario `client` sin clave,
     y manda el mail de alta. Con `plan`, el link termina en `&next=/plan?tier=<plan>`.
   - Email existente: le manda "Ya tenés una cuenta" con un link para crear una clave nueva.
3. El usuario crea la clave en `/set-password` y entra (a `next` si vino con plan).
4. Defensa:
   - 3 registros por hora y 10 por día por IP (`SIGNUP_IP_PER_HOUR`, `SIGNUP_IP_PER_DAY`);
   - lista corta de dominios descartables y trampa para bots (`website`);
   - `SIGNUP_ENABLED`; sin Turnstile o sin tier Free, 503 `signup_unavailable`.
   - El loop borra los registros sin activar a las `PASSWORD_SETUP_HOURS` (72): ningún usuario con
     `last_login_at` (crear la clave lo marca) y sin conversaciones.
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

### 2.3 Pago con Mercado Pago (fase 3, sin código)

1. En `/plan` el cliente elige el plan y "Mercado Pago".
2. `POST /clients/{id}/billing/subscribe {tier_id, method: "mercadopago"}` crea la `subscription`
   pendiente y un preapproval con:
   - `external_reference = subscription.id`, `payer_email` = el email del usuario;
   - `auto_recurring` mensual en ARS por `price_ars`;
   - `back_url = APP_URL/plan`.

   Responde el `init_point` y el front redirige.
3. El webhook `POST /mp/billing/webhook` valida `x-signature`: HMAC-SHA256 de
   `id:<data.id>;request-id:<x-request-id>;ts:<ts>;` con `MP_BILLING_WEBHOOK_SECRET`.
   - Responde 200 enseguida y procesa después; nunca usa el cuerpo: vuelve a pedir el recurso a MP.
   - `subscription_preapproval`: `authorized` → `active` y cambia el `tier_id`; `cancelled`/`canceled` → 2.4.
   - `subscription_authorized_payment` y `payment`: registra el pago (idempotente por `mp_payment_id`).
     Aprobado: `current_period_end` hasta el `next_payment_date` del preapproval. Rechazado: `past_due`.
4. **Conciliación** una vez por día: `GET /preapproval/{id}` de cada suscripción abierta.
5. Cambio de plan: `PUT` del monto. Baja: `PUT status: cancelled`; el tier dura hasta `current_period_end`.

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
| `app/billing/service.py` | Máquina de estados: pedido, pago, baja, caída al Free, números (`fit_numbers`) y el barrido (`tick`) |
| `app/billing/loop.py` | En el lifespan, cada `BILLING_TICK_SECONDS` (900): `tick` y borrar registros sin activar |
| `app/services/signup.py` | Registro y "olvidé mi clave" |
| `app/api/routers/billing.py` | `GET /clients/{id}/billing`, `POST .../billing/subscribe`, `.../cancel`, `PUT .../fiscal`. Admin: `POST .../billing/payments`, `.../suspend`, `GET /billing/subscriptions`, `GET /billing/payments`, `PATCH /billing/payments/{id}` |
| `app/api/routers/demo.py`, `auth.py` | `POST /demo/signup`, `POST /auth/password-reset` |
| `app/mail/messages.py` | Clave nueva, cómo pagar, aviso al admin, pago recibido, renovación, plan vencido, paso al Free |
| `app/services/calls.py` | Rechazo de entrantes a números suspendidos |
| `web/src/features/billing/` | `/plan` (cliente), tarjeta "Plan pago" de la ficha y vista Cobros (admin). Precio, público y orden en el formulario de tiers; `/forgot-password` |
| `landing/src/pages/registro.astro` | Registro; botones de `Pricing`, `Nav` y `/desarrolladores` hacia `/registro`. Los precios de `site.ts` se mantienen a mano iguales a `price_ars` |
| `tests/test_billing.py`, `web/src/features/billing/PlanPage.test.tsx` | Registro, clave, pedido, pago, vencimiento, gracia, Free, números y permisos |

Variables nuevas (`app/config.py`, `.env.example`): `SIGNUP_ENABLED`, `SIGNUP_IP_PER_HOUR`,
`SIGNUP_IP_PER_DAY`, `PASSWORD_RESET_IP_PER_HOUR`, `PASSWORD_RESET_EMAIL_PER_HOUR`,
`BANK_TRANSFER_INFO`, `BILLING_NOTIFY_TO`, `BILLING_GRACE_DAYS`, `BILLING_NUMBER_HOLD_DAYS`,
`BILLING_REMINDER_DAYS`, `BILLING_TICK_SECONDS`. En la fase 3: `MP_BILLING_ACCESS_TOKEN` y
`MP_BILLING_WEBHOOK_SECRET` (el prefijo no choca con las de `MERCADOPAGO_PLAN.md`).

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

**Consecuencia para la fase 3:** el flujo con tarjeta tokenizada (`authorized`) anduvo completo sin
pasar por la cuenta de MP del comprador, y una tarjeta mala falla en el acto. Si el `init_point` falla con
emails distintos, el camino es el **Card Payment Brick** en una página propia (relajar la CSP solo ahí).

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
