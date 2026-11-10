#!/usr/bin/env bash
# Crea .env.dev desde .env.dev.example: del .env solo toma la clave y los nombres de los modelos, el resto se genera.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -e .env.dev ]; then echo ".env.dev ya existe"; exit 0; fi
de_env() { sed -n "s/^$1=//p" .env | tail -1; }
host=$(hostname -I | cut -d' ' -f1)
umask 077
awk -v host="$host" -v key="$(de_env VLLM_API_KEY)" -v stt="$(de_env VLLM_STT_MODEL)" -v tts="$(de_env VLLM_TTS_MODEL)" \
    -v voz="$(de_env VLLM_TTS_VOICE)" -v fernet="$(openssl rand -base64 32 | tr '+/' '-_')" '
  /__RANDOM__/ { cmd = "openssl rand -hex 24"; cmd | getline r; close(cmd); gsub(/__RANDOM__/, r) }
  { gsub(/__DEV_HOST__/, host); gsub(/__VLLM_API_KEY__/, key); gsub(/__VLLM_STT_MODEL__/, stt);
    gsub(/__VLLM_TTS_MODEL__/, tts); gsub(/__VLLM_TTS_VOICE__/, voz); gsub(/__WA_TOKEN_KEY__/, fernet); print }
' .env.dev.example > .env.dev
echo ".env.dev creado (host $host)"
