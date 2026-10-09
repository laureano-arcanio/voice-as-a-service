#!/usr/bin/env bash
# Backup diario (cron, docs/PRODUCCION.md 3.E): base (pg_dump), .env, storage/ (archivos de la
# app), asterisk/letsencrypt (certificado y cuenta de Let's Encrypt de las llamadas de WhatsApp) y
# checkpoint del TTS servido.
# Destino: BACKUP_DIR (default ~/atentina-backups), en /home: otro disco que el de Docker (la base).
# Externo: si RCLONE_REMOTE está en .env (ej. r2:atentina-backups), sube cifrado con
# BACKUP_GPG_RECIPIENT todo menos el checkpoint, que va tal cual. Sin eso, solo local: no cubre
# robo ni incendio, y lo anota en el log en cada corrida.
# Al terminar bien deja backup.ok (y backup-remote.ok si subió) en OPS_STATE_DIR: healthcheck.sh
# avisa si tienen más de 26 h. La restauración se prueba con scripts/ops/restore-test.sh.
set -euo pipefail
cd "$(dirname "$0")/../.."

env_get() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- || true; }
DEST="${BACKUP_DIR:-$HOME/atentina-backups}"
STATE_DIR="${OPS_STATE_DIR:-$HOME/atentina-ops}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"
STAMP="$(date +%Y%m%d-%H%M)"
umask 077
mkdir -p "$DEST/db" "$DEST/env" "$DEST/tts" "$DEST/storage" "$DEST/letsencrypt" "$STATE_DIR"

# Base: dump completo en SQL, comprimido. Se verifica que no esté vacío.
db_file="$DEST/db/db-$STAMP.sql.gz"
docker exec voice-as-a-service-db-1 pg_dump -U "$(env_get POSTGRES_USER)" -d "$(env_get POSTGRES_DB)" \
    --no-owner | gzip > "$db_file"
[[ $(zcat "$db_file" | head -c 1000 | wc -c) -gt 100 ]] || { echo "backup de la base vacío" >&2; exit 1; }

# .env: tiene los secretos (WA_TOKEN_KEY: sin ella no se leen los tokens de los clientes).
cp .env "$DEST/env/env-$STAMP"

# storage/ (grabaciones y archivos que guarda la app; 8 KB el 8-oct-2026). Un tar por día: si
# crece mucho, pasar a rsync como el checkpoint.
storage_file="$DEST/storage/storage-$STAMP.tar.gz"
tar -czf "$storage_file" storage

# asterisk/letsencrypt: es de root (lo escribe certbot en un contenedor), así que se lee con un
# contenedor desechable. Se puede volver a emitir con make sip-cert, pero así no hace falta.
le_file=""
if [[ -d asterisk/letsencrypt ]]; then
    le_file="$DEST/letsencrypt/letsencrypt-$STAMP.tar.gz"
    docker run --rm --network none -v "$PWD/asterisk/letsencrypt:/le:ro" \
        postgres:16-alpine@sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea \
        tar -czf - -C /le . > "$le_file"
fi

# Checkpoint del TTS servido (no versionado; perderlo es reentrenar las voces). Solo si cambió.
ckpt="$(env_get TTS_FT_CKPT)"
if [[ -n "$ckpt" && -d "$ckpt" ]]; then
    rsync -a --delete "$ckpt/" "$DEST/tts/$(basename "$(dirname "$ckpt")")-$(basename "$ckpt")/"
fi

find "$DEST/db" "$DEST/env" "$DEST/storage" "$DEST/letsencrypt" -type f -mtime +"$KEEP_DAYS" -delete
touch "$STATE_DIR/backup.ok"

remote="$(env_get RCLONE_REMOTE)"
if [[ -n "$remote" ]]; then
    recipient="$(env_get BACKUP_GPG_RECIPIENT)"
    [[ -n "$recipient" ]] || { echo "RCLONE_REMOTE sin BACKUP_GPG_RECIPIENT: no se sube sin cifrar" >&2; exit 1; }
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
    for f in "$db_file" "$DEST/env/env-$STAMP" "$storage_file" ${le_file:+"$le_file"}; do
        gpg --batch --yes -e -r "$recipient" -o "$tmp/$(basename "$f").gpg" "$f"
    done
    rclone copy "$tmp" "$remote/daily/"
    rclone sync "$DEST/tts" "$remote/tts/"
    touch "$STATE_DIR/backup-remote.ok"
else
    echo "AVISO $(date '+%F %T'): sin RCLONE_REMOTE en .env: el backup queda solo en este host (no cubre robo, incendio ni falla del disco)" >&2
fi
echo "backup ok $(date '+%F %T'): $(du -h "$db_file" | cut -f1) base, $(du -sh "$DEST" | cut -f1) en total ($DEST)"
