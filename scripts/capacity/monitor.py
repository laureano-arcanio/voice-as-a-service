#!/usr/bin/env python3
"""Monitor del lado server del test de capacidad (docs/CAPACITY_TEST_PLAN.md,
seccion 6.3), mas la memoria de cada parte del sistema para ver como escala
con las llamadas.

Lanza el sampler de siempre (scripts/loadtest/monitor/sampler.py, sin
cambios) en <outdir>/sampler, `nvidia-smi dmon -s t` (trafico PCIe) y sigue
los logs del agente. Ademas escribe, a 1 Hz:

  mem.csv      memoria por servicio (cgroup + PSS de sus procesos), host y
               lo que queda fuera del stack
  procmem.csv  PSS/RSS/CPU por proceso: todos los del agente (main,
               forkserver, un proceso por job) y los 5 mas grandes del resto
  gpumem.csv   VRAM por proceso, mapeada a servicio
  cpu.csv      frecuencia y temperatura de la CPU, y RAPL si se puede leer
  net.csv      contadores de red por interfaz y errores UDP
  agentlog.csv sintomas de CPU saturada en el agente, por segundo

Termina con SIGTERM/SIGINT, cuando sale el sampler (IDLE_EXIT/START_TIMEOUT
por env, como siempre) o a las 4 h.

Uso: monitor.py <outdir>"""
import csv, json, os, re, signal, subprocess, sys, threading, time

OUT = os.path.abspath(sys.argv[1])
MAX_RUN = 4 * 3600
PROJECT = os.environ.get("COMPOSE_PROJECT", "voice-as-a-service")
HZ = os.sysconf("SC_CLK_TCK")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAMPLER = os.path.join(REPO, "scripts", "loadtest", "monitor", "sampler.py")
GB, MB = 2**30, 2**20
# Si leer el PSS de todos los procesos tarda mas que esto, se lee cada 5 s.
PSS_SLOW_S = 0.2
TOP_OTHERS = 5
AGENT_EVENTS = (("VAD inference is slower than realtime", "vad_slow"),
                ("event loop blocked", "loop_blocked"),
                ("no warmed process available", "no_warm"),
                ("process did not exit in time", "job_killed"),
                ('"level": "ERROR"', "error"))
os.makedirs(OUT, exist_ok=True)


def sh(*a, timeout=10):
    try:
        return subprocess.run(a, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        return ""


def rd(p):
    with open(p) as f:
        return f.read()


def containers():
    """{svc: docker inspect} de los contenedores del proyecto (como sampler.py)."""
    ids = sh("docker", "ps", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}").split()
    if not ids:
        return {}
    def name(c):
        l = c["Config"]["Labels"]
        return l["com.docker.compose.service"] + ("-run" if l.get("com.docker.compose.oneoff") == "True" else "")
    try:
        return {name(c): c for c in json.loads(sh("docker", "inspect", *ids))}
    except ValueError:
        return {}


def discover():
    """({svc: cgroup}, {container_id: svc}, id del agent)."""
    cg, ids, agent = {}, {}, None
    for svc, c in containers().items():
        p = f"/sys/fs/cgroup/system.slice/docker-{c['Id']}.scope"
        if os.path.isdir(p):
            cg[svc] = p
            ids[c["Id"]] = svc
        if svc == "agent":
            agent = c["Id"]
    return cg, ids, agent


def svc_of(pid, ids):
    """Servicio del stack de un pid del host, o ajeno:<comm>."""
    try:
        m = re.search(r"docker-([0-9a-f]{64})\.scope", rd(f"/proc/{pid}/cgroup"))
        if m and m.group(1) in ids:
            return ids[m.group(1)]
        return "ajeno:" + rd(f"/proc/{pid}/comm").strip()
    except OSError:
        return "?"


def pids_of(path):
    try:
        return [int(p) for p in rd(path + "/cgroup.procs").split()]
    except OSError:
        return []


def smaps(pid):
    """(pss, pss_anon, rss) en bytes. Si smaps_rollup no se puede leer (proceso
    de otro uid, ej. root en los contenedores de vLLM), (None, None, VmRSS de
    /proc/<pid>/status, que es legible por todos); None si el pid murio."""
    try:
        d = {}
        for l in rd(f"/proc/{pid}/smaps_rollup").splitlines()[1:]:
            k, v = l.split(":", 1)
            d[k] = int(v.split()[0]) * 1024
        return d.get("Pss", 0), d.get("Pss_Anon", 0), d.get("Rss", 0)
    except (OSError, ValueError, IndexError):
        pass
    try:
        for l in rd(f"/proc/{pid}/status").splitlines():
            if l.startswith("VmRSS:"):
                return None, None, int(l.split()[1]) * 1024
        return None, None, 0  # hilo de kernel o zombie
    except (OSError, ValueError):
        return None


def stat(pid):
    """(ppid, utime+stime en ticks), o None si el pid murio."""
    try:
        s = rd(f"/proc/{pid}/stat")
    except OSError:
        return None
    f = s[s.rindex(")") + 2:].split()
    return int(f[1]), int(f[11]) + int(f[12])


def cmdline(pid):
    try:
        return rd(f"/proc/{pid}/cmdline").replace("\0", " ")
    except OSError:
        return ""


def agent_roles(pids):
    """{pid: rol} de los procesos del agente."""
    ppid = {p: (stat(p) or (0, 0))[0] for p in pids}
    cmd = {p: cmdline(p) for p in pids}
    main = {p for p in pids if "app.livekit_agent" in cmd[p]}
    fsrv = {p for p in pids if "multiprocessing.forkserver" in cmd[p] and ppid[p] in main}
    roles = {}
    for p in pids:
        if p in main:
            roles[p] = "main"
        elif p in fsrv:
            roles[p] = "forkserver"
        elif ppid[p] in fsrv:
            roles[p] = "job"
        elif "resource_tracker" in cmd[p]:
            roles[p] = "resource_tracker"
        else:
            roles[p] = "otro"
    return roles


def memstat(path):
    try:
        ms = {a: int(b) for a, b in (l.split()[:2] for l in rd(path + "/memory.stat").splitlines() if l)}
        cur = int(rd(path + "/memory.current"))
    except OSError:
        return None
    try:
        swap = int(rd(path + "/memory.swap.current"))
    except (OSError, ValueError):
        swap = 0
    return cur, ms, swap


def meminfo():
    return {l.split(":")[0]: int(l.split()[1]) * 1024 for l in rd("/proc/meminfo").splitlines()}


def gpu_apps(ids):
    out = sh("nvidia-smi", "--query-compute-apps=gpu_bus_id,pid,used_memory", "--format=csv,noheader,nounits")
    rows = []
    for l in out.splitlines():
        f = [x.strip() for x in l.split(",")]
        if len(f) == 3 and f[1].isdigit():
            rows.append((f[0], int(f[1]), svc_of(int(f[1]), ids), f[2]))
    return rows


def hwmon_temp():
    """Ruta del sensor de temperatura de la CPU (k10temp Tctl o coretemp Package)."""
    base = "/sys/class/hwmon"
    for h in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        try:
            name = rd(f"{base}/{h}/name").strip()
        except OSError:
            continue
        if name not in ("k10temp", "coretemp"):
            continue
        for f in sorted(os.listdir(f"{base}/{h}")):
            if f.endswith("_label"):
                lab = rd(f"{base}/{h}/{f}").strip()
                if lab in ("Tctl", "Package id 0"):
                    return f"{base}/{h}/{f[:-6]}_input"
        if os.path.exists(f"{base}/{h}/temp1_input"):
            return f"{base}/{h}/temp1_input"
    return None


FREQS = sorted(p for p in (f"/sys/devices/system/cpu/{c}/cpufreq/scaling_cur_freq"
                           for c in os.listdir("/sys/devices/system/cpu") if re.fullmatch(r"cpu\d+", c))
               if os.path.exists(p))
TEMP = hwmon_temp()
RAPL = "/sys/class/powercap/intel-rapl:0/energy_uj"


def rapl():
    try:
        return int(rd(RAPL))
    except (OSError, ValueError):
        return None


def default_iface():
    for l in rd("/proc/net/route").splitlines()[1:]:
        f = l.split()
        if len(f) > 1 and f[1] == "00000000":
            return f[0]
    return None


SKIP_IF = re.compile(r"^(lo|veth|br-|docker)")


def netdev():
    d = {}
    dflt = default_iface()
    for l in rd("/proc/net/dev").splitlines()[2:]:
        name, rest = l.split(":", 1)
        name = name.strip()
        if SKIP_IF.match(name) and name != dflt:
            continue
        v = rest.split()
        # rx: bytes packets errs drop ... ; tx desde el campo 8
        d[name] = [v[0], v[8], v[1], v[9], v[2], v[10], v[3], v[11]]
    snmp = [l.split() for l in rd("/proc/net/snmp").splitlines() if l.startswith("Udp:")]
    if len(snmp) == 2:
        u = dict(zip(snmp[0][1:], snmp[1][1:]))
        d["udp"] = ["", "", u.get("InDatagrams", ""), u.get("OutDatagrams", ""),
                    u.get("InErrors", ""), "", u.get("RcvbufErrors", ""), u.get("SndbufErrors", "")]
    return d


class AgentLog:
    """Sigue `docker logs -f` del agente y cuenta eventos por segundo."""

    def __init__(self):
        self.cid = None
        self.proc = None
        self.lock = threading.Lock()
        self.counts = {}

    def attach(self, cid):
        if cid == self.cid and self.proc and self.proc.poll() is None:
            return
        self.stop()
        self.cid = cid
        if not cid:
            return
        self.proc = subprocess.Popen(["docker", "logs", "-f", "--since", "0s", cid],
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, errors="replace")
        threading.Thread(target=self._read, args=(self.proc,), daemon=True).start()

    def _read(self, proc):
        for line in proc.stdout:
            for pat, ev in AGENT_EVENTS:
                if pat in line:
                    k = (int(time.time()), ev)
                    with self.lock:
                        self.counts[k] = self.counts.get(k, 0) + 1

    def flush(self, before):
        """Cuentas de los segundos ya cerrados (< before)."""
        with self.lock:
            done = sorted(k for k in self.counts if k[0] < before)
            return [(k[0], k[1], self.counts.pop(k)) for k in done]

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None


STOP = False


def _stop(*_):
    global STOP
    STOP = True


signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)

open(f"{OUT}/monitor.pid", "w").write(str(os.getpid()))
CG, IDS, AGENT = discover()
sampler = subprocess.Popen([sys.executable, SAMPLER, f"{OUT}/sampler"],
                           stdout=open(f"{OUT}/sampler.log", "a"), stderr=subprocess.STDOUT)
dmon = subprocess.Popen(["nvidia-smi", "dmon", "-s", "t", "-d", "1", "-o", "DT"],
                        stdout=open(f"{OUT}/dmon.log", "a"), stderr=subprocess.STDOUT)
alog = AgentLog()
alog.attach(AGENT)
start = time.time()
info = {"outdir": OUT, "ts_inicio": start, "pid": os.getpid(),
        "hijos": {"sampler": sampler.pid, "dmon": dmon.pid},
        "contenedores": {s: p.rsplit("docker-", 1)[-1][:12] for s, p in CG.items()},
        "temp_sensor": TEMP, "rapl": RAPL if rapl() is not None else None}
json.dump(info, open(f"{OUT}/monitor.json", "w"), indent=1)
print(f"{time.strftime('%H:%M:%S')} {OUT}: {len(CG)} contenedores {sorted(CG)}, "
      f"agent {'si' if AGENT else 'NO'}, temp {TEMP or 'sin sensor'}", flush=True)
if info["rapl"] is None:
    print(f"{time.strftime('%H:%M:%S')} RAPL no legible sin root: rapl_w queda vacio", flush=True)

fs = {n: open(f"{OUT}/{n}", "a", buffering=1, newline="")
      for n in ("mem.csv", "procmem.csv", "gpumem.csv", "cpu.csv", "net.csv", "agentlog.csv")}
w = {n: csv.writer(f) for n, f in fs.items()}
w["mem.csv"].writerow(["ts", "componente", "mem_gb", "anon_gb", "file_gb", "shmem_gb", "kernel_gb",
                       "sock_gb", "swap_gb", "nprocs", "pss_gb", "pss_anon_gb", "rss_gb"])
w["procmem.csv"].writerow(["ts", "componente", "pid", "ppid", "rol", "pss_mb", "pss_anon_mb", "rss_mb", "cpu_pct"])
w["gpumem.csv"].writerow(["ts", "gpu", "pid", "componente", "used_mib"])
w["cpu.csv"].writerow(["ts", "freq_mhz_prom", "freq_mhz_min", "freq_mhz_max", "temp_c", "rapl_w"])
w["net.csv"].writerow(["ts", "iface", "rx_bytes", "tx_bytes", "rx_packets", "tx_packets",
                       "rx_errs", "tx_errs", "rx_drop", "tx_drop"])
w["agentlog.csv"].writerow(["ts", "evento", "cuenta"])


def r3(x):
    return round(x, 3)


pt = time.time()
pticks = {}
prapl = (rapl(), pt)
pss_every = 1
loop_s = []
n = 0
while not STOP:
    n += 1
    if n % 30 == 0:
        cg, ids, agent = discover()
        for s in set(cg) - set(CG):
            print(f"{time.strftime('%H:%M:%S')} contenedor nuevo/recreado: {s}", flush=True)
        CG, IDS = cg, ids
        alog.attach(agent)
    if sampler.poll() is not None:
        print(f"{time.strftime('%H:%M:%S')} el sampler termino (exit {sampler.returncode}) -> fin", flush=True)
        break
    time.sleep(max(0, 1.0 - (time.time() - pt) % 1.0))
    t0 = time.time()
    now = t0; dt = now - pt; ts = f"{now:.2f}"
    full_pss = n % 5 == 0  # PSS de los procesos fuera del agente
    do_pss = pss_every == 1 or full_pss
    ticks = {}

    # memoria por servicio y procesos
    stack_mem = 0
    pss_cost = 0.0
    for s, path in CG.items():
        m = memstat(path)
        if m is None:
            continue
        cur, ms, swap = m
        stack_mem += cur
        pids = pids_of(path)
        is_agent = s == "agent"
        roles = agent_roles(pids) if is_agent else {}
        per = []
        tot = [0, 0, 0]
        ok = True
        want_pss = do_pss and (is_agent or full_pss or pss_every == 1)
        for pid in pids:
            st = stat(pid)
            if st is None:
                continue
            ticks[pid] = st[1]
            cpu = round(100 * (st[1] - pticks[pid]) / HZ / dt, 1) if pid in pticks else ""
            sm = None
            if want_pss or is_agent:
                c0 = time.time()
                sm = smaps(pid)
                pss_cost += time.time() - c0
            if sm is None or sm[0] is None:
                ok = False
            if sm is not None:
                tot = [a + (b or 0) for a, b in zip(tot, sm)]
            per.append((pid, st[0], roles.get(pid, "proc"), sm, cpu))
        have = ok and per and (want_pss or is_agent)
        w["mem.csv"].writerow([ts, s, r3(cur / GB), r3(ms.get("anon", 0) / GB), r3(ms.get("file", 0) / GB),
                               r3(ms.get("shmem", 0) / GB), r3(ms.get("kernel", 0) / GB), r3(ms.get("sock", 0) / GB),
                               r3(swap / GB), len(pids),
                               r3(tot[0] / GB) if have else "", r3(tot[1] / GB) if have else "",
                               r3(tot[2] / GB) if per and (want_pss or is_agent) else ""])
        if is_agent:
            rows = per
        elif full_pss:
            # por PSS si se pudo leer, si no por RSS
            rows = sorted((p for p in per if p[3]), key=lambda p: -(p[3][0] or p[3][2]))[:TOP_OTHERS]
        else:
            rows = []
        for pid, ppid, rol, sm, cpu in rows:
            w["procmem.csv"].writerow([ts, s, pid, ppid, rol,
                                       round(sm[0] / MB, 1) if sm and sm[0] is not None else "",
                                       round(sm[1] / MB, 1) if sm and sm[1] is not None else "",
                                       round(sm[2] / MB, 1) if sm else "", cpu])
    pticks = ticks
    if pss_every == 1 and pss_cost > PSS_SLOW_S:
        pss_every = 5
        print(f"{time.strftime('%H:%M:%S')} leer PSS tardo {pss_cost*1000:.0f} ms: "
              f"fuera del agente se lee cada 5 s", flush=True)

    mi = meminfo()
    host = mi["MemTotal"] - mi["MemAvailable"]
    w["mem.csv"].writerow([ts, "host", r3(host / GB), r3(mi.get("AnonPages", 0) / GB), r3(mi.get("Cached", 0) / GB),
                           r3(mi.get("Shmem", 0) / GB),
                           r3((mi.get("Slab", 0) + mi.get("KernelStack", 0) + mi.get("PageTables", 0)) / GB),
                           "", r3((mi["SwapTotal"] - mi["SwapFree"]) / GB), "", "", "", ""])
    w["mem.csv"].writerow([ts, "fuera_del_stack", r3((host - stack_mem) / GB)] + [""] * 10)

    # VRAM por proceso
    for bus, pid, s, used in gpu_apps(IDS):
        w["gpumem.csv"].writerow([ts, bus, pid, s, used])

    # CPU: frecuencia, temperatura, RAPL
    fr = []
    for p in FREQS:
        try:
            fr.append(int(rd(p)) / 1000)
        except (OSError, ValueError):
            pass
    try:
        temp = round(int(rd(TEMP)) / 1000, 1) if TEMP else ""
    except (OSError, ValueError):
        temp = ""
    e = rapl()
    rw = ""
    if e is not None and prapl[0] is not None and e >= prapl[0]:
        rw = round((e - prapl[0]) / 1e6 / (now - prapl[1]), 1)
    prapl = (e, now)
    w["cpu.csv"].writerow([ts, round(sum(fr) / len(fr)) if fr else "", round(min(fr)) if fr else "",
                           round(max(fr)) if fr else "", temp, rw])

    # red
    for iface, v in netdev().items():
        w["net.csv"].writerow([ts, iface] + v)

    # logs del agente
    for sec, ev, c in alog.flush(int(now)):
        w["agentlog.csv"].writerow([sec, ev, c])

    loop_s.append(time.time() - t0)
    pt = now
    if now - start > MAX_RUN:
        print(f"{time.strftime('%H:%M:%S')} {MAX_RUN} s -> fin", flush=True)
        break

for p in (sampler, dmon):
    if p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
alog.stop()
for sec, ev, c in alog.flush(int(time.time()) + 1):
    w["agentlog.csv"].writerow([sec, ev, c])
for f in fs.values():
    f.close()
if loop_s:
    ls = sorted(loop_s)
    info["loop_s"] = {"n": len(ls), "p50": round(ls[len(ls) // 2], 3), "max": round(ls[-1], 3)}
info["ts_fin"] = time.time()
json.dump(info, open(f"{OUT}/monitor.json", "w"), indent=1)
try:
    os.remove(f"{OUT}/monitor.pid")
except OSError:
    pass
print(f"{time.strftime('%H:%M:%S')} monitor detenido", flush=True)
