#!/usr/bin/env python3
"""Benchmark reutilizable de GPU: velocidad de la memoria y transferencias PCIe host<->GPU,
con el resultado como % de la especificacion (para comparar GPUs entre si).

Compila gpubench.cu con nvcc la primera vez (cache en scratch/gpubench/) y lo corre
por cada GPU. Solo stdlib + nvcc + nvidia-smi.

  python3 scripts/gpubench/gpubench.py                  # todas las GPUs
  python3 scripts/gpubench/gpubench.py --gpu 1 --iters 20 --out scratch/gpubench/3090.json

Que mide y contra que se compara:
  - Memoria: lectura, escritura y copia con kernels (16 B por acceso, buffer de ~1 GiB, mayor que
    el L2) y cudaMemcpy D2D. Especificacion = bus (bits) x reloj de memoria maximo x 2 / 8, igual
    que la cifra del fabricante. Un limite de reloj de memoria (`nvidia-smi -lmc`) o de potencia
    baja el numero: el reporte muestra los relojes vistos durante la corrida.
  - PCIe: H2D, D2H y ambos a la vez, con memoria pinned y pageable. Especificacion = GB/s por
    carril de la generacion x ancho del enlace (por sentido). Se toma el enlace que nvidia-smi ve
    durante la corrida (en reposo baja de generacion). Un enlace bien armado llega a ~85-90 %.
  - Latencia: pedido de 4 B en cada sentido y lanzamiento de un kernel vacio.
Correr con la GPU sin carga (parar la inferencia si la usa): mide contra lo que haya en ejecucion.
"""
import argparse, json, os, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
BUILD = os.path.join(REPO, "scratch", "gpubench")
SRC = os.path.join(HERE, "gpubench.cu")
BIN = os.path.join(BUILD, "gpubench")
# GB/s por carril y por sentido, tras la codificacion (8b/10b en gen1-2, 128b/130b desde gen3).
PCIE_LANE_GBS = {1: 0.25, 2: 0.5, 3: 0.9846, 4: 1.9692, 5: 3.9385}


def sh(*a, timeout=30):
    r = subprocess.run(a, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip() if r.returncode == 0 else ""


def build(force=False):
    if not force and os.path.exists(BIN) and os.path.getmtime(BIN) >= os.path.getmtime(SRC):
        return
    os.makedirs(BUILD, exist_ok=True)
    # sm_86 nativo (Ampere) y PTX de compute_90, que el driver compila al vuelo para GPUs mas nuevas
    # (Blackwell, sm_120, necesita CUDA >= 12.8 para compilar nativo).
    cmd = ["nvcc", "-O3", "-std=c++14", "-gencode", "arch=compute_86,code=sm_86",
           "-gencode", "arch=compute_90,code=compute_90", "-o", BIN, SRC]
    print("compilando:", " ".join(cmd), file=sys.stderr)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit("nvcc fallo:\n" + r.stderr)


def smi_gpus():
    q = "index,pci.bus_id,name,pcie.link.gen.max,pcie.link.width.max,power.limit,clocks.max.mem,clocks.max.sm"
    out = sh("nvidia-smi", f"--query-gpu={q}", "--format=csv,noheader,nounits")
    rows = []
    for ln in out.splitlines():
        f = [x.strip() for x in ln.split(",")]
        rows.append(dict(zip(q.split(","), f)))
    return rows


class Sampler(threading.Thread):
    """nvidia-smi en modo continuo (cada 100 ms) durante la corrida: guarda el enlace PCIe mas
    ancho/rapido visto y los maximos de relojes, potencia y temperatura."""
    Q = "pcie.link.gen.current,pcie.link.width.current,clocks.sm,clocks.mem,power.draw,temperature.gpu"

    def __init__(self, bus_id):
        super().__init__(daemon=True)
        self.bus, self.best = bus_id, {}
        self.proc = subprocess.Popen(["nvidia-smi", "-i", bus_id, f"--query-gpu={self.Q}",
                                      "--format=csv,noheader,nounits", "-lms", "100"],
                                     stdout=subprocess.PIPE, text=True)

    def run(self):
        for ln in self.proc.stdout:
            try:
                gen, wid, sm, mem, pw, t = [float(x) for x in ln.split(",")]
            except ValueError:
                continue
            b = self.best
            if gen * wid >= b.get("gen", 0) * b.get("width", 0):
                b["gen"], b["width"] = int(gen), int(wid)
            for k, v in (("sm_mhz", sm), ("mem_mhz", mem), ("power_w", pw), ("temp_c", t)):
                b[k] = max(b.get(k, 0), v)

    def close(self):
        self.proc.terminate(); self.join(timeout=3)


def pct(x, ref):
    return f"{100 * x / ref:5.1f} %" if ref else "    -  "


def run_gpu(g, a):
    s = Sampler(g["pci.bus_id"]); s.start()
    r = subprocess.run([BIN, "--device", g["index"], "--iters", str(a.iters), "--size-mb", str(a.size_mb),
                        "--mem-mb", str(a.mem_mb)], capture_output=True, text=True,
                       # CUDA ordena por rapidez, nvidia-smi por bus PCI: sin esto los indices no coinciden.
                       env={**os.environ, "CUDA_DEVICE_ORDER": "PCI_BUS_ID"})
    s.close()
    if r.returncode:
        return {"device": int(g["index"]), "error": r.stderr.strip()}
    d = json.loads(r.stdout)
    d["pci_bus_id"], d["observed"] = g["pci.bus_id"], s.best
    d["power_limit_w"] = float(g["power.limit"])
    d["link_max"] = {"gen": int(g["pcie.link.gen.max"]), "width": int(g["pcie.link.width.max"])}
    d["spec_mem_gbs"] = 2 * d["mem_clock_khz"] * 1e3 * d["bus_bits"] / 8 / 1e9
    gen, wid = s.best.get("gen", 0), s.best.get("width", 0)
    d["spec_pcie_gbs"] = PCIE_LANE_GBS.get(gen, 0) * wid
    return d


def report(d):
    if "error" in d:
        print(f"\nGPU {d['device']}: ERROR {d['error']}"); return
    o, m, p = d["observed"], d["mem"], d["pcie"]
    sm, sp = d["spec_mem_gbs"], d["spec_pcie_gbs"]
    print(f"\n=== GPU {d['device']}: {d['name']} (sm_{d['cc'].replace('.', '')}, {d['sms']} SM, "
          f"{d['mem_total_mib']} MiB, L2 {d['l2_kib']} KiB, bus {d['bus_bits']} bits) ===")
    print(f"  PCIe  {d['pci_bus_id']}: gen{o.get('gen')} x{o.get('width')} en uso "
          f"(max de la GPU: gen{d['link_max']['gen']} x{d['link_max']['width']})")
    print(f"  Vistos: SM {o.get('sm_mhz'):.0f} MHz, mem {o.get('mem_mhz'):.0f} MHz, "
          f"{o.get('power_w'):.0f} W (limite {d['power_limit_w']:.0f} W), {o.get('temp_c'):.0f} C")
    print(f"\n  Memoria (buffer {d['mem_buf_mib']} MiB, {d['iters']} corridas)      GB/s mediana   mejor    % espec.")
    print(f"    {'especificacion (reloj max)':<28}{sm:>12.1f}")
    seen = sm * o.get("mem_mhz", 0) * 1e3 / d["mem_clock_khz"]
    if seen < 0.98 * sm:
        print(f"    {'especificacion (reloj visto)':<28}{seen:>12.1f}   memoria a {o.get('mem_mhz'):.0f} de "
              f"{d['mem_clock_khz'] / 1e3:.0f} MHz: {pct(m['read']['med'], seen).strip()} de esto en lectura")
    for k, lab in (("read", "lectura (kernel)"), ("write", "escritura (kernel)"),
                   ("copy", "copia (kernel, R+W)"), ("memcpy_d2d", "cudaMemcpy D2D (R+W)")):
        print(f"    {lab:<28}{m[k]['med']:>12.1f}{m[k]['best']:>9.1f}   {pct(m[k]['med'], sm)}")
    print(f"\n  PCIe ({d['xfer_mib']} MiB)                                GB/s mediana   mejor    % espec.")
    print(f"    {'especificacion (por sentido)':<28}{sp:>12.1f}")
    for k, lab in (("h2d_pinned", "H2D pinned"), ("d2h_pinned", "D2H pinned"),
                   ("h2d_pageable", "H2D pageable"), ("d2h_pageable", "D2H pageable"),
                   ("bidir_pinned", "ambos sentidos (suma)")):
        ref = sp * 2 if k == "bidir_pinned" else sp
        print(f"    {lab:<28}{p[k]['med']:>12.2f}{p[k]['best']:>9.2f}   {pct(p[k]['med'], ref)}")
    print("    H2D pinned por tamano: " + "  ".join(
        f"{x['kib'] if x['kib'] < 1024 else str(x['kib'] // 1024) + 'M'}{'K' if x['kib'] < 1024 else ''}={x['gbs']}"
        for x in p["sweep_h2d_pinned"]) + "  (KiB/MiB=GB/s)")
    L = p["lat_us"]
    print(f"    latencia: H2D 4 B {L['h2d_4b']} us, D2H 4 B {L['d2h_4b']} us, kernel vacio {L['kernel_launch']} us")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--gpu", type=int, action="append", help="indice de GPU (repetible); default todas")
    ap.add_argument("--iters", type=int, default=10, help="corridas por medicion (mediana)")
    ap.add_argument("--size-mb", type=int, default=256, help="tamano de las transferencias PCIe")
    ap.add_argument("--mem-mb", type=int, default=1024, help="buffer para memoria (baja solo si no hay libre)")
    ap.add_argument("--out", help="guarda el resultado en JSON")
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()
    if not sh("which", "nvcc") or not sh("which", "nvidia-smi"):
        sys.exit("hacen falta nvcc y nvidia-smi")
    build(a.rebuild)
    gpus = [g for g in smi_gpus() if a.gpu is None or int(g["index"]) in a.gpu]
    busy = sh("nvidia-smi", "--query-compute-apps=pid,name,used_memory", "--format=csv,noheader")
    if busy:
        print("AVISO: hay procesos de computo en las GPUs; los numeros pueden salir bajos:\n  "
              + busy.replace("\n", "\n  "), file=sys.stderr)
    res = []
    for g in gpus:
        res.append(run_gpu(g, a)); report(res[-1])
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump({"fecha": time.strftime("%Y-%m-%d %H:%M:%S"), "host": os.uname().nodename, "gpus": res},
                  open(a.out, "w"), indent=1)
        print(f"\nJSON: {a.out}")


if __name__ == "__main__":
    main()
