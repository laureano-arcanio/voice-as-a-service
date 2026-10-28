#!/usr/bin/env bash
# Instala lo que el monitoreo necesita en el host (requiere sudo; make monitoring-host-install):
# smartmontools (SMART de los discos), lm-sensors (sensores de la placa, que node-exporter lee de
# /sys/class/hwmon) y el colector atentina-hostmon (systemd). No reinicia nada del stack.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
apt-get install -y smartmontools lm-sensors
sensors-detect --auto >/dev/null || true   # carga los módulos de los sensores de la placa
install -d -m 755 /var/lib/atentina-hostmon
sed -e "s|@REPO@|$REPO|g" "$REPO/deploy/systemd/atentina-hostmon.service" > /etc/systemd/system/atentina-hostmon.service
systemctl daemon-reload
systemctl enable --now atentina-hostmon.service
systemctl restart atentina-hostmon.service
sleep 8
f=/var/lib/atentina-hostmon/atentina.prom
[[ -s $f ]] || { echo "atentina-hostmon no escribió $f: journalctl -u atentina-hostmon"; exit 1; }
echo "atentina-hostmon escribe $f ($(grep -vc '^#' "$f") muestras):"
grep -E '^atentina_(gpu_count|disk_smart_ok|sip_registered)' "$f" || true
