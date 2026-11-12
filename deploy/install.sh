#!/usr/bin/env bash
# Instala la unidad de systemd del stack y, en el server principal, el cron del usuario (requiere sudo).
# Uso: sudo deploy/install.sh [--sin-cron]   (no reinicia el stack: atentina-stack corre en el próximo arranque)
# --sin-cron: server nuevo antes del corte (docs/MIGRACION_SERVER.md, 8.2).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OWNER="$(stat -c %U "$REPO")"
unit=atentina-stack
sed -e "s|@REPO@|$REPO|g" -e "s|@USER@|$OWNER|g" "$REPO/deploy/systemd/$unit.service" \
    > "/etc/systemd/system/$unit.service"
systemctl daemon-reload
systemctl enable "$unit.service"
# Cron del usuario (backup, chequeo, trunks SIP): solo en el server principal, no en la réplica.
if [[ "${1:-}" != --sin-cron ]] && ! grep -qE '^STACK_ROLE=replica' "$REPO/.env"; then
    sudo -u "$OWNER" -H make --no-print-directory -C "$REPO" cron-install
fi
nvidia-smi --query-gpu=index,name,power.limit --format=csv,noheader
echo "Instalado. atentina-stack corre en el próximo arranque (no se reinició nada ahora)."
