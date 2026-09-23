#!/usr/bin/env bash
# Instala y configura el NVIDIA Container Toolkit para que Docker pueda pasar
# las GPUs a los contenedores (necesario para vllm-llm/stt-parakeet/vllm-tts en
# docker-compose.yml). Pensado para Ubuntu 24.04 (noble) x86_64.
#
# Uso: sudo bash scripts/install-nvidia-toolkit.sh
set -euo pipefail

echo "==> Agregando el repo de NVIDIA Container Toolkit..."
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

echo "==> Instalando..."
apt-get update
apt-get install -y nvidia-container-toolkit

echo "==> Configurando el runtime de Docker..."
nvidia-ctk runtime configure --runtime=docker

echo "==> Reiniciando Docker..."
systemctl restart docker

echo "==> Listo. Verificando acceso a GPU desde un contenedor..."
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
