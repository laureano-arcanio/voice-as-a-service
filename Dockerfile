FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first so this layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Non-root user. Defaults to 1000:1000 (matches most single-user Linux dev machines).
# Override with --build-arg UID=$(id -u) --build-arg GID=$(id -g) if those differ,
# to avoid storage/ bind-mount permission errors.
ARG UID=1000
ARG GID=1000
RUN groupadd -g "${GID}" appuser \
    && useradd -u "${UID}" -g "${GID}" -m -s /usr/sbin/nologin appuser

COPY app/ ./app/
COPY static/ ./static/
COPY templates/ ./templates/
# Catalogo de voces del TTS con sus metricas (app/voices.py).
COPY tts/finetune/voces.tsv ./tts/finetune/voces.tsv

# Pre-create storage dirs and own them so the mkdir() app/config.py runs at import
# time doesn't fail against a fresh bind mount.
RUN mkdir -p /app/storage/recordings && chown -R appuser:appuser /app

USER appuser

EXPOSE 8011

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8011/health', timeout=2)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]
