#!/usr/bin/env bash
# Rol y base de Registros en el db de la plataforma (make registros-db). Idempotente: un rol o una base
# que ya existen no se tocan. Quita el CONNECT de PUBLIC en la base principal y en crm, si existe: la
# plataforma y el CRM usan POSTGRES_USER, propietario, y no les afecta. El REVOKE no viaja en un dump:
# si crm se restaura o se crea después, volver a correrlo.
# DB_EXEC: cómo se ejecuta un comando en db, con entrada estándar (registros_ops_test.sh lo cambia).
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/ops/lib.sh

DB_EXEC="${DB_EXEC:-docker compose exec -T db}"

# Va dentro de la URL de conexión del compose y por stdin a psql, sin escapar.
password="${REGISTROS_DB_PASSWORD:-$(env_get REGISTROS_DB_PASSWORD)}"
[[ "$password" =~ ^[A-Za-z0-9_-]+$ ]] \
    || { echo "REGISTROS_DB_PASSWORD falta en .env o tiene otros caracteres que letras, números, _ y - (openssl rand -hex 32)" >&2; exit 1; }

admin() { $DB_EXEC sh -c 'exec psql -X -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"' sh "$@"; }

# La clave por stdin: no queda en los argumentos de ningún proceso.
admin <<SQL
\set password '$password'
SELECT format('CREATE ROLE registros LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE', :'password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'registros') \gexec
SQL

if [[ "$(admin -tAc "select 1 from pg_database where datname = 'registros'" </dev/null)" != 1 ]]; then
    $DB_EXEC sh -c 'createdb -U "$POSTGRES_USER" -O registros registros' </dev/null
fi

admin <<'SQL'
SELECT format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', datname)
FROM pg_database WHERE datname IN (current_database(), 'crm') \gexec
SQL

echo "rol y base registros listos"
