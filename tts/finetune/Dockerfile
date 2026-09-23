# Entorno de fine-tuning de Qwen3-TTS (ver docs/TTS_FINETUNE.md).
# Base: imagen de mozi1924/Qwen3-TTS-EasyFinetuning (torch 2.5.1+cu124, qwen-tts 0.1.1,
# qwen-asr 0.0.6, flash-attn 2.8.3), fijada por digest: solo se usa como entorno, el
# codigo de entrenamiento es el de esta carpeta. num2words: normaliza numeros en el WER.
FROM ghcr.io/mozi1924/qwen3-tts-easyfinetuning@sha256:d4e86b4441123ff978685890c39e177fa3aeb5f2636b6b8a4024e54de48e5e74
RUN pip install --no-cache-dir num2words==0.5.14
ENV PYTHONUNBUFFERED=1 NUMBA_CACHE_DIR=/tmp/numba HF_HOME=/hf HF_HUB_OFFLINE=1
WORKDIR /work
ENTRYPOINT []
