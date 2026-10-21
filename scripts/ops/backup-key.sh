#!/usr/bin/env bash
# Genera, una vez, el par de llaves GPG de los backups. La pública queda en deploy/backup-key.asc
# (versionada: cualquier server nuevo cifra con ella sin configurar nada). La privada queda en
# scratch/backup-key/ para que la guardes FUERA del server (gestor de claves) y la borres de acá:
# sin ella no se descifra ningún backup; con ella en el server, quien entre lee los backups.
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/ops/lib.sh

[[ -f "$BACKUP_KEY_FILE" ]] && { echo "$BACKUP_KEY_FILE ya existe: no se pisa" >&2; exit 1; }
out="scratch/backup-key"
mkdir -p -m 700 "$out"
home="$(mktemp -d "$PWD/$out/gnupg-XXXX")"; trap 'rm -rf "$home"' EXIT
gpg --homedir "$home" --batch --quiet --passphrase '' \
    --quick-gen-key "Atentina backups <backups@atentina.com.ar>" ed25519 cert never
fpr="$(gpg --homedir "$home" --with-colons --list-keys | awk -F: '/^fpr/ {print $10; exit}')"
gpg --homedir "$home" --batch --quiet --passphrase '' --quick-add-key "$fpr" cv25519 encr never
gpg --homedir "$home" --armor --export "$fpr" > "$BACKUP_KEY_FILE"
( umask 077; gpg --homedir "$home" --armor --export-secret-keys "$fpr" > "$out/backup-key-privada.asc" )
echo "llave $fpr"
echo "pública: $BACKUP_KEY_FILE (commitearla)"
echo "PRIVADA: $out/backup-key-privada.asc -> guardarla en el gestor de claves y borrarla: shred -u $out/backup-key-privada.asc"
