"""Operación de Registros sin Docker real: compose, boot.sh, backup.sh, backup-fetch.sh y healthcheck.sh,
copiados a un directorio temporal, con docker, make, curl y gpg falsos en el PATH.
Rol, permisos y restauración reales: make registros-ops-test."""
import gzip
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
FAKE_DUMP = "-- volcado de prueba " + "x" * 200

# Docker falso: registra cada llamada y responde según lo que pide la prueba por el entorno.
FAKE_DOCKER = f"""#!/bin/bash
echo "docker $*" >> "$FAKE_LOG"
case "$*" in
  *"--profile registros up"*) exit "${{FAKE_REGISTROS_UP_RC:-0}}" ;;
  *"config --services"*) echo app ;;
  "inspect "*) echo running ;;
  *pg_dump*'"$1"'*)
    name="${{@: -1}}"
    [[ " $FAKE_MISSING_DBS " == *" $name "* ]] && {{ echo "no existe $name" >&2; exit 1; }}
    [[ " $FAKE_EMPTY_DBS " == *" $name "* ]] && exit 0
    echo "{FAKE_DUMP} $name" ;;
  *pg_dump*-d\\ crm*) echo "{FAKE_DUMP} crm" ;;
  *pg_dump*) echo "{FAKE_DUMP} principal" ;;
  *"datname = "*) [[ -n "${{FAKE_CRM:-}}" ]] && echo 1 ;;
esac
exit 0
"""
FAKE_MAKE = '#!/bin/bash\necho "make $*" >> "$FAKE_LOG"\n'
# Devuelve el código de cada URL como lo espera healthcheck.sh; el de Registros, por el entorno.
FAKE_CURL = """#!/bin/bash
echo "curl $*" >> "$FAKE_LOG"
case "$*" in
  *registros*) printf '%s' "$FAKE_REGISTROS_CODE" ;;
  *wa.atentina*) printf 403 ;;
  *) printf 200 ;;
esac
"""
# gpg falso: "descifra" y "cifra" copiando; la huella es fija.
FAKE_GPG = """#!/bin/bash
echo "gpg $*" >> "$FAKE_LOG"
out=""; input=""
while (($#)); do
  case "$1" in
    -o) out="$2"; shift ;;
    -d) input="$2"; shift ;;
    --with-colons) echo "fpr:::::::::ABC123:"; exit 0 ;;
  esac
  shift
done
[[ -n "$out" ]] && { [[ -n "$input" ]] && cp "$input" "$out" || : > "$out"; }
exit 0
"""


class Sandbox:
    def __init__(self, base: Path):
        self.root = base / "repo"
        self.home = base / "home"
        self.bin = base / "bin"
        self.state = base / "state"
        self.backups = base / "backups"
        self.log = base / "calls.log"
        for folder in (self.root, self.home, self.bin, self.state):
            folder.mkdir()
        self.log.touch()
        for name, body in {
            "docker": FAKE_DOCKER,
            "make": FAKE_MAKE,
            "curl": FAKE_CURL,
            "gpg": FAKE_GPG,
            "nvidia-smi": "#!/bin/bash\n",
        }.items():
            path = self.bin / name
            path.write_text(body)
            path.chmod(path.stat().st_mode | stat.S_IEXEC)

    def copy(self, *relative: str) -> None:
        for rel in relative:
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, target)

    def env_file(self, **values: str) -> None:
        (self.root / ".env").write_text("".join(f"{k}={v}\n" for k, v in values.items()))

    def run(self, script: str, *args: str, **env: str) -> subprocess.CompletedProcess:
        full_env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "HOME": str(self.home),
            "FAKE_LOG": str(self.log),
            "OPS_STATE_DIR": str(self.state),
            "BACKUP_DIR": str(self.backups),
            **env,
        }
        return subprocess.run(
            ["bash", str(self.root / script), *args], env=full_env, capture_output=True, text=True, timeout=60
        )

    def calls(self, prefix: str = "") -> list[str]:
        return [line for line in self.log.read_text().splitlines() if line.startswith(prefix)]


@pytest.fixture
def sandbox(tmp_path):
    return Sandbox(tmp_path)


# --- Compose ---


def _compose_services() -> dict:
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text())["services"]


def test_registros_tiene_perfil_y_nadie_depende_de_el():
    services = _compose_services()
    assert services["registros"]["profiles"] == ["registros"]
    for name, service in services.items():
        depends = service.get("depends_on") or {}
        assert "registros" not in depends, name


def test_registros_no_recibe_secretos_de_la_plataforma():
    service = _compose_services()["registros"]
    assert "env_file" not in service
    assert all(key.startswith("REGISTROS_") for key in service["environment"])
    assert service["ports"] == ["127.0.0.1:8040:8040"]
    assert service["build"] == "./apps/registros"


def test_env_example_sin_compose_profiles_y_con_las_claves():
    text = (ROOT / ".env.example").read_text()
    assert "COMPOSE_PROFILES" not in text
    documented = {line.lstrip("#").split("=")[0] for line in text.splitlines() if "=" in line}
    assert set(_compose_services()["registros"]["environment"]) - {"REGISTROS_DB_DSN"} <= documented
    assert {"REGISTROS_DB_PASSWORD", "REGISTROS_HEALTH_URL", "BACKUP_EXTRA_DBS"} <= documented


# --- boot.sh ---


def _boot_env(sandbox: Sandbox, **values: str) -> None:
    sandbox.copy("deploy/boot.sh")
    sandbox.env_file(DATA_DISK="", VLLM_TTS_VOICE="multi41", VLLM_TTS_MODEL="modelo", CLOUDFLARE_TUNNEL_TOKEN="t", **values)


def test_boot_con_registros_que_falla_llega_a_listo(sandbox):
    _boot_env(sandbox, REGISTROS_HEALTH_URL="http://127.0.0.1:8040/health")
    result = sandbox.run("deploy/boot.sh", FAKE_REGISTROS_UP_RC="1")
    assert result.returncode == 0, result.stderr
    assert "AVISO: Registros no arrancó" in result.stdout
    assert result.stdout.strip().endswith("listo")
    docker = sandbox.calls("docker")
    assert any("docker-compose.tunnel.yml up -d tunnel" in line for line in docker)
    assert any("livekit-sip-si-local" in line for line in sandbox.calls("make"))
    # Último paso, sin --wait.
    up = [line for line in docker if "--profile registros" in line]
    assert up == ["docker compose --profile registros up -d --no-deps registros"]
    assert docker[-1] == up[0]


def test_boot_sin_la_clave_no_intenta_registros(sandbox):
    _boot_env(sandbox)
    result = sandbox.run("deploy/boot.sh")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("listo")
    assert not [line for line in sandbox.calls("docker") if "registros" in line]


# --- backup.sh ---

BASE_COMMANDS = [
    """docker compose exec -T db sh -c pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner""",
    """docker compose exec -T db sh -c psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select 1 from pg_database where datname = 'crm'\"""",
]
CRM_COMMAND = """docker compose exec -T db sh -c pg_dump -U "$POSTGRES_USER" -d crm --no-owner"""


def _backup_env(sandbox: Sandbox, **values: str) -> None:
    sandbox.copy("scripts/ops/backup.sh", "scripts/ops/lib.sh")
    (sandbox.root / "storage").mkdir()
    sandbox.env_file(DATA_DISK="", **values)


def _dumps(sandbox: Sandbox) -> list[str]:
    return sorted(p.name.rsplit("-", 2)[0] for p in (sandbox.backups / "db").glob("*.sql.gz"))


def test_backup_sin_la_variable_hace_lo_de_siempre(sandbox):
    _backup_env(sandbox)
    result = sandbox.run("scripts/ops/backup.sh")
    assert result.returncode == 0, result.stderr
    assert sandbox.calls("docker") == BASE_COMMANDS
    assert _dumps(sandbox) == ["db"]
    assert (sandbox.state / "backup.ok").exists()


def test_backup_con_crm_y_sin_la_variable(sandbox):
    _backup_env(sandbox)
    result = sandbox.run("scripts/ops/backup.sh", FAKE_CRM="1")
    assert result.returncode == 0, result.stderr
    assert sandbox.calls("docker") == [*BASE_COMMANDS, CRM_COMMAND]
    assert _dumps(sandbox) == ["crm", "db"]


@pytest.mark.parametrize("value", ["registros", "registros,otra", "registros otra"])
def test_backup_con_la_variable_vuelca_cada_base_en_db(sandbox, value):
    _backup_env(sandbox, BACKUP_EXTRA_DBS=value)
    result = sandbox.run("scripts/ops/backup.sh")
    assert result.returncode == 0, result.stderr
    names = value.replace(",", " ").split()
    assert _dumps(sandbox) == sorted(["db", *names])
    dump = next((sandbox.backups / "db").glob("registros-*.sql.gz"))
    assert gzip.decompress(dump.read_bytes()).decode().strip().endswith(" registros")
    assert (sandbox.state / "backup.ok").exists()


def test_backup_con_base_inexistente_falla_sin_backup_ok(sandbox):
    _backup_env(sandbox, BACKUP_EXTRA_DBS="registros")
    result = sandbox.run("scripts/ops/backup.sh", FAKE_MISSING_DBS="registros")
    assert result.returncode != 0
    assert not (sandbox.state / "backup.ok").exists()


def test_backup_con_base_vacia_falla_sin_backup_ok(sandbox):
    _backup_env(sandbox, BACKUP_EXTRA_DBS="registros")
    result = sandbox.run("scripts/ops/backup.sh", FAKE_EMPTY_DBS="registros")
    assert result.returncode != 0
    assert "registros" in result.stderr
    assert not (sandbox.state / "backup.ok").exists()


@pytest.mark.parametrize("name", ["db", "con;punto"])
def test_backup_rechaza_un_nombre_invalido(sandbox, name):
    _backup_env(sandbox, BACKUP_EXTRA_DBS=name)
    result = sandbox.run("scripts/ops/backup.sh")
    assert result.returncode != 0
    assert "BACKUP_EXTRA_DBS" in result.stderr
    assert not (sandbox.state / "backup.ok").exists()


@pytest.mark.parametrize(("extra", "subidos"), [("", False), ("registros", True)])
def test_backup_sube_la_base_extra_cifrada_a_s3(sandbox, extra, subidos):
    _backup_env(sandbox, BACKUP_S3_BUCKET="bucket", BACKUP_EXTRA_DBS=extra)
    key = sandbox.root / "deploy" / "backup-key.asc"
    key.parent.mkdir()
    key.write_text("llave")
    result = sandbox.run("scripts/ops/backup.sh")
    assert result.returncode == 0, result.stderr
    assert any("registros.sql.gz.gpg" in line for line in sandbox.calls("gpg")) is subidos
    assert any("s3 cp" in line for line in sandbox.calls("docker"))


# --- backup-fetch.sh ---


@pytest.mark.parametrize(("name", "muestra"), [("registros.sql.gz.gpg", True), ("db.sql.gz.gpg", False)])
def test_backup_fetch_imprime_la_restauracion_solo_si_esta_el_archivo(sandbox, tmp_path, name, muestra):
    sandbox.copy("scripts/ops/backup-fetch.sh", "scripts/ops/lib.sh")
    sandbox.env_file(BACKUP_S3_BUCKET="bucket")
    folder = tmp_path / "restore"
    folder.mkdir()
    (folder / name).write_text("cifrado")
    result = sandbox.run("scripts/ops/backup-fetch.sh", "20260101-0000", str(folder))
    assert result.returncode == 0, result.stderr
    assert (f"make registros-restore DUMP={folder}/registros.sql.gz" in result.stdout) is muestra


# --- healthcheck.sh ---


def _health_env(sandbox: Sandbox, **values: str) -> None:
    sandbox.copy("scripts/ops/healthcheck.sh")
    sandbox.env_file(DATA_DISK="", GPU_SIN_TOPE="1", **values)
    (sandbox.state / "backup.ok").touch()


def test_healthcheck_sin_la_clave_no_chequea_registros(sandbox):
    _health_env(sandbox)
    result = sandbox.run("scripts/ops/healthcheck.sh", FAKE_REGISTROS_CODE="503")
    assert result.returncode == 0, result.stderr
    assert (sandbox.state / "health.state").read_text().strip() == "ok"
    assert not [line for line in sandbox.calls("curl") if "registros" in line]


def test_healthcheck_con_la_clave_y_503_da_falla(sandbox):
    _health_env(sandbox, REGISTROS_HEALTH_URL="https://registros.atentina.com.ar/health")
    result = sandbox.run("scripts/ops/healthcheck.sh", FAKE_REGISTROS_CODE="503")
    assert result.returncode != 0
    assert (sandbox.state / "health.state").read_text().strip() == "falla"
    assert "Registros sin /health" in (sandbox.state / "health.log").read_text()


def test_healthcheck_con_la_clave_y_200_da_ok(sandbox):
    _health_env(sandbox, REGISTROS_HEALTH_URL="https://registros.atentina.com.ar/health")
    result = sandbox.run("scripts/ops/healthcheck.sh", FAKE_REGISTROS_CODE="200")
    assert result.returncode == 0, result.stderr
    assert (sandbox.state / "health.state").read_text().strip() == "ok"
