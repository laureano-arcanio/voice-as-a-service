#!/usr/bin/env python3
"""Colector del host para Prometheus (docs/OBSERVABILIDAD.md).

Lo que no trae node_exporter: cada GPU por NVML (uso, VRAM, potencia y tope, temperatura, relojes,
motivos de recorte, enlace PCIe, VRAM por servicio, errores XID), los contenedores de Atentina
(arriba, health, reinicios, OOM, CPU y RAM por cgroup), SMART de los discos, energía de la CPU
(RAPL), registro SIP de Asterisk e IP pública. Escribe un archivo .prom en el textfile collector de
node_exporter cada HOSTMON_INTERVAL segundos (5).

Corre como root (systemd, atentina-hostmon.service: smartctl, RAPL y el journal lo piden); sin root
saltea lo que no puede leer. Solo biblioteca estándar: corre con el python3 del host.
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = Path(os.environ.get("HOSTMON_DIR", "/var/lib/atentina-hostmon"))
INTERVAL = float(os.environ.get("HOSTMON_INTERVAL", "5"))
PROJECT = os.environ.get("COMPOSE_PROJECT_NAME") or REPO.name
SLOW_EVERY = 300  # SMART, IP pública y servicios esperados: cada 5 min
SIP_EVERY = 30
RAPL = Path("/sys/class/powercap/intel-rapl:0/energy_uj")

GPU_FIELDS = [
    "index", "name", "pci.bus_id", "utilization.gpu", "memory.used", "memory.total", "power.draw",
    "power.limit", "temperature.gpu", "fan.speed", "clocks.sm", "clocks.mem", "pcie.link.gen.current",
    "pcie.link.gen.max", "pcie.link.width.current", "pcie.link.width.max", "clocks_event_reasons.active",
]
# Bits de clocks_event_reasons (nvml.h). gpu_idle y app_clocks no son problema: no se exportan.
THROTTLE_BITS = {
    "sw_power_cap": 0x4, "hw_slowdown": 0x8, "sync_boost": 0x10, "sw_thermal": 0x20,
    "hw_thermal": 0x40, "hw_power_brake": 0x80,
}


def sh(*a, timeout=10):
    try:
        return subprocess.run(a, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        return ""


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def esc(v):
    return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


class Metrics:
    """Acumula muestras y las escribe en el formato de texto de Prometheus."""

    def __init__(self):
        self.help: dict[str, tuple[str, str]] = {}
        self.samples: list[tuple[str, dict, float]] = []

    def add(self, name, value, labels=None, help="", kind="gauge"):
        if value is None:
            return
        self.help.setdefault(name, (help, kind))
        self.samples.append((name, labels or {}, float(value)))

    def render(self) -> str:
        out = []
        for name, (h, kind) in self.help.items():
            out += [f"# HELP {name} {h}", f"# TYPE {name} {kind}"]
            for n, labels, v in self.samples:
                if n != name:
                    continue
                lab = ",".join(f'{k}="{esc(x)}"' for k, x in sorted(labels.items()))
                out.append(f"{n}{{{lab}}} {v:g}" if lab else f"{n} {v:g}")
        return "\n".join(out) + "\n"


# --- GPU ---------------------------------------------------------------------------------------

def parse_gpus(csv: str) -> list[dict]:
    """Filas de `nvidia-smi --query-gpu=<GPU_FIELDS> --format=csv,noheader,nounits`."""
    gpus = []
    for line in csv.splitlines():
        f = [x.strip() for x in line.split(",")]
        if len(f) != len(GPU_FIELDS):
            continue
        gpus.append(dict(zip(GPU_FIELDS, f)))
    return gpus


def throttle_reasons(hexval: str) -> dict[str, int]:
    try:
        v = int(hexval, 16)
    except (TypeError, ValueError):
        return {}
    return {k: int(bool(v & bit)) for k, bit in THROTTLE_BITS.items()}


def gpu_metrics(m: Metrics, gpus: list[dict]):
    m.add("atentina_gpu_count", len(gpus), help="GPUs que ve nvidia-smi")
    for g in gpus:
        lab = {"gpu": g["index"], "name": g["name"], "bus": g["pci.bus_id"].lower().removeprefix("00000000:")}
        util = num(g["utilization.gpu"])
        m.add("atentina_gpu_utilization_ratio", util / 100 if util is not None else None, lab, "Uso del núcleo")
        for key, name, h in (("memory.used", "atentina_gpu_memory_used_bytes", "VRAM usada"),
                             ("memory.total", "atentina_gpu_memory_total_bytes", "VRAM total")):
            v = num(g[key])
            m.add(name, v * 1024 * 1024 if v is not None else None, lab, h)
        m.add("atentina_gpu_power_watts", num(g["power.draw"]), lab, "Potencia")
        m.add("atentina_gpu_power_limit_watts", num(g["power.limit"]), lab, "Tope de potencia")
        m.add("atentina_gpu_temperature_celsius", num(g["temperature.gpu"]), lab, "Temperatura del núcleo")
        fan = num(g["fan.speed"])
        m.add("atentina_gpu_fan_ratio", fan / 100 if fan is not None else None, lab, "Ventilador")
        m.add("atentina_gpu_clock_sm_mhz", num(g["clocks.sm"]), lab, "Reloj del núcleo")
        m.add("atentina_gpu_clock_mem_mhz", num(g["clocks.mem"]), lab, "Reloj de la memoria")
        m.add("atentina_gpu_pcie_gen", num(g["pcie.link.gen.current"]), lab, "Generación PCIe actual")
        m.add("atentina_gpu_pcie_gen_max", num(g["pcie.link.gen.max"]), lab, "Generación PCIe máxima")
        m.add("atentina_gpu_pcie_width", num(g["pcie.link.width.current"]), lab, "Ancho PCIe actual")
        m.add("atentina_gpu_pcie_width_max", num(g["pcie.link.width.max"]), lab, "Ancho PCIe máximo")
        for reason, on in throttle_reasons(g["clocks_event_reasons.active"]).items():
            m.add("atentina_gpu_throttle", on, {**lab, "reason": reason}, "Motivo de recorte del reloj activo")


def container_of_pid(pid: int, ids: dict[str, str]) -> str:
    try:
        cg = Path(f"/proc/{pid}/cgroup").read_text()
    except OSError:
        return "?"
    mt = re.search(r"docker-([0-9a-f]{64})\.scope", cg)
    if mt and mt.group(1) in ids:
        return ids[mt.group(1)]
    return "otros"  # escritorio y otros proyectos: juntos (no se muestran aparte)


def gpu_process_metrics(m: Metrics, ids: dict[str, str], bus_to_index: dict[str, str]):
    out = sh("nvidia-smi", "--query-compute-apps=gpu_bus_id,pid,used_memory", "--format=csv,noheader,nounits")
    per: dict[tuple[str, str], float] = {}
    for line in out.splitlines():
        f = [x.strip() for x in line.split(",")]
        if len(f) != 3 or not f[1].isdigit() or num(f[2]) is None:
            continue
        gpu = bus_to_index.get(f[0].lower().removeprefix("00000000:"), "?")
        key = (gpu, container_of_pid(int(f[1]), ids))
        per[key] = per.get(key, 0) + num(f[2]) * 1024 * 1024
    for (gpu, svc), v in per.items():
        m.add("atentina_gpu_process_memory_bytes", v, {"gpu": gpu, "service": svc}, "VRAM por servicio")


XID_RE = re.compile(r"NVRM: Xid \(PCI:([0-9a-fA-F:.]+)\): (\d+)")


def parse_xid(journal: str) -> list[tuple[str, str]]:
    return [(b.lower(), x) for b, x in XID_RE.findall(journal)]


# --- Contenedores ------------------------------------------------------------------------------

def inspect_project() -> list[dict]:
    ids = sh("docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}").split()
    if not ids:
        return []
    try:
        return json.loads(sh("docker", "inspect", *ids, timeout=20))
    except ValueError:
        return []


def service_name(c: dict) -> str | None:
    lab = c.get("Config", {}).get("Labels", {})
    if lab.get("com.docker.compose.oneoff") == "True":
        return None
    return lab.get("com.docker.compose.service")


def cgroup_usage(cid: str) -> tuple[float | None, float | None]:
    """(segundos de CPU, bytes de RAM sin el cache inactivo, como docker stats)."""
    p = Path(f"/sys/fs/cgroup/system.slice/docker-{cid}.scope")
    try:
        stat = dict(line.split() for line in (p / "cpu.stat").read_text().splitlines())
        cpu = int(stat["usage_usec"]) / 1e6
    except (OSError, KeyError, ValueError):
        cpu = None
    try:
        cur = int((p / "memory.current").read_text())
        ms = dict(line.split() for line in (p / "memory.stat").read_text().splitlines())
        mem = cur - int(ms.get("inactive_file", 0))
    except (OSError, ValueError):
        mem = None
    return cpu, mem


HEALTH = {"healthy": 1, "unhealthy": 0, "starting": 0.5}


def container_metrics(m: Metrics, containers: list[dict], expected: set[str]) -> dict[str, str]:
    """Métricas por servicio; devuelve {container_id: servicio} de los que corren."""
    ids, seen = {}, set()
    for c in containers:
        svc = service_name(c)
        if not svc or svc == "migrate":  # corre una vez y termina
            continue
        st = c.get("State", {})
        running = st.get("Status") == "running"
        seen.add(svc)
        lab = {"service": svc}
        m.add("atentina_container_up", int(running), lab, "Contenedor corriendo")
        health = (st.get("Health") or {}).get("Status")
        if health:
            m.add("atentina_container_healthy", HEALTH.get(health, 0), lab,
                  "Healthcheck del contenedor (1 healthy, 0,5 starting, 0 unhealthy)")
        m.add("atentina_container_restarts", c.get("RestartCount", 0), lab, "Reinicios de Docker del contenedor")
        m.add("atentina_container_oom_killed", int(bool(st.get("OOMKilled"))), lab, "Último fin por OOM")
        started = st.get("StartedAt", "")
        try:
            ts = time.mktime(time.strptime(started[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
            m.add("atentina_container_started_timestamp_seconds", ts, lab, "Último arranque")
        except ValueError:
            pass
        if running:
            ids[c["Id"]] = svc
            cpu, mem = cgroup_usage(c["Id"])
            m.add("atentina_container_cpu_seconds_total", cpu, lab, "CPU usada", "counter")
            m.add("atentina_container_memory_bytes", mem, lab, "RAM usada (sin cache inactivo)")
    for svc in sorted(expected - seen):
        m.add("atentina_container_up", 0, {"service": svc}, "Contenedor corriendo")
    return ids


def expected_services() -> set[str]:
    """Servicios del compose vigente (COMPOSE_FILE del .env), más el túnel; sin `migrate`."""
    out = sh("docker", "compose", "--project-directory", str(REPO), "config", "--services", timeout=30)
    svcs = set(out.split()) | {"tunnel"} if out else set()
    return svcs - {"migrate"}


# --- Discos, SIP, red -------------------------------------------------------------------------

def parse_smart(data: dict) -> dict:
    nv = data.get("nvme_smart_health_information_log") or {}
    return {
        "ok": (data.get("smart_status") or {}).get("passed"),
        "wear": nv.get("percentage_used"),
        "media_errors": nv.get("media_errors"),
        "spare": nv.get("available_spare"),
        "temp": (data.get("temperature") or {}).get("current"),
    }


def smart_metrics(m: Metrics):
    for dev in sorted(Path("/dev").glob("nvme[0-9]")) + sorted(Path("/dev").glob("sd[a-z]")):
        try:
            data = json.loads(sh("smartctl", "-j", "-a", str(dev), timeout=20) or "{}")
        except ValueError:
            continue
        s = parse_smart(data)
        if s["ok"] is None and s["temp"] is None:
            continue
        lab = {"device": dev.name, "model": data.get("model_name", "")}
        m.add("atentina_disk_smart_ok", int(bool(s["ok"])) if s["ok"] is not None else None, lab, "SMART pasa")
        m.add("atentina_disk_wear_ratio", s["wear"] / 100 if s["wear"] is not None else None, lab,
              "Desgaste del NVMe (percentage_used)")
        m.add("atentina_disk_media_errors", s["media_errors"], lab, "Errores de medio")
        m.add("atentina_disk_spare_ratio", s["spare"] / 100 if s["spare"] is not None else None, lab,
              "Reserva disponible")
        m.add("atentina_disk_temperature_celsius", s["temp"], lab, "Temperatura del disco")


REG_RE = re.compile(r"^\s*(\S+?)/\S+\s+\S+\s+(Registered|Unregistered|Rejected|Stopped|Failed)\b", re.M)


def parse_registrations(text: str) -> dict[str, int]:
    """`pjsip show registrations` → {registro: 1 si Registered}."""
    return {name: int(state == "Registered") for name, state in REG_RE.findall(text)}


def env_value(key: str) -> str:
    """Valor de `key` en el .env del repo (la última línea gana, como en compose)."""
    try:
        lines = (REPO / ".env").read_text().splitlines()
    except OSError:
        return ""
    vals = [line.split("=", 1)[1].strip() for line in lines if line.startswith(f"{key}=")]
    return vals[-1] if vals else ""


def public_ip() -> str | None:
    try:
        with urllib.request.urlopen("https://1.1.1.1/cdn-cgi/trace", timeout=5) as r:
            for line in r.read().decode().splitlines():
                if line.startswith("ip="):
                    return line[3:]
    except OSError:
        return None
    return None


# --- Bucle ------------------------------------------------------------------------------------

class State:
    def __init__(self):
        self.slow_at = 0.0
        self.sip_at = 0.0
        self.slow = Metrics()
        self.sip = Metrics()
        self.expected: set[str] = set()
        self.xid_total: dict[tuple[str, str], int] = {}
        self.xid_since = time.time()


def collect(st: State) -> Metrics:
    now = time.time()
    m = Metrics()
    gpus = parse_gpus(sh("nvidia-smi", f"--query-gpu={','.join(GPU_FIELDS)}", "--format=csv,noheader,nounits"))
    gpu_metrics(m, gpus)
    bus_to_index = {g["pci.bus_id"].lower().removeprefix("00000000:"): g["index"] for g in gpus}

    if now - st.slow_at >= SLOW_EVERY:
        st.slow_at = now
        st.expected = expected_services() or st.expected
        st.slow = Metrics()
        if os.geteuid() == 0:
            smart_metrics(st.slow)
        host = env_value("PUBLIC_HOST")
        ip = public_ip()
        if host and ip:
            st.slow.add("atentina_public_ip_ok", int(ip == host), help="La IP pública es PUBLIC_HOST")
        st.slow.add("atentina_internet_ok", int(ip is not None), help="Cloudflare responde por HTTPS")

    ids = container_metrics(m, inspect_project(), st.expected)
    gpu_process_metrics(m, ids, bus_to_index)

    if now - st.sip_at >= SIP_EVERY:
        st.sip_at = now
        st.sip = Metrics()
        cid = next((i for i, s in ids.items() if s == "asterisk"), None)
        if cid:
            regs = parse_registrations(sh("docker", "exec", cid, "asterisk", "-rx", "pjsip show registrations"))
            for name, ok in regs.items():
                st.sip.add("atentina_sip_registered", ok, {"registration": name}, "Registro SIP de Asterisk")

    if os.geteuid() == 0:
        since = st.xid_since
        st.xid_since = now
        for bus, xid in parse_xid(sh("journalctl", "-k", "--no-pager", "-q", f"--since=@{int(since)}",
                                     "--grep", "NVRM: Xid")):
            key = (bus_to_index.get(bus.removeprefix("0000:"), bus), xid)
            st.xid_total[key] = st.xid_total.get(key, 0) + 1
        for (gpu, xid), n in st.xid_total.items():
            m.add("atentina_gpu_xid_errors_total", n, {"gpu": gpu, "xid": xid}, "Errores XID del driver", "counter")
        try:
            m.add("atentina_cpu_energy_joules_total", int(RAPL.read_text()) / 1e6, help="Energía del paquete de la "
                  "CPU (RAPL; da la vuelta, usar rate)", kind="counter")
        except (OSError, ValueError):
            pass

    for extra in (st.slow, st.sip):
        for name, (h, kind) in extra.help.items():
            m.help.setdefault(name, (h, kind))
        m.samples += extra.samples
    m.add("atentina_hostmon_last_run_timestamp_seconds", time.time(), help="Última vuelta del colector")
    return m


def write(m: Metrics):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = OUT_DIR / f".atentina.prom.{os.getpid()}"
    tmp.write_text(m.render())
    tmp.chmod(0o644)
    tmp.replace(OUT_DIR / "atentina.prom")


def main():
    st = State()
    once = "--once" in sys.argv
    print(f"hostmon: proyecto {PROJECT}, cada {INTERVAL:g} s en {OUT_DIR}, host {socket.gethostname()}",
          flush=True)
    while True:
        t0 = time.monotonic()
        try:
            write(collect(st))
        except Exception as e:  # que una vuelta rota no mate el servicio
            print(f"hostmon: error {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        if once:
            return
        time.sleep(max(0.5, INTERVAL - (time.monotonic() - t0)))


if __name__ == "__main__":
    main()
