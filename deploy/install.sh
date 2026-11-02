#!/usr/bin/env bash
# Instala las unidades de systemd (requiere sudo) y aplica los topes de GPU ya.
# Uso: sudo deploy/install.sh   (no reinicia el stack: atentina-stack corre en el próximo arranque)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OWNER="$(stat -c %U "$REPO")"
# GPU_SIN_TOPE=1 en .env: el host no lleva tope de GPU (docs/INFRA.md); solo se instala el arranque.
units="atentina-gpu-limits atentina-stack"
grep -qE '^GPU_SIN_TOPE=1' "$REPO/.env" && units="atentina-stack"
for unit in $units; do
    sed -e "s|@REPO@|$REPO|g" -e "s|@USER@|$OWNER|g" "$REPO/deploy/systemd/$unit.service" \
        > "/etc/systemd/system/$unit.service"
done
# Sin tope, atentina-stack no puede exigir una unidad que no existe: el stack no arrancaría.
if [[ "$units" != *gpu-limits* ]]; then
    sed -i -E 's/ ?atentina-gpu-limits\.service//' /etc/systemd/system/atentina-stack.service
fi
systemctl daemon-reload
for unit in $units; do systemctl enable "$unit.service"; done
[[ "$units" == *gpu-limits* ]] && systemctl start atentina-gpu-limits.service
nvidia-smi --query-gpu=index,name,power.limit --format=csv,noheader
echo "Instalado. atentina-stack corre en el próximo arranque (no se reinició nada ahora)."
