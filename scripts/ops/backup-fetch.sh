#!/usr/bin/env bash
# Baja de Cloudflare R2 un backup de backup.sh y lo descifra, para restaurar en este host u otro
# (docs/MIGRACION_SERVER.md, 4). Necesita en .env las BACKUP_R2_* y, para descifrar, la llave
# PRIVADA importada en el gpg del usuario (gpg --import), que no vive en el server: borrarla después.
# Uso: backup-fetch.sh [STAMP|latest] [DIR]   (default latest y scratch/restore/<STAMP>)
#      TTS=1 baja también el checkpoint a TTS_FT_CKPT; AUDIOS=1 los audios a RECORDINGS_DIR.
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/ops/lib.sh
umask 077
shopt -s nullglob

[[ -n "$(env_get BACKUP_R2_BUCKET)" ]] || { echo "falta BACKUP_R2_BUCKET en .env" >&2; exit 1; }
base="$(r2_base)"
mkdir -p scratch/restore
stamp="${1:-latest}"
if [[ "$stamp" == latest ]]; then
    r2 "$PWD/scratch/restore" s3 cp --quiet "$base/latest" latest
    stamp="$(cat scratch/restore/latest)"
fi
dir="${2:-scratch/restore/$stamp}"
mkdir -p -m 700 "$dir"
dir="$(cd "$dir" && pwd)"

echo "bajando $base/daily/$stamp/ a $dir"
r2 "$dir" s3 cp --quiet --recursive "$base/daily/$stamp/" .
for f in "$dir"/*.gpg; do
    gpg --batch --yes --quiet -o "${f%.gpg}" -d "$f" && rm -f "$f"
done
ls -l "$dir"

if [[ "${TTS:-}" == 1 ]]; then
    ckpt="$(env_get TTS_FT_CKPT)"
    [[ -n "$ckpt" ]] || { echo "falta TTS_FT_CKPT en .env" >&2; exit 1; }
    mkdir -p "$ckpt"
    echo "bajando el checkpoint a $ckpt"
    r2 "$(cd "$ckpt" && pwd)" s3 sync --quiet "$base/tts/${ckpt#*runs/}/" .
    sha256sum "$ckpt/model.safetensors"
fi

if [[ "${AUDIOS:-}" == 1 ]]; then
    rec="$(env_get RECORDINGS_DIR)"; rec="${rec:-$PWD/storage/recordings}"
    mkdir -p "$rec"
    echo "bajando los audios a $rec"
    r2 "$rec" s3 sync --quiet "$base/audios/" .
fi

cat <<EOF
Listo. Restaurar (docs/MIGRACION_SERVER.md, 4):
  base:        zcat $dir/db.sql.gz | docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "\$POSTGRES_USER" -d "\$POSTGRES_DB"'
  crm:         make crm-db && zcat $dir/crm.sql.gz | docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "\$POSTGRES_USER" -d crm'
  .env:        diff enmascarado contra $dir/env antes de copiarlo
  storage/:    tar -xzf $dir/storage.tar.gz
  certificado: sudo tar -xzf $dir/letsencrypt.tar.gz -C asterisk
  agentes:     $dir/agents.json (consulta; la base ya los trae)
EOF
if [[ -f "$dir/speakers.tar.gz" ]]; then
    echo "  voces TTS:   docker run --rm -v voice-as-a-service_vllm_tts_speakers_ft:/dst -v $dir:/src:ro alpine:3.24 \\"
    echo "                 tar xzf /src/speakers.tar.gz -C /dst"
fi
# Conecta como el rol registros, que queda dueño; registros-db vuelve a poner el REVOKE, que no viaja en
# el dump. Si crm se restaura después, otro make registros-db.
if [[ -f "$dir/registros.sql.gz" ]]; then
    echo "  registros:   make registros-restore DUMP=$dir/registros.sql.gz"
fi
