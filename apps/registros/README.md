# Registros

App de fichas de personas: API `/v1` para la plataforma (pre-call y post-call) y panel propio. Corre en su
contenedor, con su base `registros` y su rol, en la misma instancia de Postgres que la plataforma.
No importa código de `app/` ni de `crm/`, y no recibe `.env` de la plataforma. Cada tenant tiene su formulario, cargado en
la base; acá no hay formularios de ningún cliente. Cómo encaja en la plataforma, operación, backup, despliegue y riesgos:
[`docs/features/REGISTROS.md`](../../docs/features/REGISTROS.md). Contrato de la API: [`docs/API.md`](docs/API.md).

## Configuración

Variables, todas con prefijo `REGISTROS_`:

| Clave | Para qué |
|---|---|
| `DB_DSN` | Conexión con el rol `registros` |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | Pool; por defecto, 5 y 2 |
| `SESSION_SECRET` | Sesión del panel. Sin ella no hay login y `/health` da 503 |
| `SESSION_HOURS` | Duración de la sesión; por defecto, 12 |
| `PUBLIC_URL` | Base de los links y origen permitido. Con `https://`, la cookie sale `Secure` |

## Desarrollo

```sh
make registros-test      # tests, con su Postgres; sin servicios externos
make registros-dev       # la app en :8041 con datos de ejemplo, dos tenants y el admin (dev@admin.test)
make registros-dev-down  # la baja y borra los datos
```

Para migrar: `alembic upgrade head`, desde esta carpeta.

## Administrador

El tenant `admin` (`tenants.is_admin`, uno solo) no tiene fichas: sus usuarios entran con Espacio `admin` y administran los
demás desde `/admin` (API `/admin/api`, en [`registros/panel/admin.py`](registros/panel/admin.py)). Los administradores se crean
solo por CLI:

```sh
python -m registros.cli create-admin --email persona@atentina.com.ar   # pide la clave (12 o más)
```

Crea el tenant `admin` si falta y crea el usuario o, si existe, le cambia la clave y cierra sus sesiones. Se niega si ya hay
un tenant `admin` común. El admin ve y configura todos los demás tenants (no el suyo) y lee sus fichas sin editarlas.
**Nada de lo que hace queda en `audit_log`**: solo su login y logout, como cualquier usuario.

| `/admin/api` | Qué hace |
|---|---|
| `GET`, `POST /tenants`; `GET`, `PATCH /tenants/{id}` | Lista con conteos, alta (`slug`, `name`, `charge_amount`, `currency`), detalle con usuarios y claves, edición (el `slug` no se edita) |
| `PUT /tenants/{id}/active` | `{"active": true\|false}` → 204. Desactivar corta login, `/v1` y links, y borra las sesiones del espacio; reactivar revive las claves no revocadas, no las sesiones. `GET /tenants` y `/tenants/{id}` informan `active` |
| `GET`, `PUT /tenants/{id}/form` | Los tres archivos como texto: `form_html`, `schema` y `manifest`; lo bajado se puede volver a subir |
| `POST /tenants/{id}/users`; `PUT .../users/{uid}/password`, `.../active` | Alta (409 si existe), clave nueva y activar o desactivar; las dos últimas cierran sus sesiones |
| `POST /tenants/{id}/keys`; `DELETE .../keys/{kid}` | Clave de API (`key` sale solo en esa respuesta) y revocación, idempotente |
| `GET /tenants/{id}/persons`, `.../persons/{pid}` | Fichas en solo lectura, con los parámetros y la respuesta de `/panel/api/persons` |

Sin sesión, 401; un usuario de otro tenant, 404, como una ruta que no existe. El tenant `admin` y lo que es de otro tenant
que el de la ruta dan 404. Errores de validación, 422 con el motivo; un alta repetida, 409.

Pantallas (`admin.js`, mismas clases que el panel; todo dato entra con `textContent`):

| Ruta | Qué hay |
|---|---|
| `/admin` | Lista de espacios con conteos, formulario cargado y estado; "Nuevo espacio" (identificador, nombre, monto, moneda) |
| `/admin/espacios/{id}` | Activar o desactivar el espacio (con confirmación); datos (el monto rige para los cobros siguientes); formulario con tres archivos (`form.html`, `schema.json`, `manifest.json`) y "Bajar el actual"; usuarios (alta, clave nueva, activar o desactivar); claves de API (alta, revocación con confirmación) |
| `/admin/espacios/{id}/fichas`, `.../fichas/{pid}` | Búsqueda, filtro y paginado como `/personas`; la ficha como tabla campo → valor y sus cobros, sin editar |

La clave de API nueva se muestra una sola vez, en un recuadro para copiar, y no deja crear otra hasta cerrarlo; hay que cargarla en Atentina como `REGISTROS_READ_KEY` (`read`) o `REGISTROS_CHARGE_KEY` (`charge`). Las páginas siguen la regla de `AdminUser`: sin sesión, al login con `next`; un usuario de cliente, 404.

## Alta de un tenant

Desde `/admin/api` o por CLI (`python -m registros.cli`; en el stack, `make registros-cli ARGS="..."`, y `FORM=<carpeta>` monta el formulario en `/form`). Las dos validan igual ([`registros/admin_ops.py`](registros/admin_ops.py)):

```sh
python -m registros.cli create-tenant --slug empresa --name "Empresa" --amount 1000
python -m registros.cli load-form --tenant empresa --dir /ruta/al/formulario
python -m registros.cli create-user --tenant empresa --email persona@empresa.com
python -m registros.cli create-key --tenant empresa --scope read --name pre-call
python -m registros.cli create-key --tenant empresa --scope charge --name post-call
```

- `slug`: minúsculas, números y guiones, de 2 a 80, sin empezar por guion y distinto de `admin`. Monto de 0 a 9999999999.99, hasta 2 decimales; moneda de tres letras mayúsculas.
- `load-form` espera `form.html` (hasta 512 KB), `schema.json` y `manifest.json` (hasta 256 KB cada uno; ejemplo en `tests/fixtures/form_ejemplo/`) y rehace los teléfonos de las fichas ya cargadas. Bloquea la fila del tenant: dos cargas a la vez no se pisan. Más rutas en `contact_phone_paths` amplían a quién se le puede cobrar: se decide al cargar cada formulario.
- `create-user` con un correo que ya existe cambia la clave y cierra sus sesiones. Clave de 8 a 1024 caracteres.
- `create-key` muestra la clave una sola vez. `read` sirve para `identify` y `select`; `charge`, además, para `charges`. Usá `charge` solo en el post-call.
- Los comandos de la CLI no operan sobre el tenant `admin`.

## Sesión y límites

- Login por tenant en `POST /auth/login`, con `tenant`, `email` y `password`. Cookie `HttpOnly`, `SameSite=Lax`. El administrador entra igual, con `tenant` `admin`, y las páginas de fichas lo mandan a `/admin`.
- 5 intentos fallidos por correo cada 15 minutos, contados en todos los tenants. Después, 429, también con la clave correcta.
- Los pedidos no seguros sin `Authorization` deben venir del mismo origen.
- `tenant` o `email` con un NUL: 422, y ese intento no se anota en `audit_log` (es una ruta interna del panel, no parte de `/v1`).
- Sin límites en el borde: la app no topea el cuerpo de los pedidos ni limita el login por IP, y 5 intentos fallidos bloquean 15 minutos el login de un correo conocido. Riesgo aceptado ([`REGISTROS.md`](../../docs/features/REGISTROS.md)).

## Restauración

El dump sale `--no-owner`. Se restaura **conectado como `registros`**, para que ese rol quede como dueño de las tablas; restaurado con el superusuario, la app recibe `permission denied` y `/health` da 503. En el stack, `make registros-restore DUMP=<volcado .sql.gz>` crea antes el rol y la base si faltan y restaura con ese rol. A mano:

```sh
zcat registros-AAAA.sql.gz | psql -v ON_ERROR_STOP=1 -U registros -d registros
```

## Regenerar secretos

| Secreto | Cómo | Efecto |
|---|---|---|
| `REGISTROS_SESSION_SECRET` | Valor nuevo (`openssl rand -hex 32`) y reiniciar la app | Se cierran todas las sesiones |
| `REGISTROS_DB_PASSWORD` | `ALTER ROLE registros PASSWORD '...'`, el valor nuevo en la configuración y reiniciar la app | Ninguno, aparte del reinicio |
| Clave de API | Una nueva (`create-key` o `POST /admin/api/tenants/{id}/keys`), cambiarla en la herramienta del agente y revocar la vieja (`DELETE /admin/api/tenants/{id}/keys/{kid}`) | La vieja da 401 |
| Clave de un usuario | `create-user` con el mismo correo o `PUT /admin/api/tenants/{id}/users/{uid}/password` | Se cierran sus sesiones |
| Clave de un administrador | `create-admin` con el mismo correo | Se cierran sus sesiones |
