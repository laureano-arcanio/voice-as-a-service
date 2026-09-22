# Imagen de stt/server.py (Parakeet, servicio stt-parakeet en docker-compose.yml).
# Base vllm/vllm-openai: ya trae torch+CUDA, transformers (con AutoModelForTDT)
# y fastapi/uvicorn, y comparte capas con la imagen de vllm-llm que ya esta en
# disco. Con una base propia (python-slim + torch cu12x) la imagen pesaba
# 11.6GB nuevos y lleno el disco del host.
FROM vllm/vllm-openai:latest

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY server.py .

EXPOSE 8000

# La base trae ENTRYPOINT ["vllm", "serve"].
ENTRYPOINT []
CMD ["python3", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
