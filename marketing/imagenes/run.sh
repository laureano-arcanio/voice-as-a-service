#!/usr/bin/env bash
# Qwen-Image-2.1 en vLLM-Omni sobre la RTX 3090 (24 GB) del entorno de desarrollo.
# Lo usa el agente `videos` (marketing/VIDEOS.md) y `marketing/videos/scripts/imagen.py`.
# DiT: GGUF Q4_K_M (14,2 GB bf16 -> 4,6 GB), del repo con layout diffusers.
# Text encoder Qwen3-VL-8B: BitsAndBytes NF4 (17,5 GB bf16 -> 4,5 GB).
# VAE en bf16 (1,35 GB). Pico medido: 10,5 GB de GPU, 1024x1024/20 pasos en 25 s.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker rm -f qwen21 >/dev/null 2>&1 || true

docker run -d --name qwen21 \
  --gpus all \
  --ipc=host \
  -p 8210:8210 \
  -v /home/laureano/Models:/models:ro \
  -v "$DIR":/opt/qwen21:ro \
  -e HF_HUB_OFFLINE=1 \
  -e VLLM_LOGGING_LEVEL=INFO \
  atentina/vllm-omni-qwen21:0.32.0 \
  python /opt/qwen21/entrypoint.py serve /models/Qwen-Image-2.1 \
    --omni \
    --host 0.0.0.0 \
    --port 8210 \
    --gpu-memory-utilization 0.90 \
    --max-num-seqs 4 \
    --request-batch-max-wait-ms 50 \
    --stage-overrides '{"0":{"enable_prompt_embed_cache":true}}' \
    --diffusion-offload-config '{"mode":"module","components":["text_encoder"]}' \
    --diffusion-quantization-config '{"transformer":{"method":"gguf","gguf_model":"/models/Qwen-Image-2.1/transformer/qwen-image-2.1-Q4_K_M.gguf"},"text_encoder":{"method":"bitsandbytes","quant_type":"nf4"}}'

echo "sigue el arranque con: docker logs -f qwen21"
