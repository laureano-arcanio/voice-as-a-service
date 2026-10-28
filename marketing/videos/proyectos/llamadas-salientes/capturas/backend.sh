#!/usr/bin/env bash
# Backend de desarrollo aislado para las capturas del video llamadas-salientes (puerto 8115, SQLite propia).
# Sin LiveKit, Resend ni WhatsApp: no despacha nada al stack en vivo.
set -euo pipefail
cd /home/laureano/voice-as-a-service
mkdir -p scratch/videos/llamadas-salientes/dev
export DB_DSN=sqlite:///scratch/videos/llamadas-salientes/dev/dev.db AUTH_SECRET=dev-secret-dev-secret-dev-secret AUTH_COOKIE_SECURE=false
export ADMIN_EMAIL=admin@oime.com.ar ADMIN_PASSWORD=admin12345 ANURA_DID=1152630861
export LIVEKIT_URL= LIVEKIT_API_KEY= LIVEKIT_API_SECRET= RESEND_API_KEY= WA_ACCESS_TOKEN= BACKUP_S3_BUCKET=
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli seed
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8115
