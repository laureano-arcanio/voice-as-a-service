#!/usr/bin/env bash
# Publicación del servidor MCP en el registro oficial (registry.modelcontextprotocol.io), con el namespace
# del dominio (ar.com.atentina/*) verificado por DNS. docs/features/MCP.md (fase 4).
#   key:     genera la llave Ed25519 en secrets/ (una vez) e imprime el registro TXT para Cloudflare.
#   publish: baja mcp-publisher a scratch/, se autentica por DNS y publica deploy/mcp/server.json.
set -euo pipefail
cd "$(dirname "$0")/../.."
KEY=secrets/mcp-registry-key.pem
DOMAIN=atentina.com.ar

pubkey() { openssl pkey -in "$KEY" -pubout -outform DER | tail -c 32 | base64; }

case "${1:-}" in
  key)
    if [ ! -f "$KEY" ]; then
      openssl genpkey -algorithm Ed25519 -out "$KEY"
      chmod 600 "$KEY"
    fi
    echo "Registro TXT en Cloudflare (DNS de $DOMAIN, nombre @):"
    echo "  v=MCPv1; k=ed25519; p=$(pubkey)"
    ;;
  publish)
    [ -f "$KEY" ] || { echo "Falta $KEY: correr primero make mcp-registry-key" >&2; exit 1; }
    bin=scratch/mcp-publisher/mcp-publisher
    if [ ! -x "$bin" ]; then
      mkdir -p scratch/mcp-publisher
      os=$(uname -s | tr '[:upper:]' '[:lower:]')
      arch=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
      curl -fsSL "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_${os}_${arch}.tar.gz" \
        | tar xz -C scratch/mcp-publisher mcp-publisher
    fi
    # La semilla Ed25519 son los últimos 32 bytes del PKCS#8, en hexa.
    priv=$(openssl pkey -in "$KEY" -outform DER | tail -c 32 | xxd -p -c 64)
    "$bin" login dns --domain "$DOMAIN" --private-key "$priv"
    (cd deploy/mcp && "../../$bin" publish)
    ;;
  *)
    echo "uso: $0 key|publish" >&2; exit 2 ;;
esac
