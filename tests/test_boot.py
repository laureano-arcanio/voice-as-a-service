"""deploy/boot.sh sin Docker real: si la espera del compose falla, los trunks SIP corren igual y sale con 1."""
from tests.test_registros_ops import Sandbox

# Docker falso: los primeros FAKE_UP_FAILS `up --wait` fallan; vllm-tts con la salud de FAKE_TTS_HEALTH.
FAKE_DOCKER = """#!/bin/bash
echo "docker $*" >> "$FAKE_LOG"
case "$*" in
  *tunnel*) exit 0 ;;
  "compose up -d --wait"*)
    n=$(grep -c 'up -d --wait' "$FAKE_LOG")
    (( n > ${FAKE_UP_FAILS:-0} )) || { echo "dependency failed to start" >&2; exit 1; } ;;
  *"config --services"*) printf 'livekit\\nvllm-tts\\n' ;;
  *"ps -q vllm-tts"*) echo abc ;;
  "inspect "*) echo "${FAKE_TTS_HEALTH:-healthy}" ;;
esac
exit 0
"""
# make falso: los primeros FAKE_SIP_FAILS intentos de trunks fallan.
FAKE_MAKE = """#!/bin/bash
echo "make $*" >> "$FAKE_LOG"
n=$(grep -c '^make' "$FAKE_LOG")
(( n > ${FAKE_SIP_FAILS:-0} ))
"""


def _sandbox(tmp_path) -> Sandbox:
    box = Sandbox(tmp_path)
    for name, body in {"docker": FAKE_DOCKER, "make": FAKE_MAKE, "sleep": "#!/bin/bash\n"}.items():
        (box.bin / name).write_text(body)
        (box.bin / name).chmod(0o755)
    box.copy("deploy/boot.sh")
    box.env_file(DATA_DISK="", VLLM_TTS_VOICE="multi41", VLLM_TTS_MODEL="modelo", CLOUDFLARE_TUNNEL_TOKEN="t")
    return box


def test_primer_up_falla_segundo_anda_todo_sigue(tmp_path):
    box = _sandbox(tmp_path)
    result = box.run("deploy/boot.sh", FAKE_UP_FAILS="1")
    assert result.returncode == 0, result.stdout
    ups = [c for c in box.calls("docker") if "up -d --wait" in c]
    assert ups == ["docker compose up -d --wait --wait-timeout 900", "docker compose up -d --wait --wait-timeout 300"]
    assert box.calls("make") == ["make --no-print-directory livekit-sip-si-local"]
    assert any(c.startswith("curl") and "multi41" in c for c in box.calls("curl"))
    assert result.stdout.strip().endswith("listo")


def test_compose_falla_trunks_igual_y_sale_con_1(tmp_path):
    box = _sandbox(tmp_path)
    result = box.run("deploy/boot.sh", FAKE_UP_FAILS="9", FAKE_SIP_FAILS="2", FAKE_TTS_HEALTH="unhealthy")
    assert result.returncode == 1
    assert len(box.calls("make")) == 3  # dos fallas y el tercero anda
    assert not box.calls("curl")  # sin vllm-tts healthy no se calienta
    assert "el stack no quedó healthy" in result.stdout
    assert "TTS sin calentar" in result.stdout
    assert "trunks SIP sin crear" not in result.stdout


def test_trunks_que_nunca_andan_salen_con_1(tmp_path):
    box = _sandbox(tmp_path)
    result = box.run("deploy/boot.sh", FAKE_SIP_FAILS="9")
    assert result.returncode == 1
    assert len(box.calls("make")) == 4
    assert "trunks SIP sin crear" in result.stdout
    assert box.calls("curl")  # el TTS se calienta igual


# --- scripts/ops/livekit-sip-reconcile.sh (cron cada 5 min) ---


def _reconcile(tmp_path, env_role: str = "") -> Sandbox:
    box = Sandbox(tmp_path)
    (box.bin / "make").write_text('#!/bin/bash\necho "make $*" >> "$FAKE_LOG"\necho "$FAKE_OUT"\nexit "${FAKE_RC:-0}"\n')
    box.copy("scripts/ops/livekit-sip-reconcile.sh")
    box.env_file(STACK_ROLE=env_role)
    return box


def test_reconcile_sin_cambios_no_escribe_nada(tmp_path):
    box = _reconcile(tmp_path)
    result = box.run("scripts/ops/livekit-sip-reconcile.sh", FAKE_OUT="")
    assert result.returncode == 0 and result.stdout == ""
    assert box.calls("make") == ["make --no-print-directory -s livekit-sip-si-local SIP_ARGS=--if-missing"]


def test_reconcile_loguea_si_crea_o_falla(tmp_path):
    box = _reconcile(tmp_path)
    created = box.run("scripts/ops/livekit-sip-reconcile.sh", FAKE_OUT="Dispatch rule SDR_1 (creado)")
    assert created.returncode == 0 and "(creado)" in created.stdout
    failed = box.run("scripts/ops/livekit-sip-reconcile.sh", FAKE_OUT="LiveKit no responde", FAKE_RC="2")
    assert failed.returncode == 2 and "rc=2" in failed.stdout


def test_reconcile_no_corre_en_la_replica(tmp_path):
    box = _reconcile(tmp_path, env_role="replica")
    result = box.run("scripts/ops/livekit-sip-reconcile.sh")
    assert result.returncode == 0 and not box.calls("make")
