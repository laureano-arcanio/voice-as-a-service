#!/usr/bin/env bash
# Sandbox de codigo aislado para pruebas (make tools-runner-test): las imagenes de tools-runner y del proxy,
# en una red propia, sin tocar el compose. El proxy de prueba deja pasar solo al host (mock-api.test ->
# host-gateway), donde corre la API falsa (scripts/tools/mock_api.py) del e2e; el resto de las IPs
# privadas siguen denegadas. Imprime TOOLS_RUNNER_TEST_URL. Bajarlo: make tools-runner-test-down.
set -euo pipefail
cd "$(dirname "$0")/../.."
NET=atentina-tools-test
TOKEN=${TOOLS_RUNNER_TEST_TOKEN:-tok}
if [ "${1:-}" = "down" ]; then
  docker rm -f atentina-tools-test-runner atentina-tools-test-egress >/dev/null 2>&1 || true
  docker network rm $NET >/dev/null 2>&1 || true
  echo "sandbox de prueba bajado"; exit 0
fi
docker build -q -t atentina-tools-runner:test tools-runner >/dev/null
docker build -q -t atentina-tools-egress:test tools-runner/egress >/dev/null
docker network inspect $NET >/dev/null 2>&1 || docker network create --internal $NET >/dev/null
GW=$(docker network inspect bridge -f '{{(index .IPAM.Config 0).Gateway}}')
docker rm -f atentina-tools-test-runner atentina-tools-test-egress >/dev/null 2>&1 || true
docker run -d --name atentina-tools-test-egress --network bridge --add-host mock-api.test:host-gateway \
  --read-only --cap-drop ALL atentina-tools-egress:test \
  smokescreen --listen-ip=0.0.0.0 --listen-port=4750 --allow-range="$GW/32" >/dev/null
docker network connect $NET atentina-tools-test-egress
docker run -d --name atentina-tools-test-runner --network $NET --read-only --tmpfs /tmp:size=128m \
  --cap-drop ALL --security-opt no-new-privileges --memory 1g --pids-limit 256 \
  -e TOOLS_RUNNER_TOKEN="$TOKEN" -e TOOLS_EGRESS_PROXY=http://atentina-tools-test-egress:4750 \
  atentina-tools-runner:test >/dev/null
IP=$(docker inspect -f "{{(index .NetworkSettings.Networks \"$NET\").IPAddress}}" atentina-tools-test-runner)
for _ in $(seq 40); do curl -sf "http://$IP:8080/health" >/dev/null && break; sleep 0.25; done
echo "TOOLS_RUNNER_TEST_URL=http://$IP:8080"
echo "TOOLS_RUNNER_TEST_TOKEN=$TOKEN"
