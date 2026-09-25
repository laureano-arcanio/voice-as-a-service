#!/usr/bin/env python3
"""Ficha de hardware (y opcionalmente de config y codigo) de un host que
participa en el test de capacidad (docs/CAPACITY_TEST_PLAN.md, 6.1 y 6.2).

Solo stdlib: corre en el host, fuera de contenedores, tambien en la PC cliente
sin GPU. Lo que no se puede obtener queda en null/"" sin fallar (dmidecode solo
si `sudo -n` anda sin password).

hw_id: hash corto de los campos estables (CPU, RAM, placa, GPUs con su slot y
power limit). Mismo hardware da el mismo hw_id. config_id: idem con la config
(commit, imagenes, args, variables de capacidad, workflow, perfil).

Uso:
  python3 scripts/capacity/hwinfo.py --role inferencia,agente,livekit --config \\
      --out runs/<run>/hw_server.json [--perfil scripts/capacity/perfiles/rampa.yml] \\
      [--ping 192.168.1.99] [--ambiente "texto"] [--temp-ambiente 24.5] [--env .env]
  python3 scripts/capacity/hwinfo.py --role cliente --out hw_cliente.json --ping 192.168.1.99
"""
import argparse, glob, hashlib, json, os, re, socket, subprocess, time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROJECT = "voice-as-a-service"
HF_VOLUME = f"{PROJECT}_hf_cache"
# Variables de .env que entran en la ficha, en claro. Nada con secretos.
ENV_VARS = ("VLLM_LLM_MODEL", "VLLM_LLM_MAX_NUM_SEQS", "VLLM_LLM_GPU_MEMORY_UTILIZATION",
            "STT_MAX_BATCH", "STT_MAX_BATCH_SECONDS", "VLLM_TTS_GPU_MEMORY_UTILIZATION",
            "VLLM_TTS_MAX_NUM_SEQS", "VLLM_TTS_MODEL", "VLLM_TTS_VOICE", "TTS_FT_CKPT",
            "WORKFLOW_ID", "COMPOSE_FILE", "LIVEKIT_URL", "LIVEKIT_LOCAL_NODE_IP")
SECRET_WORDS = ("KEY", "SECRET", "PASSWORD", "TOKEN")
GPU_Q = ("index,name,memory.total,driver_version,vbios_version,power.limit,power.default_limit,"
         "clocks.max.sm,clocks.max.mem,pcie.link.gen.current,pcie.link.gen.max,"
         "pcie.link.width.current,pcie.link.width.max,pci.bus_id")


def sh(*a, timeout=15):
    try:
        r = subprocess.run(a, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def rd(p, default=""):
    try:
        with open(p) as f:
            return f.read().strip()
    except OSError:
        return default


def num(s):
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return None


def short_hash(obj):
    data = obj if isinstance(obj, (bytes, str)) else json.dumps(obj, sort_keys=True)
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha1(data).hexdigest()[:8]


# --- hardware -------------------------------------------------------------

def host_info():
    osr = dict(re.findall(r'^(\w+)="?([^"\n]*)"?$', rd("/etc/os-release"), re.M))
    return {"hostname": socket.gethostname(), "kernel": os.uname().release,
            "distro": osr.get("PRETTY_NAME", ""),
            "docker": sh("docker", "version", "--format", "{{.Server.Version}}"),
            "nvidia_ctk": sh("nvidia-ctk", "--version").splitlines()[0] if sh("nvidia-ctk", "--version") else ""}


def cpu_info():
    ls = dict((k.strip(), v.strip()) for k, v in
              (l.split(":", 1) for l in sh("lscpu").splitlines() if ":" in l))
    hilos = num(ls.get("CPU(s)")) or os.cpu_count()
    por_socket = num(ls.get("Core(s) per socket")) or 0
    sockets = num(ls.get("Socket(s)")) or 1
    base = rd("/sys/devices/system/cpu/cpu0/cpufreq/base_frequency")
    smt = rd("/sys/devices/system/cpu/smt/active")
    boost = rd("/sys/devices/system/cpu/cpufreq/boost")
    return {"modelo": ls.get("Model name", ""), "nucleos": por_socket * sockets or None, "hilos": hilos,
            "mhz_base": round(int(base) / 1000) if base.isdigit() else None,
            "mhz_min": num(ls.get("CPU min MHz")), "mhz_max": num(ls.get("CPU max MHz")),
            "governor": rd("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
            "boost": (boost == "1") if boost else None,
            "smt": (smt == "1") if smt else None}


def ram_info():
    kb = next((int(l.split()[1]) for l in rd("/proc/meminfo").splitlines() if l.startswith("MemTotal")), 0)
    out = {"total_gb": round(kb / 2**20, 1), "velocidad_mts": None, "modulos": []}
    # dmidecode necesita root: solo si sudo no pide password
    txt = sh("sudo", "-n", "dmidecode", "-t", "memory", timeout=10)
    for dev in txt.split("Memory Device")[1:]:
        f = dict((k.strip(), v.strip()) for k, v in (l.split(":", 1) for l in dev.splitlines() if ":" in l))
        if not f.get("Size", "")[:1].isdigit():  # slot vacio ("No Module Installed")
            continue
        out["modulos"].append({"slot": f.get("Locator", ""), "tamano": f.get("Size", ""),
                               "tipo": f.get("Type", ""), "velocidad": f.get("Configured Memory Speed") or f.get("Speed", ""),
                               "fabricante": f.get("Manufacturer", ""), "parte": f.get("Part Number", "")})
    if out["modulos"]:
        out["velocidad_mts"] = num(out["modulos"][0]["velocidad"].split()[0]) if out["modulos"][0]["velocidad"] else None
        out["canales"] = len({m["slot"].split("_")[0] for m in out["modulos"]})
    return out


def placa_info():
    d = "/sys/class/dmi/id/"
    return {k: rd(d + k) for k in ("board_vendor", "board_name", "bios_version", "bios_date")}


def gpu_info():
    o = sh("nvidia-smi", f"--query-gpu={GPU_Q}", "--format=csv,noheader,nounits")
    keys = GPU_Q.split(",")
    gpus = []
    for l in o.splitlines():
        v = [x.strip() for x in l.split(",")]
        if len(v) != len(keys):
            continue
        g = {}
        for k, x in zip(keys, v):
            g[k] = x if k in ("name", "driver_version", "vbios_version", "pci.bus_id") else num(x)
        gpus.append(g)
    m = re.search(r"CUDA Version:\s*([\d.]+)", sh("nvidia-smi"))
    return gpus, (m.group(1) if m else "")


def disco_info():
    mp = sh("docker", "volume", "inspect", HF_VOLUME, "--format", "{{.Mountpoint}}")
    out = {"volumen": HF_VOLUME if mp else "", "mountpoint": mp, "fuente": "", "disco": "",
           "modelo": "", "rotacional": None, "transporte": ""}
    # el mountpoint esta bajo /var/lib/docker (sin permiso de lectura): se sube
    # hasta el primer directorio accesible, que esta en el mismo filesystem
    path, src = mp or "/var/lib/docker", ""
    while path and not src:
        src = sh("findmnt", "-no", "SOURCE", "-T", path)
        path = os.path.dirname(path) if path != "/" else ""
    src = re.sub(r"\[.*\]$", "", src)  # btrfs: /dev/x[/subvol]
    out["fuente"] = src
    if src.startswith("/dev/"):
        parent = sh("lsblk", "-no", "PKNAME", src).splitlines()
        disk = "/dev/" + parent[0] if parent and parent[0] else src
        out["disco"] = disk
        info = sh("lsblk", "-dno", "MODEL,ROTA,TRAN", disk).split()
        if info:
            out["transporte"] = info[-1] if len(info) >= 3 else ""
            rota = info[-2] if len(info) >= 3 else info[-1]
            out["rotacional"] = (rota == "1") if rota in ("0", "1") else None
            out["modelo"] = " ".join(info[:-2] if len(info) >= 3 else info[:-1])
    return out


def default_iface():
    for l in rd("/proc/net/route").splitlines()[1:]:
        f = l.split()
        if len(f) > 2 and f[1] == "00000000":
            return f[0]
    return ""


def ping(host):
    o = sh("ping", "-c", "10", "-i", "0.2", "-W", "2", host, timeout=30)
    loss = re.search(r"([\d.]+)% packet loss", o)
    rtt = re.search(r"= ([\d.]+)/([\d.]+)/([\d.]+)", o)
    return {"host": host, "perdida_pct": num(loss.group(1)) if loss else None,
            "rtt_min_ms": num(rtt.group(1)) if rtt else None, "rtt_avg_ms": num(rtt.group(2)) if rtt else None,
            "rtt_max_ms": num(rtt.group(3)) if rtt else None}


def red_info(targets):
    iface = default_iface()
    speed = rd(f"/sys/class/net/{iface}/speed") if iface else ""
    drv = os.path.basename(os.path.realpath(f"/sys/class/net/{iface}/device/driver")) if iface and os.path.exists(f"/sys/class/net/{iface}/device/driver") else ""
    return {"interfaz": iface, "velocidad_mbps": num(speed) if speed and not speed.startswith("-") else None,
            "driver": drv, "ping": [ping(h) for h in targets]}


def reloj_info():
    st = sh("timedatectl", "timesync-status")
    off = re.search(r"Offset:\s*([+-]?[\d.]+\s*\w+)", st)
    srv = re.search(r"Server:\s*(.+)", st)
    show = dict(l.split("=", 1) for l in sh("timedatectl", "show").splitlines() if "=" in l)
    return {"ntp_sincronizado": (show.get("NTPSynchronized") == "yes") if show else None,
            "offset": off.group(1) if off else "", "servidor": srv.group(1).strip() if srv else ""}


# --- config y codigo ------------------------------------------------------

def redact(args):
    # misma logica que scripts/loadtest/monitor/sampler.py
    out = []
    for a in args or []:
        out.append("<redacted>" if out and out[-1] == "--api-key" else re.sub(r"(--api-key=).*", r"\1<redacted>", a))
    return out


def read_env(path):
    d = {}
    for l in rd(path).splitlines():
        l = l.strip()
        if not l or l.startswith("#") or "=" not in l:
            continue
        k, v = l.split("=", 1)
        d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def git_info(out_base):
    g = {"commit": sh("git", "-C", REPO, "rev-parse", "HEAD"),
         "rama": sh("git", "-C", REPO, "rev-parse", "--abbrev-ref", "HEAD"),
         "dirty": bool(sh("git", "-C", REPO, "status", "--porcelain")), "diff": "",
         # archivos nuevos sin versionar: no entran en git diff
         "sin_versionar": sh("git", "-C", REPO, "ls-files", "--others", "--exclude-standard").splitlines()}
    if g["dirty"]:
        diff = sh("git", "-C", REPO, "diff", "HEAD", timeout=30)
        if diff:
            p = out_base + ".diff"
            with open(p, "w") as f:
                f.write(diff + "\n")
            g["diff"] = os.path.basename(p)
            g["diff_sha1"] = short_hash(diff)
    return g


def servicios():
    ids = sh("docker", "ps", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}").split()
    if not ids:
        return {}
    try:
        cs = json.loads(sh("docker", "inspect", *ids, timeout=30) or "[]")
    except ValueError:
        return {}
    out = {}
    for c in cs:
        l = c["Config"]["Labels"]
        if l.get("com.docker.compose.oneoff") == "True":
            continue  # `docker compose run` (ej. make loadtest): no es config del stack
        devs = [d for r in (c["HostConfig"].get("DeviceRequests") or []) for d in (r.get("DeviceIDs") or [])]
        out[l["com.docker.compose.service"]] = {
            "imagen": c["Config"]["Image"], "image_id": c["Image"][:19],
            "cmd": redact((c["Config"].get("Entrypoint") or []) + (c["Config"].get("Cmd") or [])),
            "gpu_device_ids": devs,
            "compose_files": [os.path.basename(x) for x in l.get("com.docker.compose.project.config_files", "").split(",") if x],
            "started": c["State"]["StartedAt"]}
    return dict(sorted(out.items()))


def workflow_info(wid):
    out = {"id": wid, "sha1": "", "extends": "", "extends_sha1": ""}
    p = os.path.join(REPO, "app", "workflows", f"{wid}.yml")
    txt = rd(p)
    if not txt:
        return out
    out["sha1"] = short_hash(txt)
    m = re.search(r"^extends:\s*([\w.-]+)", txt, re.M)
    if m:
        out["extends"] = m.group(1)
        base = rd(os.path.join(REPO, "app", "workflows", f"{m.group(1)}.yml"))
        out["extends_sha1"] = short_hash(base) if base else ""
    return out


def perfil_info(path):
    txt = rd(path)
    if not txt:
        return {"nombre": os.path.splitext(os.path.basename(path))[0], "sha1": "", "version": None}
    m = re.search(r"^version:\s*(\S+)", txt, re.M)
    return {"nombre": os.path.splitext(os.path.basename(path))[0], "sha1": short_hash(txt),
            "version": num(m.group(1)) if m else None}


def config_info(args, out_base):
    env = read_env(args.env)
    cap = {k: env[k] for k in ENV_VARS if k in env and not any(w in k for w in SECRET_WORDS)}
    svcs = servicios()
    agents = sh("docker", "exec", f"{PROJECT}-agent-1", "python", "-c",
                "import importlib.metadata as m;print(m.version('livekit-agents'))", timeout=30)
    cfg = {"git": git_info(out_base), "servicios": svcs, "env": cap,
           "workflow": workflow_info(cap.get("WORKFLOW_ID", "")),
           "livekit": {"server": svcs.get("livekit", {}).get("imagen", ""),
                       "sip": svcs.get("livekit-sip", {}).get("imagen", ""),
                       "agents": agents or None}}
    if args.perfil:
        cfg["perfil"] = perfil_info(args.perfil)
    # sin campos volatiles: started, nombre del diff (el contenido va por diff_sha1)
    estable = json.loads(json.dumps(cfg))
    estable["git"].pop("diff", None)
    estable["git"].pop("sin_versionar", None)  # cambia al trabajar en el repo; dirty ya lo marca
    for s in estable["servicios"].values():
        s.pop("started", None)
    return cfg, short_hash(estable)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--role", required=True, help="roles separados por coma: inferencia, agente, livekit, cliente")
    p.add_argument("--out", required=True, help="archivo JSON de salida")
    p.add_argument("--config", action="store_true", help="agrega la ficha de config y codigo (server de inferencia)")
    p.add_argument("--perfil", default="", help="perfil de carga (entra en la ficha de config)")
    p.add_argument("--ping", default="", help="hosts a medir (RTT y perdida), separados por coma")
    p.add_argument("--ambiente", default="", help="notas del ambiente (texto libre)")
    p.add_argument("--temp-ambiente", type=float, default=None, help="temperatura ambiente en C")
    p.add_argument("--env", default=os.path.join(REPO, ".env"), help="ruta del .env (default: el del repo)")
    args = p.parse_args()

    gpus, cuda = gpu_info()
    info = {"rol": [r.strip() for r in args.role.split(",") if r.strip()], "ts": time.time(),
            "host": host_info(), "cpu": cpu_info(), "ram": ram_info(), "placa": placa_info(),
            "gpus": gpus, "cuda": cuda, "disco": disco_info(),
            "red": red_info([h.strip() for h in args.ping.split(",") if h.strip()]),
            "reloj": reloj_info(),
            "ambiente": {"notas": args.ambiente, "temp_c": args.temp_ambiente}}
    c = info["cpu"]
    info["hw_estable"] = {
        "cpu": c["modelo"], "nucleos": c["nucleos"], "hilos": c["hilos"], "smt": c["smt"],
        "ram_gb": round(info["ram"]["total_gb"]), "placa": info["placa"],
        "gpus": [{k: g.get(k) for k in ("name", "memory.total", "pci.bus_id", "power.limit",
                                        "pcie.link.gen.max", "pcie.link.width.max")} for g in gpus]}
    info["hw_id"] = short_hash(info["hw_estable"])

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if args.config:
        info["config"], info["config_id"] = config_info(args, os.path.splitext(out)[0])
    with open(out, "w") as f:
        json.dump(info, f, indent=1, ensure_ascii=False)

    print(f"{info['host']['hostname']} ({','.join(info['rol'])}): hw_id {info['hw_id']}"
          + (f", config_id {info['config_id']}" if args.config else ""))
    print(f"  CPU {c['modelo']} ({c['nucleos']}c/{c['hilos']}t), RAM {info['ram']['total_gb']} GB")
    for g in gpus:
        print(f"  GPU {g['index']}: {g['name']} {g['memory.total']} MiB, {g['power.limit']} W, "
              f"PCIe gen{g['pcie.link.gen.max']} x{g['pcie.link.width.max']} ({g['pci.bus_id']})")
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
