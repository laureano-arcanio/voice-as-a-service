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
make registros-dev       # la app en :8041 con datos de ejemplo y dos tenants
make registros-dev-down  # la baja y borra los datos
```

Para migrar: `alembic upgrade head`, desde esta carpeta.

## Alta de un tenant

Por CLI (`python -m registros.cli`; en el stack, `make registros-cli ARGS="..."`, y `FORM=<carpeta>` monta el formulario en `/form`):

```sh
python -m registros.cli create-tenant --slug empresa --name "Empresa" --amount 1000
python -m registros.cli load-form --tenant empresa --dir /ruta/al/formulario
python -m registros.cli create-user --tenant empresa --email persona@empresa.com
python -m registros.cli create-key --tenant empresa --scope read --name pre-call
python -m registros.cli create-key --tenant empresa --scope charge --name post-call
```

- `load-form` espera `form.html`, `schema.json` y `manifest.json` (ejemplo en `tests/fixtures/form_ejemplo/`) y rehace los teléfonos de las fichas ya cargadas. Más rutas en `contact_phone_paths` amplían a quién se le puede cobrar: se decide al cargar cada formulario.
- `create-user` con un correo que ya existe cambia la clave y cierra sus sesiones.
- `create-key` muestra la clave una sola vez. `read` sirve para `identify` y `select`; `charge`, además, para `charges`. Usá `charge` solo en el post-call.

## Sesión y límites

- Login por tenant en `POST /auth/login`, con `tenant`, `email` y `password`. Cookie `HttpOnly`, `SameSite=Lax`.
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
| Clave de API | `create-key` con una nueva, cambiarla en la herramienta del agente y revocar la vieja | La vieja da 401 |
| Clave de un usuario | `create-user` con el mismo correo | Se cierran sus sesiones |

Para revocar una clave de API, en `psql`:

```sql
UPDATE api_keys SET revoked_at = now() WHERE name = 'post-call' AND tenant_id = (SELECT id FROM tenants WHERE slug = 'empresa');
```
