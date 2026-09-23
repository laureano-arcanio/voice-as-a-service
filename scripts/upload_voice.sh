#!/usr/bin/env bash
# Sube una voz clonada al TTS (POST /v1/audio/voices), idempotente: si ya
# existe con ese nombre la borra y la vuelve a subir.
#
# La voz queda guardada en el volumen de speakers del servicio y se usa
# despues por nombre (VLLM_TTS_VOICE en .env), sin mandar ref_audio en cada
# sintesis. Sirve igual para vllm-tts (Qwen3-TTS, :8103) y tts-cosyvoice
# (CosyVoice3, :8107) -- ver README, "Voz clonada".
#
# Uso:
#   scripts/upload_voice.sh <nombre> <audio.wav> [url]
# Ej. la voz vigente del agente (CosyVoice3):
#   scripts/upload_voice.sh f08886 scripts/stt_corpus/data/entities/_voices/f08886.wav
#
# El ref_text (transcripcion exacta del audio, necesaria para ICL) se lee del
# .txt hermano del wav.
set -euo pipefail

name=${1:?uso: upload_voice.sh <nombre> <audio.wav> [url]}
audio=${2:?uso: upload_voice.sh <nombre> <audio.wav> [url]}
url=${3:-http://127.0.0.1:8107}

key=$(sed -n 's/^VLLM_API_KEY=//p' .env | tail -1)
ref_text=$(cat "${audio%.wav}.txt")

curl -sf -X DELETE "$url/v1/audio/voices/$name" -H "Authorization: Bearer $key" >/dev/null || true
curl -sf -X POST "$url/v1/audio/voices" \
  -H "Authorization: Bearer $key" \
  -F "audio_sample=@$audio;type=audio/wav" \
  -F "name=$name" \
  -F "consent=OpenSLR 61 (es_ar, CC BY-SA 4.0) -- corpus de eval, hablante $name" \
  -F "ref_text=$ref_text" \
  -F "speaker_description=Voz femenina adulta con acento argentino, calida y profesional"
echo
curl -sf "$url/v1/audio/voices" -H "Authorization: Bearer $key"
echo
