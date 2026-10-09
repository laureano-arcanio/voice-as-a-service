# Bases fijadas por digest (8-oct-2026, las del build vigente de app; docker buildx history
# inspect). Para subirlas: build con el tag, probar y anotar el digest nuevo.
# --- UI: build de la SPA (web/) ---
FROM node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402 AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# --- App (API + UI) y worker de voz: la misma imagen ---
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias primero (capa cacheada). requirements.lock fija las versiones exactas
# (constraints): sin el, cada build resolvia lo ultimo dentro de los rangos y app y agent
# podian quedar con versiones distintas. Un rango que no admite la del lock hace fallar el build.
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock

# Non-root user. Defaults to 1000:1000 (matches most single-user Linux dev machines).
# Override with --build-arg UID=$(id -u) --build-arg GID=$(id -g) if those differ,
# to avoid storage/ bind-mount permission errors.
ARG UID=1000
ARG GID=1000
RUN groupadd -g "${GID}" appuser \
    && useradd -u "${UID}" -g "${GID}" -m -s /usr/sbin/nologin appuser

COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY app/ ./app/
# Catalogo de voces del TTS con sus metricas (app/services/voices.py).
COPY tts/finetune/voces.tsv ./tts/finetune/voces.tsv
COPY --from=web /web/dist ./web/dist

RUN mkdir -p /app/storage/recordings && chown -R appuser:appuser /app

USER appuser

EXPOSE 8011

# /health/ready: 503 (unhealthy) si la base no responde; healthcheck.sh avisa por unhealthy.
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8011/health/ready', timeout=4)" || exit 1

# Sin header `server: uvicorn`. La IP real y el esquema detras del tunel los resuelve la app
# (app/api/deps.py: CF-Connecting-IP y X-Forwarded-Proto solo desde TRUSTED_PROXY_CIDRS).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011", "--proxy-headers", "--no-server-header"]
