#!/usr/bin/env bash
# Topes de las RTX 3090 (docs/PRODUCCION.md, AGENTS.md "Límites de la 3090"). Sin tope, dos 3090
# apagaron el server por un pico de consumo (25-sep-2026). nvidia-smi no los guarda: los aplica la
# unidad atentina-gpu-limits.service en cada arranque, antes de Docker. Requiere root.
set -euo pipefail

POWER_W="${GPU_POWER_W:-280}"
CORE_MHZ="${GPU_CORE_MHZ:-210,1800}"
MEM_MHZ="${GPU_MEM_MHZ:-405,9501}"

nvidia-smi -pm 1 >/dev/null
nvidia-smi --query-gpu=index,name --format=csv,noheader | while IFS=, read -r idx name; do
    idx="${idx// /}"
    if [[ "$name" == *3090* ]]; then
        nvidia-smi -i "$idx" -pl "$POWER_W" >/dev/null
        nvidia-smi -i "$idx" -lgc "$CORE_MHZ" >/dev/null
        nvidia-smi -i "$idx" -lmc "$MEM_MHZ" >/dev/null
        echo "GPU $idx ($name): ${POWER_W} W, núcleo ${CORE_MHZ} MHz, memoria ${MEM_MHZ} MHz"
    else
        echo "GPU $idx ($name): sin tope (solo las 3090 lo llevan)"
    fi
done
