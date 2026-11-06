# Registros

App de fichas de personas (`apps/registros/`) con API `/v1` para la plataforma y panel propio. La plataforma habla con
ella solo por API, desde herramientas del cliente: identifica a quien llama por su teléfono (pre-call), guarda la ficha
que la persona confirma y registra un cobro simulado (post-call). Estado: implementado y probado en local; sin desplegar
y sin probar con Meta ni con una llamada real.

Contrato de la API, ejemplos de las herramientas y alta de un tenant: [`apps/registros/docs/API.md`](../../apps/registros/docs/API.md)
y [`apps/registros/README.md`](../../apps/registros/README.md). Acá, lo que une la app con el resto.

## Cómo encaja

```text
agente (voz o WhatsApp) ── pre-call  buscar_ficha ──────► POST /v1/identify
                        ── visible   elegir_persona ────► POST /v1/identify/select
                        ── post-call registrar_cobro ───► POST /v1/charges   (clave `charge`)
operador (WhatsApp) ◄── aviso con el link /c/<token> ──► panel: login, fichas
```

Son herramientas `http` comunes del cliente ([`HERRAMIENTAS.md`](HERRAMIENTAS.md)) y workflows del agente: la plataforma
no sabe qué es una ficha ni un cobro, y Registros no importa código de `app/` ni de `crm/` (`apps/registros/tests/test_app.py`; la plataforma tampoco lo importa ni
lo lleva en su imagen: `tests/test_apps_isolation.py`). Las herramientas solo salen a https público, así que la ruta del túnel es obligatoria.

## Modelo

Base `registros` y rol `registros` en la misma instancia de Postgres que la plataforma (como el CRM, con rol propio).
Migraciones propias en `apps/registros/migrations/` (`0001_inicial`, `0002_admin`, `0003_tenant_active`).

| Tabla | Qué guarda |
|---|---|
| `tenants` | `slug`, monto del cobro y el formulario del tenant (`form_html`, `form_schema`, `manifest`), cargado por CLI o por el admin; `is_admin` marca el tenant `admin` (uno solo, índice único parcial); `active` (ver "Espacio desactivado") |
| `users`, `sessions`, `api_keys` | Login del panel; claves de la API con alcance `read` o `charge` (hash, se muestran una vez) |
| `persons`, `person_phones` | Ficha (datos del formulario, `al_dia`, versión, baja lógica) y sus teléfonos, sacados del formulario por el manifiesto |
| `conversation_choices` | La ficha que la persona confirmó en una conversación, para el link y el cobro |
| `charges` | Un cobro por `(tenant, conversation_id)`; hoy `simulated` |
| `record_links` | Link `/c/<token>` de una conversación, con vencimiento |
| `audit_log` | Login, vistas y cambios de fichas, aperturas de link. Nada de lo que hace el admin |

Aislamiento por tenant en cada consulta. El panel no tiene formularios de ningún cliente en el código.

**Administrador:** los usuarios del tenant `admin` (creados solo con `create-admin`) gestionan los demás tenants desde
`/admin` (`/admin/api`): datos, formulario, usuarios, claves de API, activar o desactivar y lectura de fichas. Detalle y
rutas: README de la app.

**Espacio desactivado** (`PUT /admin/api/tenants/{id}/active`; el tenant `admin` no se desactiva): se borran las sesiones
de sus usuarios, el login responde como a un espacio inexistente, una sesión que quede no vale (panel y páginas mandan al
login, también `/c/<token>`) y `/v1` responde **403 "Espacio desactivado"** a una clave válida (401 sigue siendo clave
inválida o revocada). El pre-call falla sin reintento y el agente atiende sin la ficha; el post-call queda `failed` y esa
conversación no se cobra. Desactivar espera a los cobros en curso: después del 204 no se registra ninguno. El admin sigue
viendo y editando el espacio y sus fichas. Reactivar revive las claves no revocadas y el login; las sesiones no vuelven.

## Operación

El servicio `registros` del compose tiene el perfil `registros`: `make up`, `docker compose up --wait` (`deploy/boot.sh`)
y `healthcheck.sh` no lo ven, y su estado no condiciona el arranque del resto. Sin `env_file`: solo recibe las
variables `REGISTROS_*`, no los secretos de la plataforma. Pool de 7 conexiones (`db` comparte `max_connections` con
`app`, `agent` y `crm`). Escucha en `127.0.0.1:8040`.

| Comando | Qué hace |
|---|---|
| `make registros-up` | `registros-db` y migraciones con su rol; levanta con `--wait`. No toca `app`, `agent` ni `db` |
| `make registros-down` | Lo para; la base queda |
| `make registros-cli ARGS="..."` | Tenants, formulario (`FORM=<carpeta>`), usuarios, claves de API y administradores (`create-admin`) |
| `make registros-restore DUMP=...` | Restaura un volcado conectado como `registros`, que queda dueño de las tablas |
| `make registros-logs`, `registros-psql` | Logs y `psql` con su rol |
| `make registros-test`, `registros-dev`, `registros-dev-down` | Tests con su Postgres; app de QA en `:8041` con datos de ejemplo |
| `make registros-ops-test` | Rol, permisos, restauración y perfil de compose contra un Postgres temporal |

- **Rol y permisos** (`scripts/ops/registros_db.sh`, idempotente): crea el rol y la base, y quita `CONNECT` de `PUBLIC` en
  la base de la plataforma y en `crm`; la plataforma y el CRM usan `POSTGRES_USER`, dueño, y no lo notan. El `REVOKE` no
  viaja en un volcado: si `crm` se restaura o se crea después, volver a correr `make registros-db`.
- **Backup:** `BACKUP_EXTRA_DBS=registros` en el `.env` suma un volcado de esa base a `backup.sh` (mismo directorio,
  retención y copia a S3 que la base principal). **Una base listada que no existe hace fallar el backup**, y
  `healthcheck.sh` avisa a las 26 h. Los secretos de Registros están en el `.env`, que el backup ya copia.
- **Restauración:** el volcado es `--no-owner`; restaurarlo con el superusuario deja las tablas ajenas y la app da
  `permission denied` (`/health` en 503). `make registros-restore` pasa antes por `registros-db`. `backup-fetch.sh`
  imprime el comando cuando baja un `registros.sql.gz`.
- **Salud:** `REGISTROS_HEALTH_URL` significa "Registros activo en este host": `deploy/boot.sh` lo levanta al arrancar el
  host (último paso, sin `--wait`, sin que su falla corte llamadas ni WhatsApp) y `healthcheck.sh` avisa por ntfy si no
  da 200. Sin la clave, ninguno de los dos lo mira. `/health` lee una tabla, no hace `SELECT 1`: una restauración con
  otro dueño o sin migrar también da 503.
- **Claves** (`.env.example`): `REGISTROS_DB_PASSWORD` (solo letras, números, `_` y `-`: va en una URL),
  `REGISTROS_SESSION_SECRET`, `REGISTROS_PUBLIC_URL`, `REGISTROS_SESSION_HOURS`, `REGISTROS_DB_POOL_SIZE`,
  `REGISTROS_DB_MAX_OVERFLOW`, `REGISTROS_HEALTH_URL`. Regenerarlas: README de la app.

## Desplegar

Con la plataforma ya desplegada (las herramientas y los workflows que usan los `/v1` viven en `app`):

1. Claves en el `.env` de server2 (diff enmascarado): `REGISTROS_DB_PASSWORD`, `REGISTROS_SESSION_SECRET`,
   `REGISTROS_PUBLIC_URL=https://registros.atentina.com.ar`.
2. `make registros-up`.
3. Administrador: `make registros-cli ARGS="create-admin --email ..."` (pide la clave). Tenant, formulario, usuario y
   claves `read` y `charge`: desde `/admin` o con `make registros-cli` (README de la app).
4. Ruta del túnel `registros.atentina.com.ar` → `http://127.0.0.1:8040` (la crea el usuario).
5. `BACKUP_EXTRA_DBS=registros` y `REGISTROS_HEALTH_URL=http://127.0.0.1:8040/health` en el `.env`; volver a correr
   `make registros-up`. Comprobar un `make backup` y una restauración en una base vacía.
6. Cargar las claves de la API como secretos del cliente (`REGISTROS_READ_KEY`, `REGISTROS_CHARGE_KEY`) y configurar el
   agente y las plantillas.

**Vuelta atrás:** sacar `REGISTROS_HEALTH_URL` del `.env` y `make registros-down`. La base queda intacta y no hay alerta.
Sin Registros los workflows fallan, el agente atiende y deriva igual, y los post-call se reintentan y quedan `failed`.
`REVOKE CONNECT` se deshace con `GRANT CONNECT ON DATABASE ... TO PUBLIC`.

## Riesgos aceptados

- **Datos sensibles legibles** (el formulario de un tenant puede pedir datos de salud): sin cifrado propio, en la instancia compartida, en los backups y con `make psql` para quien
  opere el server.
- **Backups solo en server2** ([`INFRA.md`](../INFRA.md)): perder ese server es perder la base, las fichas y los backups.
- **Sin límites en el borde:** `registros.atentina.com.ar` se expone sin tope de cuerpo ni límite de login por IP. Los
  intentos fallidos se cuentan por correo (5 cada 15 minutos): quien sepa un correo puede bloquearle el login 15 minutos.
- **Una persona cargada como contacto en una sola ficha** que llama por otra ficha cobra a esa ficha: sin anulación y
  sin detección de caller ID falsificado. La nota del operador la nombra y el cobro se ve en el panel.
- **Cualquier usuario del tenant** que abra el link ve la ficha completa, igual que en el panel; la apertura queda en
  `audit_log`. Un link reenviado no abre sin login.
- **El modelo elige la ficha** por lo que entendió de la persona: se cobra a esa, y la nota la nombra.
- **El admin ve todas las fichas y nada de lo que hace queda registrado** (decisión del usuario): ni sus vistas de fichas ni
  sus cambios (altas, formularios, montos, claves de usuario, claves de API creadas o revocadas) van a `audit_log`; solo su
  login y logout. Un acceso o un cambio indebido no se puede reconstruir.
- **Sesión del admin robada = todos los tenants y todas sus fichas**, sin rastro. Cookie `HttpOnly`, `SameSite=Lax`,
  `Secure` con https, 12 h; CSRF por `Origin`. No puede crear administradores (solo `create-admin`); desactivarlo o
  cambiarle la clave cierra sus sesiones.
- **Bloqueo del login del admin:** el límite de intentos es por correo; quien sepa el correo de un administrador le bloquea el
  login 15 minutos. La CLI sigue andando.
- **Registros en la red de la plataforma:** `app`, `agent` y demás alcanzan su puerto sin credenciales; la API exige clave.

## Pendientes

- Pasarela de pago real: el cobro es simulado (`charges.status = simulated`).
- Anulación de cobros.
- Cifrado propio y adjuntos: el formulario solo marca "documento recibido".
- Identificación por nombre, DNI o código: hoy solo por teléfono.
- Probar con un operador real: el aviso por WhatsApp, el link y la sesión, y un cobro de punta a punta.
