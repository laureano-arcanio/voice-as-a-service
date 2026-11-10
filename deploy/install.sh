#!/usr/bin/env bash
# Instala la unidad de systemd del stack (requiere sudo).
# Uso: sudo deploy/install.sh   (no reinicia el stack: atentina-stack corre en el próximo arranque)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OWNER="$(stat -c %U "$REPO")"
unit=atentina-stack
sed -e "s|@REPO@|$REPO|g" -e "s|@USER@|$OWNER|g" "$REPO/deploy/systemd/$unit.service" \
    > "/etc/systemd/system/$unit.service"
systemctl daemon-reload
systemctl enable "$unit.service"
nvidia-smi --query-gpu=index,name,power.limit --format=csv,noheader
echo "Instalado. atentina-stack corre en el próximo arranque (no se reinició nada ahora)."
