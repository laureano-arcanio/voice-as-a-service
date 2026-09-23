#!/usr/bin/env bash
# Corre un comando en el entorno de fine-tuning (ver docs/TTS_FINETUNE.md).
#   GPU=0|1|none  (default 0; none = solo CPU)   NET=host para hablar con vllm-tts local
#   OPENSLR_DIR   carpeta con es_ar_female/ y es_ar_male/ (default ~/Downloads)
# Monta: este directorio en /code, work/ en /work, el HF cache del proyecto en /hf
# (offline: los modelos tienen que estar ya descargados) y OpenSLR 61 en /src.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
IMAGE=voice-tts-ft:latest
mkdir -p "$HERE/work"
docker image inspect "$IMAGE" >/dev/null 2>&1 || docker build -q -t "$IMAGE" "$HERE" >/dev/null
OPENSLR_DIR="${OPENSLR_DIR:-$HOME/Downloads}"
args=(--rm --shm-size 4g -u "$(id -u):$(id -g)" -e HOME=/work/.home -e PYTHONPATH=/code
      -v "$HERE":/code:ro -v "$HERE/work":/work -v voice-as-a-service_hf_cache:/hf -w /work)
for d in es_ar_female es_ar_male; do
  [ -d "$OPENSLR_DIR/$d" ] && args+=(-v "$OPENSLR_DIR/$d":/src/$d:ro)
done
[ "${GPU:-0}" != none ] && args+=(--gpus "device=${GPU:-0}")
[ "${NET:-}" = host ] && args+=(--network host -e VLLM_API_KEY="${VLLM_API_KEY:-not-needed}")
exec docker run "${args[@]}" "$IMAGE" bash -c "$*"
