# Imagen de stt/server.py. BACKEND (parakeet | moonshine) elige base y
# requirements (ver servicios stt-* en docker-compose.yml):
#   parakeet  -> BASE=vllm/vllm-openai:latest: ya trae torch+CUDA, transformers
#                (con AutoModelForTDT) y fastapi/uvicorn, y comparte capas con
#                la imagen de vllm-llm que ya esta en disco. Con una base
#                propia (python-slim + torch cu12x) la imagen pesaba 11.6GB
#                nuevos y lleno el disco del host.
#   moonshine -> BASE=python:3.12-slim-bookworm: solo CPU, liviana (~400MB).
ARG BASE=python:3.12-slim-bookworm
FROM ${BASE}

ARG BACKEND

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY requirements-${BACKEND}.txt ./
RUN pip install -r requirements-${BACKEND}.txt

COPY server.py .

EXPOSE 8000

# La base de vLLM trae ENTRYPOINT ["vllm", "serve"].
ENTRYPOINT []
CMD ["python3", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
