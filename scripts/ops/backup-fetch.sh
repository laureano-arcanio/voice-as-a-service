#!/usr/bin/env bash
# Baja de S3 un backup de backup.sh y lo descifra, para restaurar en este host u otro
# (docs/MIGRACION_SERVER.md, 4). Necesita en .env las BACKUP_S3_* y, para descifrar, la llave
# PRIVADA importada en el gpg del usuario (gpg --import), que no vive en el server: borrarla después.
# Uso: backup-fetch.sh [STAMP|latest] [DIR]   (default latest y scratch/restore/<STAMP>)
#      TTS=1 baja también el checkpoint del TTS a la ruta de TTS_FT_CKPT.
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/ops/lib.sh
umask 077

[[ -n "$(env_get BACKUP_S3_BUCKET)" ]] || { echo "falta BACKUP_S3_BUCKET en .env" >&2; exit 1; }
base="$(s3_base)"
mkdir -p scratch/restore
stamp="${1:-latest}"
if [[ "$stamp" == latest ]]; then
    s3 "$PWD/scratch/restore" s3 cp --quiet "$base/latest" latest
    stamp="$(cat scratch/restore/latest)"
fi
dir="${2:-scratch/restore/$stamp}"
mkdir -p -m 700 "$dir"
dir="$(cd "$dir" && pwd)"

echo "bajando $base/daily/$stamp/ a $dir"
s3 "$dir" s3 cp --quiet --recursive "$base/daily/$stamp/" .
for f in "$dir"/*.gpg; do
    gpg --batch --yes --quiet -o "${f%.gpg}" -d "$f" && rm -f "$f"
done
ls -l "$dir"

if [[ "${TTS:-}" == 1 ]]; then
    ckpt="$(env_get TTS_FT_CKPT)"
    [[ -n "$ckpt" ]] || { echo "falta TTS_FT_CKPT en .env" >&2; exit 1; }
    mkdir -p "$ckpt"
    echo "bajando el checkpoint a $ckpt"
    s3 "$(cd "$ckpt" && pwd)" s3 sync --quiet "$base/tts/${ckpt#*runs/}/" .
    sha256sum "$ckpt/model.safetensors"
fi
cat <<EOF
Listo. Restaurar (docs/MIGRACION_SERVER.md, 4):
  base:        zcat $dir/db.sql.gz | docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "\$POSTGRES_USER" -d "\$POSTGRES_DB"'
  .env:        diff enmascarado contra $dir/env antes de copiarlo
  storage/:    tar -xzf $dir/storage.tar.gz
  certificado: sudo tar -xzf $dir/letsencrypt.tar.gz -C asterisk
EOF
