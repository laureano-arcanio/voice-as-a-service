#!/usr/bin/env bash
# Backend de desarrollo aislado para las capturas del video tutorial-agente-free-mobile (puerto 8113, SQLite
# propia). Sin LiveKit, Resend ni WhatsApp: no despacha nada al stack en vivo. Las claves de Turnstile y la
# URL de LiveKit son de mentira: solo habilitan la pagina del link para llamar (nunca se llama).
set -euo pipefail
cd /home/laureano/voice-as-a-service
export DB_DSN=sqlite:///scratch/videos/tafm/dev.db AUTH_SECRET=dev-secret-dev-secret-dev-secret AUTH_COOKIE_SECURE=false
export ADMIN_EMAIL=admin@oime.com.ar ADMIN_PASSWORD=admin12345 ANURA_DID=1152630861
export LIVEKIT_URL= LIVEKIT_API_KEY= LIVEKIT_API_SECRET= RESEND_API_KEY= WA_ACCESS_TOKEN= BACKUP_S3_BUCKET=
export DEMO_LIVEKIT_URL=wss://rtc.invalid TURNSTILE_SITE_KEY=dev-site-key TURNSTILE_SECRET_KEY=dev-secret-key
export CALL_LINK_BASE_URL=https://llamar.atentina.com.ar
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli seed
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8113
