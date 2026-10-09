#!/usr/bin/env bash
# Prueba de restauración del backup (docs/PRODUCCION.md 3.E): restaura el último dump de
# BACKUP_DIR en un PostgreSQL 16 DESECHABLE (contenedor vaas-restore-test, 127.0.0.1:55433, datos
# en tmpfs), corre `alembic upgrade head` con el código de este árbol (.venv) y cuenta clientes,
# agentes, números y cuentas de WhatsApp. Imprime tiempos y conteos, nunca datos. El contenedor se
# borra siempre al final. No toca la base de producción ni el stack.
# Uso: scripts/ops/restore-test.sh [dump.sql.gz]   (requiere docker y .venv con requirements.txt)
set -euo pipefail
cd "$(dirname "$0")/../.."

env_get() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- || true; }
DEST="${BACKUP_DIR:-$HOME/atentina-backups}"
NAME=vaas-restore-test
PORT=55433
# Misma imagen que `db` (docker-compose.yml), fijada por digest.
IMAGE=postgres:16-alpine@sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea

dump="${1:-$(find "$DEST/db" -name 'db-*.sql.gz' -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)}"
[[ -f "$dump" ]] || { echo "no hay dump en $DEST/db" >&2; exit 1; }
[[ -x .venv/bin/alembic ]] || { echo "falta .venv con alembic (python -m venv .venv && .venv/bin/pip install -r requirements.txt)" >&2; exit 1; }

# Mismo usuario que producción: el dump (--no-owner) puede traer GRANTs a ese rol.
user="$(env_get POSTGRES_USER)"; user="${user:-postgres}"
db=restore_test
pass="$(head -c 18 /dev/urandom | base64 | tr -d '/+=')"
dsn="postgresql+psycopg://$user:$pass@127.0.0.1:$PORT/$db"

t0=$(date +%s%N)
lap() { local now; now=$(date +%s%N); printf '%-26s %6d ms\n' "$1" $(((now - t0) / 1000000)); t0=$now; }
cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup   # restos de una corrida cortada

echo "dump: $(basename "$dump") ($(du -h "$dump" | cut -f1), de $(date -r "$dump" '+%F %T'))"
docker run -d --rm --name "$NAME" -p "127.0.0.1:$PORT:5432" --tmpfs /var/lib/postgresql/data \
    -e POSTGRES_USER="$user" -e POSTGRES_PASSWORD="$pass" -e POSTGRES_DB="$db" "$IMAGE" >/dev/null
# -h 127.0.0.1: por socket responde durante la init (el server temporal), antes de estar listo.
for _ in $(seq 60); do
    docker exec "$NAME" pg_isready -q -h 127.0.0.1 -U "$user" -d "$db" && break
    sleep 1
done
docker exec "$NAME" pg_isready -q -h 127.0.0.1 -U "$user" -d "$db" || { echo "el PostgreSQL desechable no arrancó" >&2; exit 1; }
lap "postgres desechable listo"

zcat "$dump" | docker exec -i "$NAME" psql -q -v ON_ERROR_STOP=1 -U "$user" -d "$db" >/dev/null
from_rev="$(docker exec "$NAME" psql -tA -U "$user" -d "$db" -c 'SELECT version_num FROM alembic_version')"
lap "dump restaurado"

# Guardia: alembic tiene que apuntar al desechable y no a la base del .env.
target="$(DB_DSN="$dsn" .venv/bin/python -c 'from app.config import settings; print(settings.db_dsn)')"
[[ "$target" == *"@127.0.0.1:$PORT/$db" ]] || { echo "DB_DSN no apunta al desechable: no corro alembic" >&2; exit 1; }
if ! out="$(DB_DSN="$dsn" .venv/bin/alembic upgrade head 2>&1)"; then
    echo "alembic upgrade head falló:" >&2; tail -20 <<<"$out" >&2; exit 1
fi
to_rev="$(docker exec "$NAME" psql -tA -U "$user" -d "$db" -c 'SELECT version_num FROM alembic_version')"
lap "alembic upgrade head"

echo "migración: $from_rev -> $to_rev"
for t in clients agents phone_numbers wa_accounts; do
    printf '  %-14s %s\n' "$t" "$(docker exec "$NAME" psql -tA -U "$user" -d "$db" -c "SELECT count(*) FROM $t")"
done
lap "conteos"
echo "restauración ok"
