# Funciones comunes de scripts/ops/ (se cargan con `source`; el script ya hizo cd a la raíz del repo).

env_get() { grep -E "^$1=" "${OPS_ENV_FILE:-.env}" | tail -1 | cut -d= -f2- || true; }

STATE_DIR="${OPS_STATE_DIR:-$HOME/atentina-ops}"
AWS_CLI_IMAGE="amazon/aws-cli:2.27.0"
BACKUP_KEY_FILE="${BACKUP_KEY_FILE:-deploy/backup-key.asc}"   # llave pública (versionada); la privada no está en el server

# Endpoint de Cloudflare R2: https://<cuenta>.r2.cloudflarestorage.com. BACKUP_R2_ENDPOINT lo pisa
# para una jurisdicción (eu/us) o para probar contra otro S3 compatible.
r2_endpoint() {
    local endpoint account
    endpoint="$(env_get BACKUP_R2_ENDPOINT)"
    if [[ -n "$endpoint" ]]; then echo "$endpoint"; return 0; fi
    account="$(env_get BACKUP_R2_ACCOUNT_ID)"
    [[ -n "$account" ]] || return 1
    echo "https://$account.r2.cloudflarestorage.com"
}

r2_base() {
    local bucket prefix
    bucket="$(env_get BACKUP_R2_BUCKET)"; prefix="$(env_get BACKUP_R2_PREFIX)"
    [[ -n "$bucket" ]] || return 1
    echo "s3://$bucket${prefix:+/$prefix}"
}

# aws-cli en contenedor (sin instalar nada en el host), con las credenciales de backup del .env.
# Monta el directorio de trabajo en /w: las rutas locales que se le pasen van relativas a /w.
# Uso: r2 <dir local montado> s3 cp ...
r2() {
    local dir="$1"; shift
    local endpoint; endpoint="$(r2_endpoint)" \
        || { echo "falta BACKUP_R2_ACCOUNT_ID (o BACKUP_R2_ENDPOINT) en .env" >&2; return 1; }
    docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
        -e AWS_ACCESS_KEY_ID="$(env_get BACKUP_R2_ACCESS_KEY_ID)" \
        -e AWS_SECRET_ACCESS_KEY="$(env_get BACKUP_R2_SECRET_ACCESS_KEY)" \
        -e AWS_DEFAULT_REGION=auto \
        -v "$dir":/w -w /w "$AWS_CLI_IMAGE" --endpoint-url "$endpoint" "$@"
}

# gpg con un keyring propio, para no depender del del usuario. Importa la llave pública del repo.
backup_gpg() { gpg --homedir "$STATE_DIR/gnupg" --batch --yes --quiet "$@"; }
backup_key_fpr() {
    mkdir -p -m 700 "$STATE_DIR/gnupg"
    backup_gpg --import "$BACKUP_KEY_FILE" 2>/dev/null
    backup_gpg --with-colons --import-options show-only --import "$BACKUP_KEY_FILE" 2>/dev/null \
        | awk -F: '/^fpr/ {print $10; exit}'
}
