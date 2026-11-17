#!/usr/bin/env bash
# Alta, una vez, del bucket de backups en Cloudflare R2 (docs/INFRA.md). Verifica (o crea, si el
# token es de administración) el bucket, configura el lifecycle de daily/ a BACKUP_KEEP_DAYS (30) días
# y guarda las BACKUP_R2_* en .env (copia previa en scratch/). Las claves son de un token R2 con
# "Object Read & Write" acotado a ese bucket (por defecto, para los backups diarios).
# Uso: r2-setup.sh <cuenta> <bucket> [access_key_id] [secret]
#      Sin las claves usa BACKUP_R2_ACCESS_KEY_ID/SECRET ya presentes en .env (reaplicar lifecycle).
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/ops/lib.sh

account="${1:?uso: r2-setup.sh <cuenta> <bucket> [access_key_id] [secret]}"
bucket="${2:?uso: r2-setup.sh <cuenta> <bucket> [access_key_id] [secret]}"
key="${3:-$(env_get BACKUP_R2_ACCESS_KEY_ID)}"
secret="${4:-$(env_get BACKUP_R2_SECRET_ACCESS_KEY)}"
[[ -n "$key" && -n "$secret" ]] || { echo "faltan las claves: pasalas como argumentos o en .env" >&2; exit 1; }
endpoint="${BACKUP_R2_ENDPOINT:-$(env_get BACKUP_R2_ENDPOINT)}"
endpoint="${endpoint:-https://$account.r2.cloudflarestorage.com}"
keep="${BACKUP_KEEP_DAYS:-30}"
mkdir -p scratch
work="$(mktemp -d "$PWD/scratch/r2-setup-XXXX")"; trap 'rm -rf "$work"' EXIT

r2_admin() {
    docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
        -e AWS_ACCESS_KEY_ID="$key" -e AWS_SECRET_ACCESS_KEY="$secret" -e AWS_DEFAULT_REGION=auto \
        -v "$work":/w -w /w "$AWS_CLI_IMAGE" --endpoint-url "$endpoint" "$@"
}

echo "endpoint: $endpoint"
if r2_admin s3api head-bucket --bucket "$bucket" 2>/dev/null; then
    echo "el bucket $bucket ya existe"
elif r2_admin s3api create-bucket --bucket "$bucket" --create-bucket-configuration LocationConstraint=auto >/dev/null 2>&1; then
    echo "bucket $bucket creado"
else
    echo "AVISO: no se pudo ver ni crear el bucket $bucket con ese token." >&2
    echo "Si ya existe, el token es de objetos y no de administración: seguimos; verificá el nombre." >&2
    echo "Si no existe, creálo en Cloudflare > R2 antes de usar el backup." >&2
fi

cat > "$work/lifecycle.json" <<EOF
{"Rules": [
  {"ID": "daily", "Status": "Enabled", "Filter": {"Prefix": "daily/"},
   "Expiration": {"Days": $keep}},
  {"ID": "multipart", "Status": "Enabled", "Filter": {},
   "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 2}}
]}
EOF
if r2_admin s3api put-bucket-lifecycle-configuration --bucket "$bucket" \
        --lifecycle-configuration file://lifecycle.json; then
    echo "lifecycle: daily/ se borra a los $keep días"
else
    echo "AVISO: el token no pudo configurar el lifecycle." >&2
    echo "Configuralo en Cloudflare > R2 > $bucket > Settings > Object lifecycle: daily/ a $keep días." >&2
fi

if [[ -n "$(env_get BACKUP_R2_BUCKET)" ]]; then
    echo "BACKUP_R2_* ya está en .env: no se reescribe"
else
    cp .env "scratch/env.antes-r2-$(date +%Y%m%d-%H%M)"
    {
        echo "BACKUP_R2_ACCOUNT_ID=$account"
        echo "BACKUP_R2_BUCKET=$bucket"
        echo "BACKUP_R2_ACCESS_KEY_ID=$key"
        echo "BACKUP_R2_SECRET_ACCESS_KEY=$secret"
    } >> .env
    echo "BACKUP_R2_* agregadas a .env (copia previa en scratch/)"
fi
echo "listo: probar con make backup y make backup-list"
