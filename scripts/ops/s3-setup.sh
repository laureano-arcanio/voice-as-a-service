#!/usr/bin/env bash
# Crea, una vez, el bucket de backups y un usuario IAM que solo puede escribir y leer en él (no
# borrar: un server comprometido no puede borrar los backups). Corre con credenciales de admin de
# AWS (AWS_PROFILE del ~/.aws del usuario), no con las de backup. Bucket privado, cifrado SSE-S3,
# con versionado; lifecycle: daily/ se borra a los BACKUP_KEEP_DAYS (30) días y las versiones
# viejas a los 7. Guarda las BACKUP_S3_* en .env (copia previa en scratch/).
# Uso: AWS_PROFILE=<perfil admin> scripts/ops/s3-setup.sh <bucket> [región]
set -euo pipefail
cd "$(dirname "$0")/../.."
source scripts/ops/lib.sh

bucket="${1:?uso: s3-setup.sh <bucket> [región]}"
region="${2:-sa-east-1}"
keep="${BACKUP_KEEP_DAYS:-30}"
user="atentina-backup"
mkdir -p scratch
work="$(mktemp -d "$PWD/scratch/s3-setup-XXXX")"; trap 'rm -rf "$work"' EXIT

aws_admin() {
    docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e AWS_PROFILE="${AWS_PROFILE:-default}" \
        -e AWS_DEFAULT_REGION="$region" -v "$HOME/.aws":/tmp/.aws:ro -v "$work":/w -w /w "$AWS_CLI_IMAGE" "$@"
}

echo "cuenta: $(aws_admin sts get-caller-identity --query Arn --output text)"
if aws_admin s3api head-bucket --bucket "$bucket" 2>/dev/null; then
    echo "el bucket $bucket ya existe"
else
    location=(--create-bucket-configuration "LocationConstraint=$region")
    [[ "$region" == us-east-1 ]] && location=()   # us-east-1 no acepta LocationConstraint
    aws_admin s3api create-bucket --bucket "$bucket" "${location[@]}" >/dev/null
    echo "bucket $bucket creado en $region"
fi
aws_admin s3api put-public-access-block --bucket "$bucket" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws_admin s3api put-bucket-encryption --bucket "$bucket" --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws_admin s3api put-bucket-versioning --bucket "$bucket" --versioning-configuration Status=Enabled
cat > "$work/lifecycle.json" <<EOF
{"Rules": [
  {"ID": "daily", "Status": "Enabled", "Filter": {"Prefix": "daily/"},
   "Expiration": {"Days": $keep}, "NoncurrentVersionExpiration": {"NoncurrentDays": 7}},
  {"ID": "versiones", "Status": "Enabled", "Filter": {},
   "NoncurrentVersionExpiration": {"NoncurrentDays": 30},
   "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 2}}
]}
EOF
aws_admin s3api put-bucket-lifecycle-configuration --bucket "$bucket" --lifecycle-configuration file://lifecycle.json

cat > "$work/policy.json" <<EOF
{"Version": "2012-10-17", "Statement": [
  {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": "arn:aws:s3:::$bucket"},
  {"Effect": "Allow", "Action": ["s3:PutObject", "s3:GetObject"], "Resource": "arn:aws:s3:::$bucket/*"}
]}
EOF
aws_admin iam get-user --user-name "$user" >/dev/null 2>&1 || aws_admin iam create-user --user-name "$user" >/dev/null
aws_admin iam put-user-policy --user-name "$user" --policy-name "backup-$bucket" --policy-document file://policy.json

if [[ -n "$(env_get BACKUP_S3_ACCESS_KEY_ID)" ]]; then
    echo "BACKUP_S3_ACCESS_KEY_ID ya está en .env: no se crea otra key"
else
    aws_admin iam create-access-key --user-name "$user" --query 'AccessKey.[AccessKeyId,SecretAccessKey]' \
        --output text > "$work/key"
    read -r key_id key_secret < "$work/key"
    cp .env "scratch/env.antes-s3-setup-$(date +%Y%m%d-%H%M)"
    {
        echo "BACKUP_S3_BUCKET=$bucket"
        echo "BACKUP_S3_REGION=$region"
        echo "BACKUP_S3_ACCESS_KEY_ID=$key_id"
        echo "BACKUP_S3_SECRET_ACCESS_KEY=$key_secret"
    } >> .env
    echo "BACKUP_S3_* agregadas a .env (copia previa en scratch/)"
fi
echo "listo: probar con make backup"
