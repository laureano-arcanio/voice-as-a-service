#!/usr/bin/env python3
"""Sampler de capacidad: CPU por core, CPU/mem/threads por contenedor, GPU y
metricas de vLLM, a 1 Hz. Sale solo tras IDLE_EXIT s sin requests en vLLM
(una vez que hubo actividad). Uso: sampler.py <outdir>"""
import csv, json, os, re, subprocess, sys, time, urllib.request

OUT = sys.argv[1]
IDLE_EXIT = int(os.environ.get("IDLE_EXIT", 600))
MAX_RUN = 4 * 3600
SVCS = ["vllm-llm", "vllm-stt", "vllm-tts", "vllm-tts-2", "app", "proxy", "ngrok", "db"]
PORTS = {"vllm-llm": 8101, "vllm-stt": 8102, "vllm-tts": 8103, "vllm-tts-2": 8104}
HZ = os.sysconf("SC_CLK_TCK")
os.makedirs(OUT, exist_ok=True)

def cg(svc):
    cid = subprocess.run(["docker", "inspect", "-f", "{{.Id}}", f"voice-as-a-service-{svc}-1"],
                         capture_output=True, text=True).stdout.strip()
    p = f"/sys/fs/cgroup/system.slice/docker-{cid}.scope"
    return p if cid and os.path.isdir(p) else None

CG = {s: p for s in SVCS if (p := cg(s))}

def rd(p):
    with open(p) as f:
        return f.read()

def kv(p):
    return {a: int(b) for a, b in (l.split()[:2] for l in rd(p).splitlines() if l)}

def cpus():
    d = {}
    for l in rd("/proc/stat").splitlines():
        if l.startswith("cpu"):
            f = l.split(); v = list(map(int, f[1:9]))
            d[f[0]] = (sum(v), v[3] + v[4], v[4])  # total, idle+iowait, iowait
    return d

def threads(path):
    d = {}
    try:
        pids = rd(path + "/cgroup.procs").split()
    except OSError:
        return d
    tl = []
    for pid in pids:
        try:
            tl += [(pid, t) for t in os.listdir(f"/proc/{pid}/task")]
        except OSError:
            pass
    for pid, t in tl:
        try:
            s = rd(f"/proc/{pid}/task/{t}/stat")
        except OSError:
            continue
        r = s.rindex(")"); comm = s[s.index("(") + 1:r]; f = s[r + 2:].split()
        # f[0]=state f[11]=utime f[12]=stime f[36]=processor
        d[t] = (comm, f[0], int(f[11]), int(f[12]), int(f[36]))
    return d

GQ = "index,utilization.gpu,utilization.memory,memory.used,power.draw,temperature.gpu,clocks.sm,pstate,clocks_throttle_reasons.active,pcie.link.gen.current"
def gpus():
    o = subprocess.run(["nvidia-smi", f"--query-gpu={GQ}", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True).stdout
    return [[x.strip() for x in l.split(",")] for l in o.strip().splitlines()]

MRE = re.compile(r'^(vllm:[a-z_]+?)(?:\{(.*)\})? ([-0-9.e+]+)$')
KEEP = ("num_requests_running", "num_requests_waiting", "kv_cache_usage_perc", "num_preemptions_total",
        "prompt_tokens_total", "generation_tokens_total", "request_success_total",
        "_seconds_sum", "_seconds_count")
def vllm(port):
    try:
        t = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=0.8).read().decode()
    except Exception:
        return None
    d = {}
    for l in t.splitlines():
        m = MRE.match(l)
        if not m or not m.group(1).endswith(KEEP):
            continue
        lab = m.group(2) or ""
        st = re.search(r'stage="(\d)"', lab); fr = re.search(r'finished_reason="(\w+)"', lab)
        rs = re.search(r'reason="(\w+)"', lab) if "by_reason" in m.group(1) else None
        k = m.group(1)[5:] + (f"@s{st.group(1)}" if st else "") + (f"@{fr.group(1)}" if fr else "") + (f"@{rs.group(1)}" if rs else "")
        d[k] = d.get(k, 0) + float(m.group(3))
    return d

fs = {n: open(f"{OUT}/{n}", "a", buffering=1) for n in ("sys.csv", "cont.csv", "threads.csv", "gpu.csv", "vllm.jsonl")}
w = {n: csv.writer(f) for n, f in fs.items() if n.endswith("csv")}
ncpu = os.cpu_count()
w["sys.csv"].writerow(["ts", "total_busy_pct", "iowait_pct", "cores_gt90", "cores_gt50", "load1", "mem_used_gb", "mem_avail_gb", "swap_used_gb"] + [f"cpu{i}" for i in range(ncpu)])
w["cont.csv"].writerow(["ts", "svc", "cpu_cores", "user_cores", "sys_cores", "mem_gb", "anon_gb", "file_gb", "nthreads", "running_threads", "throttled_usec"])
w["threads.csv"].writerow(["ts", "svc", "tid", "comm", "state", "cpu_pct", "user_pct", "sys_pct", "last_cpu"])
w["gpu.csv"].writerow(["ts"] + GQ.split(","))

pc, pcont, pthr, pt = cpus(), {s: kv(p + "/cpu.stat") for s, p in CG.items()}, {s: threads(p) for s, p in CG.items()}, time.time()
start, last_active, seen = pt, pt, False
ptok = {}
while True:
    time.sleep(max(0, 1.0 - (time.time() - pt) % 1.0))
    now = time.time(); dt = now - pt; ts = f"{now:.2f}"
    c = cpus(); per = []
    for i in range(ncpu):
        a, b = c[f"cpu{i}"], pc[f"cpu{i}"]; tot = a[0] - b[0] or 1
        per.append(round(100 * (1 - (a[1] - b[1]) / tot), 1))
    a, b = c["cpu"], pc["cpu"]; tot = a[0] - b[0] or 1
    mi = {l.split(":")[0]: int(l.split()[1]) for l in rd("/proc/meminfo").splitlines()}
    w["sys.csv"].writerow([ts, round(100 * (1 - (a[1] - b[1]) / tot), 1), round(100 * (a[2] - b[2]) / tot, 1),
                           sum(x > 90 for x in per), sum(x > 50 for x in per), rd("/proc/loadavg").split()[0],
                           round((mi["MemTotal"] - mi["MemAvailable"]) / 2**20, 2), round(mi["MemAvailable"] / 2**20, 2),
                           round((mi["SwapTotal"] - mi["SwapFree"]) / 2**20, 2)] + per)
    pc = c
    for s, p in CG.items():
        try:
            cs, ms, th = kv(p + "/cpu.stat"), kv(p + "/memory.stat"), threads(p)
            mem = int(rd(p + "/memory.current"))
        except OSError:
            continue
        o = pcont[s]; run = 0
        for t, (comm, state, ut, st, cpu) in th.items():
            run += state == "R"
            if t in pthr[s]:
                du, ds = ut - pthr[s][t][2], st - pthr[s][t][3]
                pct = 100 * (du + ds) / HZ / dt
                if pct >= 2:
                    w["threads.csv"].writerow([ts, s, t, comm, state, round(pct, 1), round(100 * du / HZ / dt, 1), round(100 * ds / HZ / dt, 1), cpu])
        w["cont.csv"].writerow([ts, s, round((cs["usage_usec"] - o["usage_usec"]) / 1e6 / dt, 3),
                                round((cs["user_usec"] - o["user_usec"]) / 1e6 / dt, 3), round((cs["system_usec"] - o["system_usec"]) / 1e6 / dt, 3),
                                round(mem / 2**30, 3), round(ms.get("anon", 0) / 2**30, 3), round(ms.get("file", 0) / 2**30, 3),
                                len(th), run, cs.get("throttled_usec", 0)])
        pcont[s], pthr[s] = cs, th
    for g in gpus():
        w["gpu.csv"].writerow([ts] + g)
    active = 0
    for s, port in PORTS.items():
        d = vllm(port)
        if d is None:
            continue
        # Actividad = avance de contadores de tokens. El gauge num_requests_running
        # de vllm-omni queda pegado en 1 sin trafico, asi que no sirve para esto.
        tok = sum(v for k, v in d.items() if "tokens_total" in k)
        active += tok != ptok.get(s, tok)
        ptok[s] = tok
        fs["vllm.jsonl"].write(json.dumps({"ts": float(ts), "svc": s, **d}) + "\n")
    if active > 0:
        if not seen or now - last_active > 60:
            print(f"{time.strftime('%H:%M:%S')} actividad ({active} servicios con trafico)", flush=True)
        seen, last_active = True, now
    pt = now
    if (seen and now - last_active > IDLE_EXIT) or now - start > MAX_RUN:
        print(f"{time.strftime('%H:%M:%S')} sin actividad hace {IDLE_EXIT}s -> fin", flush=True)
        break
