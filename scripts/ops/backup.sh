#!/usr/bin/env bash
# Backup (cron, docs/INFRA.md): base (pg_dump), crm y las bases de BACKUP_EXTRA_DBS, .env, storage/,
# secrets/ (credenciales de Google y clave del registro MCP), certificado SIP, agentes en JSON,
# embeddings del TTS y checkpoint del TTS servido. Local en
# BACKUP_DIR (.env o entorno; default ~/atentina-backups): otro disco que el de Docker. Copia externa
# a Cloudflare R2 si BACKUP_R2_BUCKET está en .env: la base, .env, agentes, storage/, secrets/ y certificado se
# cifran con la llave pública de deploy/backup-key.asc (la privada no está en el server); los audios
# (RECORDINGS_DIR, sin line-spool/) y el checkpoint se sincronizan incrementales y sin cifrar.
# Restaurar: scripts/ops/backup-fetch.sh (docs/MIGRACION_SERVER.md, 4).
# BACKUP_EXTRA_DBS en .env: otras bases del mismo db, con el mismo trato (coma o espacio entre nombres).
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/ops/lib.sh

OK_FILE="$STATE_DIR/backup.ok"
# Compatibilidad con el cron viejo (make cron-install lo reemplaza por 00:00 y 12:00): el --if-due
# horario no repite un backup de las últimas 11 h.
if [[ "${1:-}" == --if-due && -n "$(find "$OK_FILE" -mmin -660 2>/dev/null)" ]]; then exit 0; fi
mkdir -p "$STATE_DIR"
exec 9>"$STATE_DIR/backup.lock"
flock -n 9 || { echo "otro backup en curso" >&2; exit 0; }

DEST="${BACKUP_DIR:-$(env_get BACKUP_DIR)}"; DEST="${DEST:-$HOME/atentina-backups}"
# DATA_DISK en .env: el disco de datos tiene que estar montado, si no el backup caería en el disco de la base.
disk="$(env_get DATA_DISK)"
[[ -z "$disk" ]] || mountpoint -q "$disk" || { echo "disco de datos $disk sin montar: no se hace el backup" >&2; exit 1; }
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"
STAMP="$(date +%Y%m%d-%H%M)"
umask 077
mkdir -p "$DEST/db" "$DEST/env" "$DEST/storage" "$DEST/secrets" "$DEST/letsencrypt" "$DEST/tts" "$DEST/speakers" "$STATE_DIR"

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

# Bases extra. Una listada que no existe corta acá, sin backup.ok: healthcheck.sh avisa.
extra_dbs=()
extra_names="$(env_get BACKUP_EXTRA_DBS)"
for name in ${extra_names//,/ }; do
    # "db" pisaría el volcado de la base principal.
    [[ "$name" =~ ^[A-Za-z0-9_]+$ && "$name" != db ]] || { echo "BACKUP_EXTRA_DBS: nombre inválido ($name)" >&2; exit 1; }
    extra_file="$DEST/db/$name-$STAMP.sql.gz"
    docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$1" --no-owner' sh "$name" | gzip > "$extra_file"
    [[ $(zcat "$extra_file" | head -c 1000 | wc -c) -gt 100 ]] || { echo "backup de la base $name vacío" >&2; exit 1; }
    extra_dbs+=("$name")
done

# .env: tiene los secretos (WA_TOKEN_KEY: sin ella no se leen los tokens de los clientes).
env_file="$DEST/env/env-$STAMP"
cp "${OPS_ENV_FILE:-.env}" "$env_file"

# Agentes versionados en JSON, legibles sin restaurar la base (la base ya los trae completos).
agents_file="$DEST/env/agents-$STAMP.json"
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA' > "$agents_file" <<'SQL' || rm -f "$agents_file"
select coalesce(jsonb_agg(to_jsonb(a) order by a.client_id, a.slug), '[]'::jsonb) from agents a;
SQL
[[ -s "$agents_file" ]] || { rm -f "$agents_file"; echo "AVISO: no se pudo exportar los agentes en JSON" >&2; }

# storage/: aperturas pregeneradas, imágenes de los links para llamar y logos de la marca blanca.
storage_file="$DEST/storage/storage-$STAMP.tar.gz"
tar -czf "$storage_file" --warning=no-file-changed storage || [[ $? -eq 1 ]]

# secrets/: credenciales de Google Analytics del CRM y clave privada del registro MCP (no versionados).
secrets_file=""
if [[ -d secrets ]]; then
    secrets_file="$DEST/secrets/secrets-$STAMP.tar.gz"
    tar -czf "$secrets_file" --warning=no-file-changed secrets || [[ $? -eq 1 ]]
fi

# Certificado SIP de WhatsApp (de root: se lee desde un contenedor). Se regenera con make sip-cert.
le_file=""
if [[ -d asterisk/letsencrypt ]]; then
    le_file="$DEST/letsencrypt/letsencrypt-$STAMP.tar.gz"
    docker run --rm -v "$PWD/asterisk/letsencrypt":/letsencrypt:ro alpine:3.24 \
        tar czf - -C / letsencrypt > "$le_file"
fi

# Embeddings de voces del TTS (volumen vllm_tts_speakers_ft). Sin la base suele estar vacío: se copia si tiene algo.
speakers_file=""
speakers_vol="$(docker volume ls -q --filter name='_vllm_tts_speakers_ft' 2>/dev/null | head -1 || true)"
if [[ -n "$speakers_vol" && -n "$(docker run --rm -v "$speakers_vol":/src:ro alpine:3.24 sh -c 'ls -A /src' 2>/dev/null)" ]]; then
    speakers_file="$DEST/speakers/speakers-$STAMP.tar.gz"
    docker run --rm -v "$speakers_vol":/src:ro alpine:3.24 tar czf - -C /src . > "$speakers_file"
fi

# Checkpoint del TTS servido (no versionado; perderlo es reentrenar las voces). Con la ruta desde
# runs/ (multi41/lr2e-6/checkpoint-epoch-2), la misma que espera TTS_FT_CKPT. Solo copia lo que cambió.
ckpt="$(env_get TTS_FT_CKPT)"; ckpt_rel=""
if [[ -n "$ckpt" && -d "$ckpt" ]]; then
    ckpt_rel="${ckpt#*runs/}"
    mkdir -p "$DEST/tts/$ckpt_rel"
    rsync -a --delete "$ckpt/" "$DEST/tts/$ckpt_rel/"
fi

find "$DEST/db" "$DEST/env" "$DEST/storage" "$DEST/secrets" "$DEST/letsencrypt" "$DEST/speakers" -type f -mtime +"$KEEP_DAYS" -delete

remote="local"; audios_remote="no"
if [[ -n "$(env_get BACKUP_R2_BUCKET)" ]]; then
    [[ -f "$BACKUP_KEY_FILE" ]] || { echo "falta $BACKUP_KEY_FILE (make backup-key): no se sube sin cifrar" >&2; exit 1; }
    fpr="$(backup_key_fpr)"
    [[ -n "$fpr" ]] || { echo "no se pudo leer la llave de $BACKUP_KEY_FILE" >&2; exit 1; }
    base="$(r2_base)"
    tmp="$(mktemp -d "$DEST/.subida-XXXX")"; trap 'rm -rf "$tmp"' EXIT
    enc() { backup_gpg --trust-model always -e -r "$fpr" -o "$tmp/$2" "$1"; }
    enc "$db_file" db.sql.gz.gpg
    [[ -n "$crm_file" ]] && enc "$crm_file" crm.sql.gz.gpg
    for name in "${extra_dbs[@]}"; do enc "$DEST/db/$name-$STAMP.sql.gz" "$name.sql.gz.gpg"; done
    enc "$env_file" env.gpg
    [[ -n "$agents_file" ]] && enc "$agents_file" agents.json.gpg
    enc "$storage_file" storage.tar.gz.gpg
    [[ -n "$secrets_file" ]] && enc "$secrets_file" secrets.tar.gz.gpg
    [[ -n "$le_file" ]] && enc "$le_file" letsencrypt.tar.gz.gpg
    [[ -n "$speakers_file" ]] && enc "$speakers_file" speakers.tar.gz.gpg
    snapshot_files=("$db_file" "$env_file" "$storage_file")
    [[ -n "$secrets_file" ]] && snapshot_files+=("$secrets_file")
    [[ -n "$crm_file" ]] && snapshot_files+=("$crm_file")
    for name in "${extra_dbs[@]}"; do snapshot_files+=("$DEST/db/$name-$STAMP.sql.gz"); done
    [[ -n "$agents_file" ]] && snapshot_files+=("$agents_file")
    [[ -n "$le_file" ]] && snapshot_files+=("$le_file")
    [[ -n "$speakers_file" ]] && snapshot_files+=("$speakers_file")
    {
        echo "stamp=$STAMP"
        echo "created=$(date -Iseconds)"
        for f in "${snapshot_files[@]}"; do
            echo "sha256=$(sha256sum "$f" | cut -d' ' -f1) size=$(stat -c%s "$f") file=$(basename "$f")"
        done
    } > "$tmp/manifest.txt"
    echo "$STAMP" > "$tmp/latest"

    # Instantánea cifrada: base, .env, agentes, storage/, secrets/, certificado y embeddings.
    r2 "$tmp" s3 cp --quiet --recursive --exclude latest . "$base/daily/$STAMP/"

    # Audios (grabaciones, Estudio, contenido de la API) y checkpoint: espejo incremental, sin cifrar.
    rec_dir="$(env_get RECORDINGS_DIR)"; rec_dir="${rec_dir:-$PWD/storage/recordings}"
    if [[ -d "$rec_dir" ]]; then
        r2 "$rec_dir" s3 sync --quiet --exclude 'line-spool/*' . "$base/audios/"
        audios_remote="$base/audios"
    else
        echo "AVISO: no existe $rec_dir: no se copiaron audios" >&2
    fi
    [[ -n "$ckpt_rel" ]] && r2 "$DEST/tts" s3 sync --quiet "$ckpt_rel" "$base/tts/$ckpt_rel/"

    r2 "$tmp" s3 cp --quiet latest "$base/latest"   # último backup completo: lo usa backup-fetch.sh
    remote="$base/daily/$STAMP"
fi
touch "$OK_FILE"
echo "$(date '+%F %T') backup ok: $(du -h "$db_file" | cut -f1) base, $(du -sh "$DEST" | cut -f1) local ($DEST); externo: $remote; audios: $audios_remote"
