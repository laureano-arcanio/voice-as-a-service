# Admin separado y "ver como cliente" (27-oct-2026)

El panel tenía una sola UI para el admin y los clientes, con ~180 `isAdmin` en `web/src`: el admin
operaba los agentes de `atentina` usando su acceso a todos los clientes. Este plan separa las dos
cosas: el admin administra en `/admin/*` y, para dar soporte o trabajar con los agentes propios,
entra como un cliente y ve exactamente su panel.

## 1. Decisiones (con el usuario, 27-oct-2026)

| Tema | Decisión |
|---|---|
| Área del admin | `/admin/*`, con su layout y su menú. Un admin que inicia sesión va siempre a `/admin`. |
| Vistas de todos los clientes en `/admin` | Reportes de plataforma, Conversaciones, Uso de la API, Agentes (solo lectura), Clientes, Números, Tiers, Cobros, Usuarios. El resto (herramientas, contactos, WhatsApp, campañas, equipo...) se ve entrando como el cliente. |
| Ver como cliente | El admin entra a un cliente sin loguearse con otro usuario. Puede hacer todo lo que hace el cliente, sin auditoría. |
| Dónde vive el cliente activo | Por pestaña (`sessionStorage`): sobrevive a una recarga y cada pestaña puede estar en otro cliente. Las rutas de cliente no cambian. |
| JSON, slug y prompt armado del agente | Para todos los clientes (el backend ya aceptaba la definición entera; `preview-prompt` se abre a los agentes propios). |
| Conexiones LLM a la red interna (`allow_private`) | Se quita la excepción del admin: todos con https y host público (no había ninguna conexión cargada). |
| Datos técnicos de las conversaciones | Entrando como cliente, se ve lo mismo que el cliente. Latencia, agente, cliente y borrar quedan en `/admin/conversaciones`. |
| Plan, Mi cuenta y perfil en modo soporte | Solo lectura: pagar, cambiar o dar de baja el plan, datos fiscales, aceptar condiciones y el perfil dan 403 `support_read_only`. Los resúmenes por email de Mi cuenta siguen editables (son de operación). |
| Tier interno | `tiers.internal` (migración 0037) en lugar de comparar con el nombre "Interno". |
| WhatsApp | El cliente conecta su número con **su propia app de Meta** (token, app secret, webhook por cuenta), con una guía. Embedded Signup se apaga con `WA_EMBEDDED_SIGNUP=false` sin borrar código (falta el Tech Provider). Ver la sección 4. |

## 2. Backend

- **Principal de soporte** (`app/api/deps.py`, `get_principal`): con sesión de un usuario `admin` y el
  header `X-Atentina-Client: <client_id>`, el pedido es `Principal(role=client, client_id=<ese>,
  support=True)`. Igual que `MCP_CLIENT_HEADER` del MCP. Lo ignoran las API keys y los tokens OAuth.
  Un cliente inexistente da 404. El CSRF por `Origin` ya cubre las escrituras.
- `GET /auth/me` en modo soporte: el `Me` del cliente (`role=client`, `client_id`, `client_name`, marca)
  con `support: true` y el nombre y mail del admin; sin `legal_pending` ni bienvenida.
- **Solo lectura en soporte:** `/auth/me/*` (perfil, clave, mail, condiciones, bienvenida) y las
  escrituras de cobros y plan del cliente (`require_not_support`).
- Lo que el admin podía y el cliente no: `preview-prompt` pasa a cualquiera con acceso al agente;
  `allow_private` desaparece; los números de la WABA compartida (`_get_managed`) los administra un
  admin o el admin en soporte.
- `handoff.py`: `get_member`/`get_area` validan el cliente (`ensure_access`).

## 3. Frontend (`web/`)

- `src/api/client.ts`: middleware que agrega `X-Atentina-Client` si la pestaña está en un cliente
  (`src/features/support/`: `useSupportSwitch()` con `enter(clientId, path)` y `exit()`, `useAreaPath()` para los links de las pantallas de las dos áreas, `supportUrl()` para abrirlo en otra pestaña). Al entrar o salir
  se vacía la caché de TanStack Query (las keys no llevan el cliente) y se relee `me`.
- Rutas: `/admin/*` con `AppLayout` (menú `ADMIN_NAV`) y `RequireAdminArea`; las de cliente quedan en `/`. Un admin sin
  cliente activo que abre una ruta de cliente va a `/admin`; con cliente activo, ve el panel del cliente
  con la marca "soporte" y el botón "Volver a administración", que es la única forma de salir (abrir `/admin` en
  esa pestaña lleva al panel del cliente).
- En modo soporte `me.role === 'client'`, así que `useIsAdmin()` es falso en las pantallas del cliente:
  las ramas `isAdmin` de las pantallas que el admin ya no abre se borran.
- La vista previa de la marca (`branding:preview`) se reemplaza por entrar como el cliente.

## 4. WhatsApp con la app de Meta del cliente

Sin Tech Provider no hay Embedded Signup. El cliente usa su propia app de Meta:

1. Crea en su Business Manager una app de Meta (tipo Business) con el producto WhatsApp, la pasa a
   modo Live (pide URL de política de privacidad) y un usuario de sistema con token permanente con
   `whatsapp_business_messaging` y `whatsapp_business_management` sobre su WABA.
2. En el panel (WhatsApp → "Conectar con mi app de Meta") carga `phone_number_id`, `waba_id`, el token
   y el app secret, y elige el agente. La app valida con Graph que el número sea de esa WABA y suscribe
   su app a la WABA (`subscribed_apps`). Token y secret se guardan cifrados (`WA_TOKEN_KEY`).
3. El panel le da la **URL del webhook de esa cuenta** (`https://wa.atentina.com.ar/wa/webhook/<clave>`)
   y su **verify token**; los pega en su app (Webhooks → WhatsApp Business Account) y suscribe `messages`.

- `wa_accounts`: `app_secret` (cifrado), `webhook_key` (única) y `verify_token` (cifrado); `source = own_app`.
- `GET/POST /wa/webhook/{key}`: verifica con el token y el secreto de esa cuenta y solo procesa los
  cambios de su WABA y su número. `/wa/webhook` sigue para la WABA de Atentina.
- El túnel ya rutea `^/wa/webhook`: no hay que tocar Cloudflare.
- A verificar con un número real: que una app en Live sin App Review reciba los webhooks de sus
  propios números, y que un número que está en la app WhatsApp Business del celular no puede usarse
  a la vez por la API sin coexistencia (necesita Embedded Signup).
- Las llamadas de WhatsApp por SIP siguen solo con el número de Atentina.

## 5. Cómo desplegar

`make migrate` (0037 y 0038), `make calls-active && make up-agent` (recrea `app` y `agent`) y
`make web-build` si la UI no se construye en la imagen.

Desplegado el 27-oct-2026: `make migrate-test` (0034 → 0038 sobre el backup, ida y vuelta), `make up-agent`
(base en 0038, Interno con `internal=true`) y `make reports-backfill` (36 conversaciones, por la 0036
que entró en el mismo despliegue). Embedded Signup quedó apagado (sin `WA_EMBEDDED_SIGNUP` en `.env`).
