# Imagen de stt/server.py (Parakeet, servicio stt-parakeet en docker-compose.yml).
# Base vllm/vllm-openai: ya trae torch+CUDA, transformers (con AutoModelForTDT)
# y fastapi/uvicorn, y comparte capas con la imagen de vllm-llm que ya esta en
# disco. Con una base propia (python-slim + torch cu12x) la imagen pesaba
# 11.6GB nuevos y lleno el disco del host.
# Fijada por digest (8-oct-2026): la misma vllm-openai que vllm-llm (docker-compose.yml).
FROM vllm/vllm-openai:latest@sha256:c2914767605584b6d8f45686b82de173ecc99e781897aa3d0a66dacd72c51ae1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# requirements.lock: versiones exactas (constraints) de lo que instala esta capa.
COPY requirements.txt requirements.lock ./
RUN pip install -r requirements.txt -c requirements.lock

COPY server.py .

EXPOSE 8000

# La base trae ENTRYPOINT ["vllm", "serve"].
ENTRYPOINT []
CMD ["python3", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
