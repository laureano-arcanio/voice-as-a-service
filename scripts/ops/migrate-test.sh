#!/usr/bin/env bash
# Prueba las migraciones pendientes contra una copia del último backup de la base, antes de `make
# migrate`: PostgreSQL 16 temporal (contenedor y red propios, sin puertos del host), restaura el
# volcado, corre `alembic upgrade head`, `downgrade` a la revisión del backup y `upgrade head` otra vez,
# con el código de este checkout montado en la imagen de `app`. No toca la base viva. Uso:
#   make migrate-test            # el último db-*.sql.gz de BACKUP_DIR
#   make migrate-test DUMP=...   # otro volcado
set -euo pipefail
cd "$(dirname "$0")/../.."

DEST="${BACKUP_DIR:-$HOME/atentina-backups}"
DUMP="${DUMP:-$(ls -t "$DEST"/db/db-*.sql.gz 2>/dev/null | head -1)}"
[[ -r "$DUMP" ]] || { echo "No hay volcado de la base en $DEST/db (o DUMP=$DUMP no se puede leer)" >&2; exit 1; }
PG_USER="$(grep -m1 '^POSTGRES_USER=' .env | cut -d= -f2-)"
PG_DB="$(grep -m1 '^POSTGRES_DB=' .env | cut -d= -f2-)"
NAME=atentina-migtest
IMAGE="${IMAGE:-voice-as-a-service-app:latest}"

cleanup() { docker rm -f "$NAME-db" >/dev/null 2>&1 || true; docker network rm "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup
docker network create --internal "$NAME" >/dev/null
docker run -d --name "$NAME-db" --network "$NAME" -e POSTGRES_USER="$PG_USER" -e POSTGRES_DB="$PG_DB" \
  -e POSTGRES_PASSWORD=migtest postgres:16-alpine >/dev/null
until docker exec "$NAME-db" pg_isready -U "$PG_USER" -d "$PG_DB" -q 2>/dev/null; do sleep 1; done
sleep 2
echo "Restaurando $(basename "$DUMP")..."
zcat "$DUMP" | docker exec -i "$NAME-db" psql -q -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$PG_DB" >/dev/null
FROM="$(docker exec "$NAME-db" psql -tA -U "$PG_USER" -d "$PG_DB" -c 'select version_num from alembic_version')"
echo "Revisión del backup: $FROM"

alembic() {
  docker run --rm --network "$NAME" -e DB_DSN="postgresql+psycopg://$PG_USER:migtest@$NAME-db:5432/$PG_DB" \
    -e AUTH_SECRET=migtest -v "$PWD/app:/app/app:ro" -v "$PWD/migrations:/app/migrations:ro" \
    -v "$PWD/alembic.ini:/app/alembic.ini:ro" "$IMAGE" alembic "$@"
}
alembic upgrade head
alembic downgrade "$FROM"
alembic upgrade head
echo "OK: $FROM -> $(docker exec "$NAME-db" psql -tA -U "$PG_USER" -d "$PG_DB" -c 'select version_num from alembic_version'), ida y vuelta sobre la copia de $(basename "$DUMP")"
