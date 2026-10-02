#!/usr/bin/env bash
# Instala las unidades de systemd (requiere sudo) y aplica los topes de GPU ya.
# Uso: sudo deploy/install.sh   (no reinicia el stack: atentina-stack corre en el próximo arranque)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OWNER="$(stat -c %U "$REPO")"
for unit in atentina-gpu-limits atentina-stack; do
    sed -e "s|@REPO@|$REPO|g" -e "s|@USER@|$OWNER|g" "$REPO/deploy/systemd/$unit.service" \
        > "/etc/systemd/system/$unit.service"
done
systemctl daemon-reload
systemctl enable atentina-gpu-limits.service atentina-stack.service
systemctl start atentina-gpu-limits.service
nvidia-smi --query-gpu=index,name,power.limit --format=csv,noheader
echo "Instalado. atentina-stack corre en el próximo arranque (no se reinició nada ahora)."
