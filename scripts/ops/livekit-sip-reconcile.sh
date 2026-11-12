#!/usr/bin/env bash
# Repone los trunks SIP y la dispatch rule si el Redis de LiveKit (sin persistencia) los perdió
# (cron cada 5 min, docs/INFRA.md). Si están, solo lee y no escribe nada en el log; escribe solo
# cuando crea algo o falla. Con LiveKit Cloud o en la réplica, livekit-sip-si-local no hace nada.
set -uo pipefail
cd "$(dirname "$0")/../.."

grep -qE '^STACK_ROLE=replica' .env && exit 0
STATE_DIR="${OPS_STATE_DIR:-$HOME/atentina-ops}"
mkdir -p "$STATE_DIR"
# Una corrida a la vez (un arranque lento no se pisa con la siguiente).
exec 9>"$STATE_DIR/livekit-sip.lock"
flock -n 9 || exit 0

out="$(make --no-print-directory -s livekit-sip-si-local SIP_ARGS=--if-missing 2>&1)"
rc=$?
if (( rc != 0 )) || grep -q '(creado)' <<<"$out"; then
    echo "[livekit-sip $(date '+%F %T')] rc=$rc"
    echo "$out"
fi
exit "$rc"
