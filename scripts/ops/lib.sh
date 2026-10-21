# Funciones comunes de scripts/ops/ (se cargan con `source`; el script ya hizo cd a la raíz del repo).

env_get() { grep -E "^$1=" "${OPS_ENV_FILE:-.env}" | tail -1 | cut -d= -f2- || true; }

STATE_DIR="${OPS_STATE_DIR:-$HOME/atentina-ops}"
AWS_CLI_IMAGE="amazon/aws-cli:2.27.0"
BACKUP_KEY_FILE="${BACKUP_KEY_FILE:-deploy/backup-key.asc}"   # llave pública (versionada); la privada no está en el server

# aws-cli en contenedor (sin instalar nada en el host), con las credenciales de backup del .env.
# Monta el directorio de trabajo en /w: las rutas locales que se le pasen van relativas a /w.
# Uso: s3 <dir local montado> s3 cp ...
s3() {
    local dir="$1"; shift
    local endpoint; endpoint="$(env_get BACKUP_S3_ENDPOINT)"
    docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
        -e AWS_ACCESS_KEY_ID="$(env_get BACKUP_S3_ACCESS_KEY_ID)" \
        -e AWS_SECRET_ACCESS_KEY="$(env_get BACKUP_S3_SECRET_ACCESS_KEY)" \
        -e AWS_DEFAULT_REGION="$(env_get BACKUP_S3_REGION | grep . || echo sa-east-1)" \
        -v "$dir":/w -w /w "$AWS_CLI_IMAGE" ${endpoint:+--endpoint-url "$endpoint"} "$@"
}

s3_base() {
    local bucket prefix
    bucket="$(env_get BACKUP_S3_BUCKET)"; prefix="$(env_get BACKUP_S3_PREFIX)"
    echo "s3://$bucket${prefix:+/$prefix}"
}

# gpg con un keyring propio, para no depender del del usuario. Importa la llave pública del repo.
backup_gpg() { gpg --homedir "$STATE_DIR/gnupg" --batch --yes --quiet "$@"; }
backup_key_fpr() {
    mkdir -p -m 700 "$STATE_DIR/gnupg"
    backup_gpg --import "$BACKUP_KEY_FILE" 2>/dev/null
    backup_gpg --with-colons --import-options show-only --import "$BACKUP_KEY_FILE" 2>/dev/null \
        | awk -F: '/^fpr/ {print $10; exit}'
}
