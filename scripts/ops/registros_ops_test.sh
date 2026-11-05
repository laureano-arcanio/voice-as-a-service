#!/usr/bin/env bash
# Prueba de operación de Registros (make registros-ops-test): rol, permisos, idempotencia, restauración y
# perfil de compose, con los targets reales de make contra un PostgreSQL 16 temporal (red interna propia,
# sin puertos del host). No toca la base viva ni el stack: DB_EXEC y COMPOSE apuntan a lo temporal.
set -euo pipefail
cd "$(dirname "$0")/../.."

NAME=atentina-regops
DB="$NAME-db"
APP="$NAME-app"
DOWN_PROJECT="$NAME-down"
PG_USER=regops_admin
PG_DB=regops_principal
ROLE_PASSWORD=regops_clave
mkdir -p scratch
TMP="$(mktemp -d "$PWD/scratch/registros-ops-XXXXXX")"
DOWN_COMPOSE="docker compose -p $DOWN_PROJECT -f $TMP/down.yml"

cat > "$TMP/down.yml" <<YAML
services:
  base:
    image: postgres:16-alpine
    command: ["sleep", "300"]
  con-perfil:
    profiles: ["registros"]
    image: postgres:16-alpine
    command: ["sleep", "300"]
YAML

cleanup() {
    docker rm -f "$APP" "$DB" >/dev/null 2>&1 || true
    docker network rm "$NAME" >/dev/null 2>&1 || true
    $DOWN_COMPOSE --profile registros down -t 0 >/dev/null 2>&1 || true
    rm -rf "$TMP"
}
trap cleanup EXIT
docker rm -f "$APP" "$DB" >/dev/null 2>&1 || true; docker network rm "$NAME" >/dev/null 2>&1 || true

failed() { echo "FALLA: $*" >&2; exit 1; }
ok() { echo "ok: $*"; }

# --- Perfil de compose ---
# Valores de prueba para las variables obligatorias, en lugar del .env del host.
grep -ohE '\$\{[A-Z0-9_]+:\?' docker-compose.yml docker-compose.replica.yml \
    | sed -E 's/\$\{([A-Z0-9_]+):\?/\1=127.0.0.1/' | sort -u > "$TMP/compose.env"
services() { env -u COMPOSE_PROFILES docker compose --env-file "$TMP/compose.env" -f docker-compose.yml "$@" config --services 2>/dev/null; }
services | grep -qx db || failed "compose no lista db sin perfil"
services | grep -qx registros && failed "registros aparece sin el perfil"
services --profile registros | grep -qx registros || failed "registros no aparece con el perfil"
ok "registros solo con su perfil de compose"

# --- Targets ---
up_lines="$(make --no-print-directory -n registros-up)"
[[ "$up_lines" == *STACK_ROLE=replica* ]] || failed "registros-up sin solo-principal"
[[ "$(grep -E ' up ' <<<"$up_lines")" == "docker compose --profile registros up -d --build --no-deps --wait registros" ]] \
    || failed "registros-up levanta otra cosa: $up_lines"
grep -qE '(^| )(app|agent)( |$)' <<<"$up_lines" && failed "registros-up menciona app o agent: $up_lines"
ok "registros-up no toca app ni agent"

$DOWN_COMPOSE --profile registros up -d --quiet-pull >/dev/null 2>&1 || failed "no levantó el proyecto de prueba de make down"
make --no-print-directory down COMPOSE="$DOWN_COMPOSE" >/dev/null 2>&1 || failed "make down falló con el perfil"
[[ -z "$(docker ps -aq --filter "label=com.docker.compose.project=$DOWN_PROJECT")" ]] || failed "make down dejó contenedores"
[[ -z "$(docker network ls -q --filter "label=com.docker.compose.project=$DOWN_PROJECT")" ]] || failed "make down dejó la red"
ok "make down baja también lo que tiene el perfil"

# En la réplica, db está fuera y --profile registros es inválido: make down tiene que seguir andando.
# --dry-run y un proyecto propio: no baja nada de este host.
make --no-print-directory down \
    COMPOSE="docker compose --dry-run -p $NAME-replica --env-file $TMP/compose.env -f docker-compose.yml -f docker-compose.replica.yml" >/dev/null 2>&1 \
    || failed "make down falla con la réplica"
ok "make down sirve con el compose de la réplica"

# --- Rol y permisos ---
docker network create --internal "$NAME" >/dev/null
docker run -d --name "$DB" --network "$NAME" -e POSTGRES_USER="$PG_USER" -e POSTGRES_DB="$PG_DB" \
    -e POSTGRES_PASSWORD=regops postgres:16-alpine >/dev/null
# Por TCP: durante la carga inicial Postgres solo atiende por socket.
wait_db() { until docker exec "$DB" pg_isready -h 127.0.0.1 -U "$PG_USER" -d "$PG_DB" -q 2>/dev/null; do sleep 1; done; }
wait_db

sql() { local user="$1" base="$2"; shift 2; docker exec -i "$DB" psql -X -q -tA -v ON_ERROR_STOP=1 -U "$user" -d "$base" "$@"; }
export DB_EXEC="docker exec -i $DB" REGISTROS_DB_PASSWORD="$ROLE_PASSWORD"
registros_db() { make --no-print-directory registros-db >/dev/null; }

sql "$PG_USER" "$PG_DB" -c 'create database crm'
registros_db

for base in "$PG_DB" crm; do
    err="$(sql registros "$base" -c 'select 1' 2>&1)" && failed "el rol registros se conecta a $base"
    [[ "$err" == *"permission denied for database"* ]] || failed "conexión a $base: $err"
    [[ "$(sql "$PG_USER" "$base" -c 'select 1')" == 1 ]] || failed "POSTGRES_USER no se conecta a $base"
done
[[ "$(sql registros registros -c 'select 1')" == 1 ]] || failed "el rol registros no se conecta a su base"
[[ "$(sql "$PG_USER" "$PG_DB" -c "select rolsuper, rolcreatedb, rolcreaterole from pg_roles where rolname = 'registros'")" == "f|f|f" ]] \
    || failed "el rol registros tiene privilegios de más"
ok "el rol solo entra a su base, y POSTGRES_USER a todas"

over_tcp() { docker run --rm --network "$NAME" -e PGPASSWORD="$1" postgres:16-alpine psql -X -tA -h "$DB" -U registros -d registros -c 'select 1' 2>/dev/null; }
[[ "$(over_tcp "$ROLE_PASSWORD")" == 1 ]] || failed "la clave de REGISTROS_DB_PASSWORD no conecta por red"
over_tcp clave-incorrecta >/dev/null && failed "por red entra con otra clave"
ok "la clave del rol es la de REGISTROS_DB_PASSWORD"

snapshot='select rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin, rolpassword from pg_authid order by 1;
          select datname, pg_get_userbyid(datdba), datacl from pg_database order by 1'
before="$(sql "$PG_USER" "$PG_DB" -c "$snapshot")"
registros_db
[[ "$(sql "$PG_USER" "$PG_DB" -c "$snapshot")" == "$before" ]] || failed "registros-db dos veces cambió algo"
ok "registros-db dos veces no cambia nada"

REGISTROS_DB_PASSWORD='con@arroba' make --no-print-directory registros-db >/dev/null 2>&1 && failed "acepta una clave que rompe la URL de conexión"
ok "rechaza una clave que rompe la URL de conexión"

# --- Backup y restauración ---
# El mismo pg_dump de backup.sh: si cambia allá, esta prueba deja de valer.
grep -qF "pg_dump -U \"\$POSTGRES_USER\" -d \"\$1\" --no-owner" scripts/ops/backup.sh || failed "backup.sh cambió el pg_dump"
sql registros registros -c "create table fichas (id serial primary key, nombre text not null); insert into fichas (nombre) values ('uno')"
docker exec "$DB" sh -c 'pg_dump -U "$POSTGRES_USER" -d "$1" --no-owner' sh registros | gzip > "$TMP/registros.sql.gz"

make --no-print-directory registros-restore DUMP="$TMP/registros.sql.gz" >/dev/null 2>&1 && failed "restaura sobre una base con datos"
[[ "$(sql registros registros -c 'select count(*) from fichas')" == 1 ]] || failed "la restauración fallida cambió los datos"
ok "no restaura sobre una base con datos"

docker exec "$DB" dropdb -U "$PG_USER" registros
echo basura > "$TMP/roto.sql.gz"
make --no-print-directory registros-restore DUMP="$TMP/roto.sql.gz" >/dev/null 2>&1 && failed "un volcado roto termina sin error"
make --no-print-directory registros-restore DUMP="$TMP/no-existe.sql.gz" >/dev/null 2>&1 && failed "un volcado inexistente termina sin error"
ok "un volcado roto o inexistente falla a la vista"

docker exec "$DB" dropdb -U "$PG_USER" registros
make --no-print-directory registros-restore DUMP="$TMP/registros.sql.gz" >/dev/null
[[ "$(sql registros registros -c "select tableowner from pg_tables where tablename = 'fichas'")" == registros ]] \
    || failed "la tabla restaurada no es del rol registros"
sql registros registros -c "insert into fichas (nombre) values ('dos'); update fichas set nombre = 'tres' where nombre = 'uno'"
[[ "$(sql registros registros -c 'select count(*) from fichas')" == 2 ]] || failed "el rol no lee ni escribe lo restaurado"
err="$(sql registros "$PG_DB" -c 'select 1' 2>&1)" && failed "tras restaurar, el rol entra a la principal: $err"
ok "restaurado con el comando de registros-restore: el rol es dueño, lee y escribe"

# --- La imagen real con el rol real ---
docker build -q -t "$NAME-app" apps/registros >/dev/null
dsn="postgresql+psycopg://registros:$ROLE_PASSWORD@$DB:5432/registros"
docker run --rm --network "$NAME" -e REGISTROS_DB_DSN="$dsn" "$NAME-app" alembic upgrade head >/dev/null 2>&1 || failed "alembic no corre con el rol registros"
docker run -d --name "$APP" --network "$NAME" -e REGISTROS_DB_DSN="$dsn" -e REGISTROS_SESSION_SECRET=regops "$NAME-app" >/dev/null
health() {
    docker exec "$APP" python -c "
import urllib.request, urllib.error
try:
    print(urllib.request.urlopen('http://127.0.0.1:8040/health', timeout=8).status)
except urllib.error.HTTPError as e:
    print(e.code)
except OSError:
    print('sin respuesta')" 2>/dev/null
}
wait_health() { for _ in {1..40}; do [[ "$(health)" == "$1" ]] && return 0; sleep 1; done; failed "/health nunca dio $1 ($2)"; }
wait_health 200 "migrada con el rol registros"
ok "la imagen migra y atiende con el rol registros"

docker stop -t 5 "$DB" >/dev/null
docker restart -t 5 "$APP" >/dev/null
wait_health 503 "reiniciada antes que db"
docker start "$DB" >/dev/null
wait_db
wait_health 200 "db volvió, sin reiniciar la app"
ok "reiniciada antes que db: da 503 y al volver la base, 200"

echo "OK: registros-ops-test"
