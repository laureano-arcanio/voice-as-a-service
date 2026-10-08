#!/usr/bin/env bash
# Backend de desarrollo contra SQLite (scratch/dev.db, no versionada), sin tocar el stack. Puerto 8111.
# Lo usa `npm run dev` de web/ (proxy de /api a :8111 por defecto). Credenciales solo de desarrollo.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p scratch
export DB_DSN=sqlite:///scratch/dev.db AUTH_SECRET=dev-secret-dev-secret-dev-secret AUTH_COOKIE_SECURE=false
export ADMIN_EMAIL=admin@oime.com.ar ADMIN_PASSWORD=admin12345 ANURA_DID=1152630861
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli seed
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8111}" "$@"
