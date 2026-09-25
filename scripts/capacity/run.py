"""Test de capacidad con calidad percibida (docs/CAPACITY_TEST_PLAN.md).

Corre en la PC cliente, dentro del contenedor `agent` (como `make loadtest`).
Lee un perfil de scripts/capacity/perfiles/, genera llegadas Poisson por
escalon (o llamadas en serie, modo `cerrado`, para la linea base) y cada
llamada la atiende un QualityCaller: el VirtualCaller de scripts/loadtest con
mas medicion (saludo, cortes dentro de la respuesta, transcripcion).

Salida en scripts/capacity/runs/<fecha>_<perfil>/: run.json, calls.csv,
turns.csv y client.csv (CPU del cliente a 1 Hz). El analisis (analyze.py) lo
cruza con el monitor del server.

Uso:
    make capacity PERFIL=rampa ARGS="--base-url http://192.168.1.99:8011"
    make capacity PERFIL=base
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
import multiprocessing as mp
import os
import random
import re
import shutil
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import yaml

from app import config
from scripts.loadtest.caller import (AgentHangup, VirtualCaller, load_pcm16_mono,
                                     sample_think_time)
from scripts.loadtest.run import _create_call, _load_utterances, _mint_token, _preflight, _transient

HERE = Path(__file__).resolve().parent
PERFILES = HERE / "perfiles"
RUNS = HERE / "runs"
# Ficha de hardware del cliente: la escribe `make capacity` con hwinfo.py en el
# host (fuera del contenedor) antes de lanzar el run.
HW_CLIENTE = RUNS / ".hw_cliente.json"

# Silencio dentro de una respuesta que cuenta como corte (entre 0,3 s y el
# SILENCE_HOLD_S de caller.py, 1,5 s, que ya es fin de respuesta).
CORTE_MIN_S = 0.3
# Callers por proceso: hasta ~16 anda (ver scripts/loadtest/run.py); se deja margen.
CALLERS_POR_PROCESO = 12

TURN_COLUMNS = [
    "call_id", "paso", "concurrencia_obj", "turno", "categoria", "texto", "transcripcion", "wer",
    "t_habla", "t_fin_envio", "t_resp", "t_fin_resp", "espera_s", "resp_s", "cortes_n", "cortes_s",
    "error", "pausa_s", "apareado",
    "eou", "stt", "endpointing", "llm", "llm_total", "tts", "total", "e2e",
]
SERVER_KEYS = ("eou", "stt", "endpointing", "llm", "llm_total", "tts", "total", "e2e")
CALL_COLUMNS = [
    "call_id", "paso", "concurrencia_obj", "t_prog", "t_inicio", "t_conectado", "saludo_s", "t_fin",
    "turnos_plan", "turnos_cliente", "turnos_server", "turnos_sin_resp", "status", "ended_reason",
    "error", "mic_lag_max_s", "workflow_status", "outcome", "wer", "cortes",
]


# ---------- perfil ----------

def cargar_perfil(nombre: str) -> tuple[dict, str]:
    """Perfil mezclado con _comun.yml y hash del contenido (va al registro)."""
    path = Path(nombre) if nombre.endswith((".yml", ".yaml")) else PERFILES / f"{nombre}.yml"
    comun = PERFILES / "_comun.yml"
    raw = comun.read_text() + "\n---\n" + path.read_text()
    perfil = {**yaml.safe_load(comun.read_text()), **yaml.safe_load(path.read_text())}
    return perfil, hashlib.sha1(raw.encode()).hexdigest()[:8]


def llegadas_poisson(concurrencia: float, dur_llamada_s: float, desde: float, hasta: float,
                     rng: random.Random) -> list[float]:
    """Instantes de llegada en [desde, hasta) con tasa concurrencia/duracion (Little)."""
    lam = concurrencia / dur_llamada_s
    t, out = desde, []
    while True:
        t += rng.expovariate(lam)
        if t >= hasta:
            return out
        out.append(t)


# ---------- caller con medicion de calidad ----------

def textos_corpus() -> dict[str, str]:
    """Nombre de archivo -> texto del corpus de scripts/loadtest (gen_audio.py)."""
    try:
        from scripts.loadtest.gen_audio import UTTERANCES
    except Exception:  # noqa: BLE001
        return {}
    return {f"{cat}_{i:02d}.wav": t for cat, textos in UTTERANCES.items() for i, t in enumerate(textos)}


@dataclass
class TurnoQ:
    categoria: str
    texto: str
    t_habla: float            # epoch: el usuario empieza a hablar
    t_fin_envio: float = 0.0  # epoch: termino de mandar su audio
    t_resp: float | None = None       # epoch: primer audio del agente
    t_fin_resp: float | None = None   # epoch: el agente termino de hablar
    error: str = ""
    pausa_s: float = 0.0
    cortes: list[float] = field(default_factory=list)  # silencios dentro de la respuesta (s)


class QualityCaller(VirtualCaller):
    """VirtualCaller que ademas registra en epoch: conexion, saludo, cada
    respuesta (inicio y fin) y los silencios de 0,3-1,5 s dentro de ella."""

    def __init__(self, *a, textos: dict[str, str], **kw):
        super().__init__(*a, **kw)
        self.textos = textos
        self.off = time.time() - time.monotonic()   # monotonic -> epoch
        self.t_conectado: float | None = None
        self.t_saludo: float | None = None
        self.turnos: list[TurnoQ] = []
        self._ultimo_fuerte = 0.0
        self._silencios: list[tuple[float, float]] = []  # (fin del silencio mono, duracion)

    async def _consume_audio(self, track):  # mismo stream que el original + registro de silencios
        from livekit import rtc
        import audioop
        from scripts.loadtest.caller import LISTEN_FRAME_MS, LISTEN_SAMPLE_RATE, SILENCE_RMS_THRESHOLD
        stream = rtc.AudioStream(track, sample_rate=LISTEN_SAMPLE_RATE, num_channels=1,
                                 frame_size_ms=LISTEN_FRAME_MS)
        self._streams.append(stream)
        async for ev in stream:
            now = time.monotonic()
            if self._detector.speaking and audioop.rms(bytes(ev.frame.data), 2) > SILENCE_RMS_THRESHOLD:
                gap = now - self._ultimo_fuerte
                if CORTE_MIN_S <= gap:
                    self._silencios.append((now, gap))
                self._ultimo_fuerte = now
            self._detector.feed(ev.frame, now)
            if self._detector.speaking and self._ultimo_fuerte < (self._detector.speaking_since or 0):
                self._ultimo_fuerte = now

    def _cortes_entre(self, a: float, b: float) -> list[float]:
        return [round(d, 3) for t, d in self._silencios if a < t <= b]

    async def run(self):
        error = None
        greeted = False
        try:
            self._wire_events()
            from livekit import rtc
            await self.room.connect(self.livekit_url, self.token, options=rtc.RoomOptions(auto_subscribe=True))
            self.t_conectado = time.time()
            self.t_saludo = await self._wait_for_speech_start(self.greeting_timeout) + self.off
            greeted = True
            await self._wait_until_silent(self.reply_timeout)
            await self._publish_mic()
            for _ in range(self.n_turns):
                path, cat = self._pick_utterance()
                pcm, sr = load_pcm16_mono(path)
                if sr != self._mic_sample_rate:
                    raise ValueError(f"sample rate {sr} != mic {self._mic_sample_rate} (regenerar audio)")
                t = TurnoQ(categoria=cat, texto=self.textos.get(path.name, ""), t_habla=time.time())
                self.turnos.append(t)
                sent_end = await self._speak(pcm)
                t.t_fin_envio = sent_end + self.off
                try:
                    started = await self._wait_for_speech_start(self.turn_timeout)
                    t.t_resp = started + self.off
                    await self._wait_until_silent(self.reply_timeout)
                    fin = time.monotonic()
                    t.t_fin_resp = fin + self.off
                    t.cortes = self._cortes_entre(started, fin)
                except TimeoutError as e:
                    t.error = str(e)
                t.pausa_s = sample_think_time()
                await asyncio.sleep(t.pausa_s)
        except AgentHangup as e:
            error = f"AgentHangup: {e}"
        except Exception as e:  # noqa: BLE001
            error = f"{type(e).__name__}: {e}"
        finally:
            await self._cleanup()
        self.error, self.greeted = error, greeted
        return self


# ---------- una llamada ----------

def _norm(s: str) -> list[str]:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", s)


def wer(ref: str, hyp: str) -> float | None:
    r, h = _norm(ref), _norm(hyp)
    if not r:
        return None
    d = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        prev, d[0] = d[0], i
        for j, hw in enumerate(h, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (rw != hw))
    return round(d[-1] / len(r), 3)


async def _detalle_final(client: httpx.AsyncClient, base_url: str, cid: str, timeout: float) -> dict:
    """GET /api/calls/{id} completo cuando el agente cierra la llamada."""
    deadline = time.monotonic() + timeout
    ultimo: dict = {}
    while time.monotonic() < deadline:
        try:
            r = await client.get(f"{base_url}/api/calls/{cid}")
            r.raise_for_status()
            ultimo = r.json()
            if (ultimo.get("call") or {}).get("status") in ("finalizada", "fallida"):
                return ultimo
        except httpx.HTTPError as e:
            if not _transient(e):
                raise
        await asyncio.sleep(1.0)
    ultimo.setdefault("call", {})["status"] = "timeout"
    return ultimo


async def una_llamada(client, base_url, workflow, voz, utterances, textos, lleg: dict) -> dict:
    t_inicio = time.time()
    fila = {"paso": lleg["paso"], "concurrencia_obj": lleg["conc"], "t_prog": round(lleg["t"], 3),
            "t_inicio": round(t_inicio, 3), "turnos_plan": lleg["turnos"]}
    try:
        created = await _create_call(client, base_url, workflow, voz)
    except Exception as e:  # noqa: BLE001
        return {"call": {**fila, "call_id": f"sin-crear-{os.getpid()}-{lleg['i']}", "status": "exception",
                         "error": f"{type(e).__name__}: {e}", "t_fin": round(time.time(), 3)}, "turns": []}
    cid, room = created["conversation_id"], created["room"]
    caller = QualityCaller(call_id=cid, room_name=room, livekit_url=config.LIVEKIT_URL,
                           token=_mint_token(room, identity=f"capacity-{cid[:8]}"),
                           utterances=utterances, n_turns=lleg["turnos"], textos=textos)
    await caller.run()
    t_fin = time.time()
    try:
        det = await _detalle_final(client, base_url, cid, timeout=60.0 if caller.greeted else 10.0)
    except httpx.HTTPError as e:
        det = {"call": {"status": "error_api"}}
        caller.error = caller.error or f"{type(e).__name__}: {e}"
    call = det.get("call") or {}
    server = ((call.get("latency") or {}).get("turns")) or []
    usuario = [m.get("text") or "" for m in det.get("messages") or [] if m.get("role") == "user"]
    apareado = len(server) == len(caller.turnos)
    trans_ok = len(usuario) == len(caller.turnos)
    turnos = []
    for i, t in enumerate(caller.turnos):
        st = server[i] if apareado else {}
        hyp = usuario[i] if trans_ok else ""
        turnos.append({
            "call_id": cid, "paso": lleg["paso"], "concurrencia_obj": lleg["conc"], "turno": i,
            "categoria": t.categoria, "texto": t.texto, "transcripcion": hyp,
            "wer": wer(t.texto, hyp) if trans_ok and t.texto else "",
            "t_habla": round(t.t_habla, 3), "t_fin_envio": round(t.t_fin_envio, 3),
            "t_resp": round(t.t_resp, 3) if t.t_resp else "", "t_fin_resp": round(t.t_fin_resp, 3) if t.t_fin_resp else "",
            "espera_s": round(t.t_resp - t.t_fin_envio, 3) if t.t_resp else "",
            "resp_s": round(t.t_fin_resp - t.t_resp, 3) if t.t_fin_resp and t.t_resp else "",
            "cortes_n": len(t.cortes), "cortes_s": round(sum(t.cortes), 3),
            "error": t.error, "pausa_s": round(t.pausa_s, 3), "apareado": int(apareado),
            **{k: ("" if st.get(k) is None else st[k]) for k in SERVER_KEYS},
        })
    # WER de la llamada: sobre todo el texto (sirve aunque no se aparee por turno).
    ref = " ".join(t.texto for t in caller.turnos)
    fila.update({
        "call_id": cid, "t_conectado": round(caller.t_conectado, 3) if caller.t_conectado else "",
        "saludo_s": round(caller.t_saludo - caller.t_conectado, 3) if caller.t_saludo and caller.t_conectado else "",
        "t_fin": round(t_fin, 3), "turnos_cliente": len(caller.turnos), "turnos_server": len(server),
        "turnos_sin_resp": sum(1 for t in caller.turnos if t.t_resp is None),
        "status": call.get("status", "?"), "ended_reason": call.get("ended_reason") or "",
        "error": caller.error or "", "mic_lag_max_s": round(caller.mic_lag_max_s, 3),
        "workflow_status": det.get("workflow_status", ""),
        "outcome": (det.get("outcome") or {}).get("id", "") if isinstance(det.get("outcome"), dict) else (det.get("outcome") or ""),
        "wer": wer(ref, " ".join(usuario)) if ref.strip() else "",
        "cortes": sum(len(t.cortes) for t in caller.turnos),
    })
    return {"call": fila, "turns": turnos}


# ---------- procesos hijos ----------

async def _worker_async(p: dict) -> None:
    utter = {k: [Path(x) for x in v] for k, v in p["utterances"].items()}
    textos = textos_corpus()
    out = open(p["out"], "a", buffering=1)

    async def correr(lleg):
        res = await una_llamada(client, p["base_url"], p["workflow"], p["voz"], utter, textos, lleg)
        out.write(json.dumps(res) + "\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        if p["modo"] == "cerrado":
            # `concurrencia` cadenas, cada una hace sus llamadas una tras otra.
            async def cadena(k):
                for j in range(k, p["llamadas"], p["concurrencia"]):
                    await correr({"paso": p["paso"], "conc": p["concurrencia"], "t": time.time(),
                                  "turnos": p["turnos_llamada"][j], "i": j})
                    await asyncio.sleep(2.0)
            await asyncio.gather(*[cadena(k) for k in range(p["concurrencia"])])
        else:
            tareas = []
            for lleg in p["llegadas"]:
                await asyncio.sleep(max(0.0, lleg["t"] - time.time()))
                tareas.append(asyncio.create_task(correr(lleg)))
            await asyncio.gather(*tareas, return_exceptions=True)
    out.close()


def _worker_entry(p: dict) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_worker_async(p))
    except BaseException as e:  # noqa: BLE001
        with open(p["out"], "a") as f:
            f.write(json.dumps({"worker_error": f"{type(e).__name__}: {e}"}) + "\n")
    # Sin teardown del loop: ver _worker_entry en scripts/loadtest/run.py.
    os._exit(0)


# ---------- cliente: CPU a 1 Hz ----------

class MonitorCliente:
    def __init__(self, path: Path):
        self.f = open(path, "w", newline="", buffering=1)
        self.w = csv.writer(self.f)
        self.w.writerow(["ts", "cpu_pct", "cpu_max_core_pct", "load1", "procesos"])
        self.prev = self._stat()

    @staticmethod
    def _stat():
        d = {}
        for l in open("/proc/stat"):
            if l.startswith("cpu"):
                f = l.split(); v = list(map(int, f[1:9]))
                d[f[0]] = (sum(v), v[3] + v[4])
        return d

    def muestra(self, procesos: int) -> None:
        c = self._stat()
        def busy(k):
            a, b = c[k], self.prev[k]
            return round(100 * (1 - (a[1] - b[1]) / ((a[0] - b[0]) or 1)), 1)
        cores = [busy(k) for k in c if k != "cpu"]
        self.w.writerow([f"{time.time():.1f}", busy("cpu"), max(cores), open("/proc/loadavg").read().split()[0], procesos])
        self.prev = c


# ---------- orquestador ----------

def _lanzar(ctx, p: dict) -> mp.Process:
    pr = ctx.Process(target=_worker_entry, args=(p,))
    pr.start()
    return pr


def _esperar(procs: list[mp.Process], hasta: float, mon: MonitorCliente, etiqueta: str, rundir: Path,
             hasta_que_terminen: bool = False) -> None:
    """Muestrea el cliente hasta `hasta`. Con hasta_que_terminen (escalon en
    serie, drenaje) corta antes, apenas terminan los procesos."""
    ult = 0.0
    while time.time() < hasta:
        vivos = [p for p in procs if p.is_alive()]
        mon.muestra(len(vivos))
        if hasta_que_terminen and not vivos:
            return
        if time.time() - ult >= 30:
            hechas = sum(1 for f in (rundir / "workers").glob("*.jsonl") for _ in open(f))
            print(f"  {time.strftime('%H:%M:%S')} {etiqueta}: {hechas} llamadas terminadas, {len(vivos)} procesos vivos", flush=True)
            ult = time.time()
        time.sleep(max(0.0, 1.0 - time.time() % 1.0))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--perfil", default="rampa", help="nombre en scripts/capacity/perfiles/ o ruta a un .yml")
    ap.add_argument("--base-url", default="http://app:8011", help="URL de la app (default: red de compose)")
    ap.add_argument("--duracion-base", type=float, default=None,
                    help="duracion media de llamada (s); pisa la del perfil")
    ap.add_argument("--base", default=None, help="summary.json de un run `base`: toma de ahi la duracion media")
    ap.add_argument("--seed", type=int, default=None, help="semilla de las llegadas (default: aleatoria, queda en run.json)")
    ap.add_argument("--notas", default="", help="texto libre que va a run.json")
    a = ap.parse_args()

    perfil, perfil_hash = cargar_perfil(a.perfil)
    dur = perfil["duracion_base_s"]
    if a.base:
        dur = json.loads(Path(a.base).read_text()).get("duracion_llamada_s") or dur
    if a.duracion_base:
        dur = a.duracion_base
    seed = a.seed if a.seed is not None else random.randrange(1 << 30)
    rng = random.Random(seed)

    utterances = _load_utterances()
    if {"short", "medium", "long"} - set(utterances):
        raise SystemExit("faltan audios en scripts/loadtest/audio: correr make loadtest-audio")
    _preflight(a.base_url, perfil["workflow"], perfil.get("voz"))

    rundir = RUNS / f"{time.strftime('%Y%m%d_%H%M%S')}_{perfil['nombre']}"
    (rundir / "workers").mkdir(parents=True)
    if HW_CLIENTE.exists():
        shutil.copy(HW_CLIENTE, rundir / "hw_cliente.json")
    else:
        print(f"aviso: no esta {HW_CLIENTE} (la escribe `make capacity` con hwinfo.py): el run queda sin ficha del cliente")

    # Plan de pasos: warm-up (no se mide) + escalones.
    pasos = []
    if perfil.get("warmup_s"):
        pasos.append({"paso": "warmup", "modo": "abierto", "concurrencia": perfil["warmup_concurrencia"],
                      "duracion_s": perfil["warmup_s"]})
    for i, e in enumerate(perfil["escalones"]):
        pasos.append({"paso": f"e{i}_{e['concurrencia']}", "modo": e.get("modo", "abierto"), **e})
    lo, hi = perfil["turnos"]

    run = {"perfil": perfil, "perfil_hash": perfil_hash, "duracion_llamada_s": dur, "seed": seed,
           "base_url": a.base_url, "livekit_url": config.LIVEKIT_URL, "notas": a.notas,
           "inicio": time.time(), "pasos": []}
    (rundir / "run.json").write_text(json.dumps(run, indent=1))
    print(f"run {rundir.name}: perfil {perfil['nombre']} v{perfil.get('version')} ({perfil_hash}), "
          f"duracion media {dur:.0f} s, seed {seed}", flush=True)

    ctx = mp.get_context("spawn")
    mon = MonitorCliente(rundir / "client.csv")
    procs: list[mp.Process] = []
    comun = {"base_url": a.base_url, "workflow": perfil["workflow"], "voz": perfil.get("voz"),
             "utterances": {k: [str(x) for x in v] for k, v in utterances.items()}}
    try:
        for p in pasos:
            t0 = time.time()
            if p["modo"] == "cerrado":
                n = p["llamadas"]
                print(f"\n--- {p['paso']}: {n} llamadas, {p['concurrencia']} a la vez ---", flush=True)
                w = {**comun, **p, "out": str(rundir / "workers" / f"{p['paso']}_w0.jsonl"),
                     "turnos_llamada": [rng.randint(lo, hi) for _ in range(n)]}
                procs.append(_lanzar(ctx, w))
                _esperar([procs[-1]], t0 + n * (hi * 45 + 120), mon, p["paso"], rundir, hasta_que_terminen=True)
                run["pasos"].append({"paso": p["paso"], "t0": t0, "t1": time.time(), "modo": "cerrado",
                                     "concurrencia": p["concurrencia"], "llamadas": n})
                continue
            t1 = t0 + p["duracion_s"]
            lleg = llegadas_poisson(p["concurrencia"], dur, t0 + 1.0, t1, rng)
            nproc = max(1, math.ceil(p["concurrencia"] * 1.3 / CALLERS_POR_PROCESO))
            print(f"\n--- {p['paso']}: concurrencia objetivo {p['concurrencia']}, {len(lleg)} llegadas en "
                  f"{p['duracion_s']} s, {nproc} procesos ---", flush=True)
            for k in range(nproc):
                mias = [{"paso": p["paso"], "conc": p["concurrencia"], "t": t, "turnos": rng.randint(lo, hi), "i": i}
                        for i, t in enumerate(lleg) if i % nproc == k]
                if mias:
                    procs.append(_lanzar(ctx, {**comun, **p, "llegadas": mias,
                                               "out": str(rundir / "workers" / f"{p['paso']}_w{k}.jsonl")}))
            run["pasos"].append({"paso": p["paso"], "t0": t0, "t1": t1, "modo": "abierto",
                                 "concurrencia": p["concurrencia"], "llegadas": len(lleg), "procesos": nproc})
            (rundir / "run.json").write_text(json.dumps(run, indent=1))
            _esperar(procs, t1, mon, p["paso"], rundir)
        # Drenaje: sin llegadas nuevas, dejar cerrar las llamadas en curso (no se mide).
        print(f"\n--- drenaje: esperando las llamadas en curso ---", flush=True)
        run["fin_llegadas"] = time.time()
        _esperar(procs, time.time() + hi * 45 + 180, mon, "drenaje", rundir, hasta_que_terminen=True)
    except KeyboardInterrupt:
        print("\ninterrumpido: se guarda lo medido hasta ahora", flush=True)
    finally:
        for pr in procs:
            if pr.is_alive():
                pr.terminate()
        run["fin"] = time.time()
        (rundir / "run.json").write_text(json.dumps(run, indent=1))
        n = _juntar(rundir)
        print(f"\n{n} llamadas -> {rundir}/calls.csv y turns.csv", flush=True)


def _juntar(rundir: Path) -> int:
    calls, turns, errores = [], [], []
    for f in sorted((rundir / "workers").glob("*.jsonl")):
        for l in open(f):
            d = json.loads(l)
            if "worker_error" in d:
                errores.append(d["worker_error"])
                continue
            calls.append(d["call"]); turns.extend(d["turns"])
    for path, cols, rows in ((rundir / "calls.csv", CALL_COLUMNS, calls), (rundir / "turns.csv", TURN_COLUMNS, turns)):
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in cols})
    if errores:
        print(f"errores de procesos: {sorted(set(errores))[:5]}")
    return len(calls)


if __name__ == "__main__":
    main()
