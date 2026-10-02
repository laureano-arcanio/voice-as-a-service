#!/usr/bin/env bash
# Backup diario (cron, docs/PRODUCCION.md 3.E): base (pg_dump), .env y checkpoint del TTS servido.
# Destino: BACKUP_DIR (default ~/atentina-backups), en /home: otro disco que el de Docker (la base).
# Externo: si RCLONE_REMOTE está en .env (ej. r2:atentina-backups), sube base y .env cifrados con
# BACKUP_GPG_RECIPIENT y el checkpoint tal cual. Sin eso, solo local: no cubre robo ni incendio.
set -euo pipefail
cd "$(dirname "$0")/../.."

env_get() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- || true; }
DEST="${BACKUP_DIR:-$HOME/atentina-backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"
STAMP="$(date +%Y%m%d-%H%M)"
umask 077
mkdir -p "$DEST/db" "$DEST/env" "$DEST/tts"

# Base: dump completo en SQL, comprimido. Se verifica que no esté vacío.
db_file="$DEST/db/db-$STAMP.sql.gz"
docker exec voice-as-a-service-db-1 pg_dump -U "$(env_get POSTGRES_USER)" -d "$(env_get POSTGRES_DB)" \
    --no-owner | gzip > "$db_file"
[[ $(zcat "$db_file" | head -c 1000 | wc -c) -gt 100 ]] || { echo "backup de la base vacío" >&2; exit 1; }

# .env: tiene los secretos (WA_TOKEN_KEY: sin ella no se leen los tokens de los clientes).
cp .env "$DEST/env/env-$STAMP"

# Checkpoint del TTS servido (no versionado; perderlo es reentrenar las voces). Solo si cambió.
ckpt="$(env_get TTS_FT_CKPT)"
if [[ -n "$ckpt" && -d "$ckpt" ]]; then
    rsync -a --delete "$ckpt/" "$DEST/tts/$(basename "$(dirname "$ckpt")")-$(basename "$ckpt")/"
fi

find "$DEST/db" "$DEST/env" -type f -mtime +"$KEEP_DAYS" -delete

remote="$(env_get RCLONE_REMOTE)"
if [[ -n "$remote" ]]; then
    recipient="$(env_get BACKUP_GPG_RECIPIENT)"
    [[ -n "$recipient" ]] || { echo "RCLONE_REMOTE sin BACKUP_GPG_RECIPIENT: no se sube sin cifrar" >&2; exit 1; }
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
    gpg --batch --yes -e -r "$recipient" -o "$tmp/db-$STAMP.sql.gz.gpg" "$db_file"
    gpg --batch --yes -e -r "$recipient" -o "$tmp/env-$STAMP.gpg" "$DEST/env/env-$STAMP"
    rclone copy "$tmp" "$remote/daily/"
    rclone sync "$DEST/tts" "$remote/tts/"
fi
echo "backup ok: $(du -h "$db_file" | cut -f1) base, $(du -sh "$DEST" | cut -f1) en total ($DEST)"
