# App de fichas Registros: imagen propia, sin código ni secretos de la plataforma.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

ARG UID=1000
ARG GID=1000
RUN groupadd -g "${GID}" appuser \
    && useradd -u "${UID}" -g "${GID}" -m -s /usr/sbin/nologin appuser

COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY registros/ ./registros/

USER appuser

EXPOSE 8040

# Sin log de accesos: la URL de /c/<token> no queda en los logs y el healthcheck no los llena.
CMD ["uvicorn", "registros.main:app", "--host", "0.0.0.0", "--port", "8040", "--no-server-header", "--no-access-log"]
