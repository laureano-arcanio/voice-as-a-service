#!/usr/bin/env bash
# Backup (cron, docs/INFRA.md): base (pg_dump), .env, storage/, certificado SIP y checkpoint
# del TTS servido. Local en BACKUP_DIR (default ~/atentina-backups, en /home: otro disco que el de
# Docker). Copia externa a S3 si BACKUP_S3_BUCKET está en .env: base, .env, storage/ y certificado
# cifrados con la llave pública de deploy/backup-key.asc (la privada no está en el server), y el
# checkpoint tal cual. Restaurar: scripts/ops/backup-fetch.sh (docs/MIGRACION_SERVER.md, 4).
# --if-due: no hace nada si el último backup completo tiene menos de 25 h. El cron lo corre a las
# 03:30 y, con esa bandera, cada hora: si el host estuvo apagado a las 03:30, se recupera solo.
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/ops/lib.sh

OK_FILE="$STATE_DIR/backup.ok"
if [[ "${1:-}" == --if-due && -n "$(find "$OK_FILE" -mmin -1500 2>/dev/null)" ]]; then exit 0; fi
mkdir -p "$STATE_DIR"
exec 9>"$STATE_DIR/backup.lock"
flock -n 9 || { echo "otro backup en curso" >&2; exit 0; }

DEST="${BACKUP_DIR:-$HOME/atentina-backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"
STAMP="$(date +%Y%m%d-%H%M)"
umask 077
mkdir -p "$DEST/db" "$DEST/env" "$DEST/storage" "$DEST/letsencrypt" "$DEST/tts" "$STATE_DIR"

# Base: dump completo en SQL, comprimido. Se verifica que no esté vacío.
db_file="$DEST/db/db-$STAMP.sql.gz"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' | gzip > "$db_file"
[[ $(zcat "$db_file" | head -c 1000 | wc -c) -gt 100 ]] || { echo "backup de la base vacío" >&2; exit 1; }

# Base del CRM de ventas (docs/features/CRM.md), si existe.
crm_file=""
if docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select 1 from pg_database where datname = '"'"'crm'"'"'"' | grep -q 1; then
    crm_file="$DEST/db/crm-$STAMP.sql.gz"
    docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d crm --no-owner' | gzip > "$crm_file"
fi

# .env: tiene los secretos (WA_TOKEN_KEY: sin ella no se leen los tokens de los clientes).
env_file="$DEST/env/env-$STAMP"
cp "${OPS_ENV_FILE:-.env}" "$env_file"

# storage/: grabaciones, aperturas pregeneradas, imágenes de los links para llamar y logos de la marca blanca.
storage_file="$DEST/storage/storage-$STAMP.tar.gz"
tar -czf "$storage_file" --warning=no-file-changed storage || [[ $? -eq 1 ]]

# Certificado SIP de WhatsApp (de root: se lee desde un contenedor). Se regenera con make sip-cert.
le_file=""
if [[ -d asterisk/letsencrypt ]]; then
    le_file="$DEST/letsencrypt/letsencrypt-$STAMP.tar.gz"
    docker run --rm -v "$PWD/asterisk/letsencrypt":/letsencrypt:ro alpine:3.24 \
        tar czf - -C / letsencrypt > "$le_file"
fi

# Checkpoint del TTS servido (no versionado; perderlo es reentrenar las voces). Con la ruta desde
# runs/ (multi41/lr2e-6/checkpoint-epoch-2), la misma que espera TTS_FT_CKPT. Solo copia lo que cambió.
ckpt="$(env_get TTS_FT_CKPT)"; ckpt_rel=""
if [[ -n "$ckpt" && -d "$ckpt" ]]; then
    ckpt_rel="${ckpt#*runs/}"
    mkdir -p "$DEST/tts/$ckpt_rel"
    rsync -a --delete "$ckpt/" "$DEST/tts/$ckpt_rel/"
fi

find "$DEST/db" "$DEST/env" "$DEST/storage" "$DEST/letsencrypt" -type f -mtime +"$KEEP_DAYS" -delete

remote="local"
if [[ -n "$(env_get BACKUP_S3_BUCKET)" ]]; then
    [[ -f "$BACKUP_KEY_FILE" ]] || { echo "falta $BACKUP_KEY_FILE (make backup-key): no se sube sin cifrar" >&2; exit 1; }
    fpr="$(backup_key_fpr)"
    [[ -n "$fpr" ]] || { echo "no se pudo leer la llave de $BACKUP_KEY_FILE" >&2; exit 1; }
    tmp="$(mktemp -d "$DEST/.subida-XXXX")"; trap 'rm -rf "$tmp"' EXIT
    enc() { backup_gpg --trust-model always -e -r "$fpr" -o "$tmp/$2" "$1"; }
    enc "$db_file" db.sql.gz.gpg
    [[ -n "$crm_file" ]] && enc "$crm_file" crm.sql.gz.gpg
    enc "$env_file" env.gpg
    enc "$storage_file" storage.tar.gz.gpg
    [[ -n "$le_file" ]] && enc "$le_file" letsencrypt.tar.gz.gpg
    echo "$STAMP" > "$tmp/latest"
    base="$(s3_base)"
    s3 "$tmp" s3 cp --quiet --recursive --exclude latest . "$base/daily/$STAMP/"
    [[ -n "$ckpt_rel" ]] && s3 "$DEST/tts" s3 sync --quiet "$ckpt_rel" "$base/tts/$ckpt_rel/"
    s3 "$tmp" s3 cp --quiet latest "$base/latest"   # último backup completo: lo usa backup-fetch.sh
    remote="$base/daily/$STAMP"
fi
touch "$OK_FILE"
echo "$(date '+%F %T') backup ok: $(du -h "$db_file" | cut -f1) base, $(du -sh "$DEST" | cut -f1) local ($DEST); externo: $remote"
