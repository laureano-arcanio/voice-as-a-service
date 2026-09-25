"""Load test de usuario -> livekit agent -> usuario (sin telefonia/SIP).

Dispara N llamadas con POST /calls {"loadtest": true} (como el modo prueba
del dashboard, pero en vez de un humano conectandose por navegador, cada
llamada la atiende un VirtualCaller (caller.py) que publica audio pregenerado
(gen_audio.py) y mide la latencia percibida del lado del cliente). Con
loadtest el agente no corta al completar el workflow: cada llamada dura los
--turns pedidos y la carga es la misma que en EXP-001 a 008. Corre oleadas de
concurrencia creciente y, para cada una, agrega:

  - la latencia percibida por el "usuario" (medida acá, extremo a extremo)
  - el desglose server-side por vertical que loguea app/latency.py
    (eou/stt/endpointing/llm/tts/e2e), leido de call.latency via
    GET /api/calls/{id}. Ver SERVER_COLUMNS por el cambio de ttft_s.

Guarda UNA fila por turno (de cada llamada, de cada oleada) en un CSV bajo
scripts/loadtest/results/ -- esa es la fuente de datos completa; report.html
la lee y arma los graficos/estadisticas.

Los callers se reparten en varios PROCESOS (--callers-per-process): cada uno
mantiene dos streams de audio en tiempo real y un cliente WebRTC, y todo eso
junto satura un solo event loop de asyncio mucho antes de que se sature el
backend (ver comentario largo mas abajo, arriba de _worker_async).

Uso (dentro del contenedor `agent`, que tiene livekit-agents instalado):
    make loadtest                      # niveles/turnos por defecto
    make loadtest ARGS="--levels 1,2,4,8 --turns 3"
    make loadtest ARGS="--levels 24 --turns 4 --callers-per-process 3"

Requiere el corpus de audio ya generado: make loadtest-audio
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import multiprocessing as mp
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

import httpx
from livekit import api

from app import config
from scripts.loadtest.caller import Turn, VirtualCaller

AUDIO_DIR = Path(__file__).resolve().parent / "audio"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Columna del CSV -> clave por turno de app/latency.py (call.latency["turns"]).
# Los nombres de columna son los de EXP-001 a 008, para comparar. Desde el
# motor por workflow el LLM no pasa por el plugin de LiveKit:
#   - ttft_s es "llm": hasta el primer texto de assistant_message, contado
#     desde que el agente arranca el turno. Ademas del TTFT de vLLM incluye la
#     espera de la extraccion del turno anterior (hasta 1,5 s), leer el estado
#     y los tokens del JSON previos al mensaje. El TTFT puro de vLLM sale del
#     sampler (analyze.py).
#   - total_s = eou + llm + tts, igual que antes con ttft.
#   - e2e_s es nuevo: lo que mide LiveKit hasta el primer audio.
#   - llm_tokens y cancelled ya no se registran: quedan vacias.
SERVER_COLUMNS = {
    "eou_s": "eou", "stt_s": "stt", "endpointing_s": "endpointing",
    "ttft_s": "llm", "llm_total_s": "llm_total", "tts_s": "tts",
    "tts_audio_s": "tts_audio", "total_s": "total", "e2e_s": "e2e",
}

CSV_COLUMNS = [
    "run_id", "concurrency", "call_id", "turn_index", "row_kind", "category", "status",
    "call_error", "turn_error", "client_latency_s", "think_time_s",
    "turn_duration_s", "user_speech_s", "turn_start_ts", "turn_end_ts",
    "eou_s", "stt_s", "endpointing_s", "ttft_s", "llm_total_s", "llm_tokens",
    "tts_s", "tts_audio_s", "cancelled", "total_s",
    "call_start_ts", "call_end_ts",
    # Agregadas despues de EXP-008, al final para no correr las anteriores.
    "e2e_s", "workflow_id", "ended_reason",
]

STATS_FIELDS = ("client_latency_s", "think_time_s", "eou_s", "stt_s", "endpointing_s", "ttft_s", "llm_total_s", "tts_s", "total_s", "e2e_s")


def _mint_token(room_name: str, identity: str) -> str:
    return (
        api.AccessToken(config.LIVEKIT_API_KEY, config.LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )


async def _create_call(client: httpx.AsyncClient, base_url: str, workflow_id: str, voice: str | None) -> dict:
    body = {"workflow_id": workflow_id, "loadtest": True}
    if voice:
        body["voice"] = voice
    r = await client.post(f"{base_url}/calls", json=body)
    r.raise_for_status()
    return r.json()


async def _wait_finalized(client: httpx.AsyncClient, base_url: str, call_id: str, timeout: float) -> dict:
    """El registro de la llamada (call de GET /api/calls/{id}) cuando el agente
    la cierra; la latencia por turno se guarda recien ahi."""
    deadline = time.monotonic() + timeout
    status = "?"
    while time.monotonic() < deadline:
        r = await client.get(f"{base_url}/api/calls/{call_id}")
        r.raise_for_status()
        call = r.json().get("call") or {}
        status = call.get("status", "?")
        if status in ("finalizada", "fallida"):
            return call
        await asyncio.sleep(0.5)
    raise TimeoutError(f"call {call_id}: no finalizo a tiempo (status {status})")


_EMPTY_SERVER = {col: "" for col in SERVER_COLUMNS}


def _server_cols(st: dict) -> dict:
    # app/latency.py puede guardar la clave con None explicito (turno al que no
    # le llegaron todas las metricas); en el CSV va vacia, como si faltara.
    return {col: ("" if st.get(key) is None else st[key]) for col, key in SERVER_COLUMNS.items()}


def _rows_for_call(
    run_id: str, concurrency: int, call_id: str, status: str, call_error: str | None,
    turns: list[Turn], server_summary: dict | None,
    call_start_ts: float = 0.0, call_end_ts: float = 0.0,
    workflow_id: str = "", ended_reason: str = "",
) -> list[dict]:
    """Arma las filas del CSV de una llamada.

    Los turnos del cliente (los que dispara este caller) y los del server
    (app/latency.py, leidos de calls.latency_json) NO siempre son la misma
    cantidad: si el VAD del agente parte una frase del usuario en dos, o si
    no llega a reconocer alguna, el server registra mas o menos turnos que los
    que mandamos. Aparearlos ciegamente por indice (lo que se hacia antes)
    pegaba las metricas del server al turno equivocado y ademas descartaba los
    turnos sobrantes.

    Si las cantidades coinciden se aparean (row_kind="paired"); si no,
    se emiten por separado -- las filas del cliente sin columnas de server
    ("client_only") y las del server sin columnas de cliente ("server_only").
    No se pierde ningun dato y no se inventa ningun apareamiento. Las
    estadisticas por columna siguen siendo correctas porque cada metrica vive
    en un solo tipo de fila.
    """
    server_turns = (server_summary or {}).get("turns", [])
    base = {"run_id": run_id, "concurrency": concurrency, "call_id": call_id,
            "status": status, "call_error": call_error or "",
            "workflow_id": workflow_id, "ended_reason": ended_reason,
            # Ventana real en la que esta llamada estuvo viva -- con arranque
            # escalonado la concurrencia nominal del nivel no es la que hubo
            # en simultaneo; con esto se puede calcular el pico real.
            "call_start_ts": round(call_start_ts, 3) if call_start_ts else "",
            "call_end_ts": round(call_end_ts, 3) if call_end_ts else ""}
    empty_client = {"category": "", "turn_error": "", "client_latency_s": "", "think_time_s": "",
                    "turn_start_ts": "", "turn_end_ts": "", "turn_duration_s": "", "user_speech_s": ""}

    def client_cols(t: Turn) -> dict:
        # turn_duration_s: desde que el usuario abre la boca hasta que el
        # agente termina de contestar (NO incluye la pausa de pensar, que va
        # aparte en think_time_s).
        dur = round(t.ended_ts - t.started_ts, 3) if (t.started_ts and t.ended_ts) else ""
        return {
            "category": t.category,
            "turn_error": t.error or "",
            "client_latency_s": t.latency if t.latency is not None else "",
            "think_time_s": t.think_time_s if t.think_time_s is not None else "",
            "turn_start_ts": round(t.started_ts, 3) if t.started_ts else "",
            "turn_end_ts": round(t.ended_ts, 3) if t.ended_ts else "",
            "turn_duration_s": dur,
            "user_speech_s": round(t.speech_s, 3) if t.speech_s else "",
        }

    if not turns and not server_turns:
        return [{**base, "turn_index": "", "row_kind": "client_only", **empty_client, **_EMPTY_SERVER}]

    if len(turns) == len(server_turns):
        return [{**base, "turn_index": i, "row_kind": "paired", **client_cols(t), **_server_cols(st)}
                for i, (t, st) in enumerate(zip(turns, server_turns))]

    rows = [{**base, "turn_index": i, "row_kind": "client_only", **client_cols(t), **_EMPTY_SERVER}
            for i, t in enumerate(turns)]
    rows += [{**base, "turn_index": i, "row_kind": "server_only", **empty_client, **_server_cols(st)}
             for i, st in enumerate(server_turns)]
    return rows


async def _run_one(
    client: httpx.AsyncClient, base_url: str, run_id: str, concurrency: int, n_turns: int,
    utterances: dict[str, list[Path]], start_delay: float, workflow_id: str, voice: str | None,
) -> list[dict]:
    # Arranque escalonado: en trafico real las llamadas no entran todas en el
    # mismo instante. El delay lo calcula el padre a partir del indice GLOBAL
    # del caller (no del indice dentro de su proceso), asi el escalonamiento
    # es parejo entre todos los procesos.
    if start_delay:
        await asyncio.sleep(start_delay)

    call_start_ts = time.time()
    created = await _create_call(client, base_url, workflow_id, voice)
    call_id = created["conversation_id"]
    room_name = created["room"]
    token = _mint_token(room_name, identity=f"loadtest-{call_id[:8]}")

    caller = VirtualCaller(
        call_id=call_id,
        room_name=room_name,
        livekit_url=config.LIVEKIT_URL,
        token=token,
        utterances=utterances,
        n_turns=n_turns,
    )
    result = await caller.run()
    # La llamada termina cuando el caller se desconecta; lo que sigue
    # (esperar a que se finalice en la base) es contabilidad, no carga.
    call_end_ts = time.time()

    # Al cortar, el agente espera la extraccion en curso (hasta 10 s) y guarda.
    # Si nunca saludo, probablemente no tomo el job: la llamada queda en
    # pendiente o sonando y no tiene sentido esperar el minuto entero.
    try:
        call = await _wait_finalized(client, base_url, call_id, timeout=60.0 if result.greeted else 10.0)
    except TimeoutError as e:
        call = {"status": "timeout"}
        result.error = result.error or str(e)

    return _rows_for_call(run_id, concurrency, call_id, call.get("status", "?"), result.error,
                          result.turns, call.get("latency"), call_start_ts, call_end_ts,
                          workflow_id, call.get("ended_reason") or "")


def _stats(vals: list[float]) -> dict | None:
    if not vals:
        return None
    vals = sorted(vals)
    def pct(p):
        i = min(len(vals) - 1, int(len(vals) * p))
        return vals[i]
    return {
        "n": len(vals),
        "avg": round(statistics.fmean(vals), 3),
        "p50": round(pct(0.5), 3),
        "p95": round(pct(0.95), 3),
        "max": round(max(vals), 3),
    }


def _error_row(run_id: str, concurrency: int, call_id: str, error: str) -> dict:
    return {
        "run_id": run_id, "concurrency": concurrency, "call_id": call_id, "status": "exception",
        "call_error": error, "turn_index": "", "row_kind": "client_only", "category": "",
        "turn_error": "", "client_latency_s": "", "think_time_s": "",
        "turn_duration_s": "", "user_speech_s": "", "turn_start_ts": "", "turn_end_ts": "",
        "workflow_id": "", "ended_reason": "",
        **_EMPTY_SERVER,
    }


# ---------- worker: corre en un proceso hijo ----------
# Cada caller mantiene DOS streams de audio en tiempo real (manda su
# microfono cada 20ms y consume el audio del agente), y todo eso mas el
# cliente WebRTC vive en un solo event loop de asyncio (un solo core, con
# GIL). Probado en vivo: hasta ~16 callers en un proceso anda, con 18 el
# event loop se satura tanto que el audio saliente deja de ir en tiempo real,
# el VAD del agente nunca ve un fin de turno limpio y TODAS las llamadas
# quedan trabadas despues del saludo sin generar una sola request al backend.
# Por eso los callers se reparten en varios procesos (--callers-per-process):
# la concurrencia real la da el sistema operativo, no el event loop.

async def _worker_async(
    base_url: str, run_id: str, concurrency: int, n_turns: int, n_callers: int,
    utterances_spec: dict[str, list[str]], start_index: int, stagger_s: float,
    workflow_id: str, voice: str | None,
) -> list[dict]:
    utterances = {k: [Path(p) for p in v] for k, v in utterances_spec.items()}
    async with httpx.AsyncClient(timeout=30.0) as client:
        results = await asyncio.gather(
            *[_run_one(client, base_url, run_id, concurrency, n_turns, utterances,
                       (start_index + j) * stagger_s, workflow_id, voice)
              for j in range(n_callers)],
            return_exceptions=True,
        )
    rows: list[dict] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            rows.append(_error_row(run_id, concurrency, f"error-{os.getpid()}-{i}", f"{type(r).__name__}: {r}"))
        else:
            rows.extend(r)
    return rows


def _worker_entry(payload: dict) -> None:
    out_path = Path(payload.pop("out_path"))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        rows = loop.run_until_complete(_worker_async(**payload))
    except BaseException as e:  # noqa: BLE001
        rows = [_error_row(payload["run_id"], payload["concurrency"], f"worker-{os.getpid()}", f"{type(e).__name__}: {e}")]
    with out_path.open("w") as f:
        json.dump(rows, f)
        f.flush()
        os.fsync(f.fileno())
    # A proposito no se cierra el loop: el bridge FFI de livekit sigue
    # empujando eventos desde su thread de Rust un rato despues, y contra un
    # loop ya cerrado eso escupe "error putting to queue: Event loop is
    # closed" (y en algunos casos un panic de Rust que no se puede catchear).
    # Los resultados ya estan en disco, asi que salimos sin teardown.
    os._exit(0)


def _split_callers(total: int, per_process: int) -> list[int]:
    n_workers = math.ceil(total / per_process)
    base, extra = divmod(total, n_workers)
    return [base + (1 if i < extra else 0) for i in range(n_workers)]


def _run_level(
    base_url: str, run_id: str, concurrency: int, n_turns: int,
    utterances_spec: dict[str, list[str]], per_process: int, tmpdir: Path,
    stagger_s: float, workflow_id: str, voice: str | None,
) -> list[dict]:
    chunks = _split_callers(concurrency, per_process)
    rampa = (concurrency - 1) * stagger_s
    print(f"  ({len(chunks)} procesos: {chunks} callers c/u | arranque escalonado "
          f"cada {stagger_s:g}s, la ultima entra a los {rampa:.1f}s)")
    ctx = mp.get_context("spawn")
    procs = []
    start_index = 0
    for idx, n_callers in enumerate(chunks):
        out_path = tmpdir / f"level{concurrency}_w{idx}.json"
        payload = {
            "base_url": base_url, "run_id": run_id, "concurrency": concurrency,
            "n_turns": n_turns, "n_callers": n_callers,
            "utterances_spec": utterances_spec, "out_path": str(out_path),
            "start_index": start_index, "stagger_s": stagger_s,
            "workflow_id": workflow_id, "voice": voice,
        }
        p = ctx.Process(target=_worker_entry, args=(payload,))
        p.start()
        procs.append((p, out_path, n_callers))
        start_index += n_callers

    # Cota de seguridad por oleada: un turno son, en el peor caso, el audio
    # del usuario + esperar la respuesta completa (reply_timeout) + la pausa
    # de pensar (hasta THINK_TIME_MAX_S), y despues hay que esperar a que la
    # llamada se finalice en la base. Mas la rampa de arranque.
    deadline = time.monotonic() + n_turns * 45 + 180 + rampa
    rows: list[dict] = []
    for i, (p, out_path, n_callers) in enumerate(procs):
        p.join(max(5.0, deadline - time.monotonic()))
        if p.is_alive():
            p.terminate()
            p.join(10)
            rows.extend(_error_row(run_id, concurrency, f"worker{i}-c{j}", "worker colgado: timeout de la oleada")
                        for j in range(n_callers))
            continue
        if out_path.exists():
            rows.extend(json.loads(out_path.read_text()))
        else:
            rows.extend(_error_row(run_id, concurrency, f"worker{i}-c{j}", f"worker murio sin resultados (exitcode={p.exitcode})")
                        for j in range(n_callers))
    return rows


def _peak_concurrency(rows: list[dict]) -> int:
    """Maximo de llamadas vivas al mismo tiempo, contado sobre las ventanas
    reales de cada llamada. Con arranque escalonado la concurrencia NOMINAL
    del nivel no es la que hubo en simultaneo: si la rampa es larga respecto a
    lo que dura una llamada, las primeras terminan antes de que entren las
    ultimas y el pico real queda por debajo."""
    spans = {}
    for r in rows:
        if r.get("call_start_ts") and r.get("call_end_ts"):
            spans[r["call_id"]] = (float(r["call_start_ts"]), float(r["call_end_ts"]))
    # Al empatar timestamps, procesar primero los cierres (-1) para no contar
    # un solapamiento que no existio.
    events = sorted([(s, 1) for s, _ in spans.values()] + [(e, -1) for _, e in spans.values()])
    cur = peak = 0
    for _, delta in events:
        cur += delta
        peak = max(peak, cur)
    return peak


def _fmt_dur(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    return f"{int(seconds // 60)}m {seconds % 60:04.1f}s"


def _print_level(rows: list[dict], concurrency: int, elapsed: float) -> None:
    calls = {r["call_id"] for r in rows}
    failed_calls = {r["call_id"] for r in rows if r["call_error"]}
    print(f"\n=== concurrencia {concurrency} (llamadas ok {len(calls) - len(failed_calls)}/{len(calls)}) "
          f"| oleada: {_fmt_dur(elapsed)} ===")
    errors = sorted({r["call_error"] for r in rows if r["call_error"]})
    if errors:
        print(f"  errores: {errors[:10]}")
    # Llamadas donde el server registro distinta cantidad de turnos que los que
    # mandamos (el VAD del agente partio o se comio alguna frase): sus metricas
    # NO se aparean, van en filas separadas. Ver _rows_for_call.
    unaligned = {r["call_id"] for r in rows if r["row_kind"] in ("client_only", "server_only")}
    if unaligned:
        print(f"  llamadas sin apareamiento cliente/server: {len(unaligned)}/{len(calls)}")
    # Lo normal es customer_hangup (corta el caller). Otra cosa (completed,
    # max duration, job caido) cambia la carga respecto de otros runs.
    reasons: dict[str, int] = {}
    for r in {r["call_id"]: r for r in rows}.values():
        if r.get("ended_reason") and r["ended_reason"] != "customer_hangup":
            reasons[r["ended_reason"]] = reasons.get(r["ended_reason"], 0) + 1
    if reasons:
        print(f"  llamadas cerradas por el agente: {reasons}")
    peak = _peak_concurrency(rows)
    if peak:
        aviso = "  <-- la rampa es larga para lo que dura una llamada" if peak < concurrency else ""
        print(f"  concurrencia REAL (pico simultaneo): {peak}/{concurrency}{aviso}")
    for field in STATS_FIELDS:
        vals = [float(r[field]) for r in rows if r[field] != ""]
        s = _stats(vals)
        if s:
            print(f"  {field:18s}: avg {s['avg']:.2f}s p50 {s['p50']:.2f}s p95 {s['p95']:.2f}s max {s['max']:.2f}s (n={s['n']})")


def _load_utterances() -> dict[str, list[Path]]:
    # categoria = prefijo del archivo (short_00.wav, medium_01.wav, ...), ver
    # gen_audio.py -- VirtualCaller samplea una categoria por turno segun
    # caller.CATEGORY_WEIGHTS (50% cortas / 25% medianas / 25% largas).
    utterances: dict[str, list[Path]] = {}
    for category in ("short", "medium", "long"):
        files = sorted(AUDIO_DIR.glob(f"{category}_*.wav"))
        if files:
            utterances[category] = files
    return utterances


def _preflight(base_url: str, workflow_id: str, voice: str | None) -> None:
    """Falla antes de lanzar la oleada si la app no responde o el workflow o la
    voz no existen: si no, cada llamada fallaria por separado con un 404/422."""
    if not (config.LIVEKIT_URL and config.LIVEKIT_API_KEY and config.LIVEKIT_API_SECRET):
        raise SystemExit("faltan LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET en .env")
    try:
        workflows = {w["id"]: w for w in httpx.get(f"{base_url}/api/workflows", timeout=10).raise_for_status().json()}
    except httpx.HTTPError as e:
        raise SystemExit(f"la app no responde en {base_url} ({e}); levantala con make up-agent")
    if workflow_id not in workflows:
        raise SystemExit(f"workflow {workflow_id!r} inexistente; hay: {sorted(workflows)}")
    if voice and voice not in {v["nombre"] for v in httpx.get(f"{base_url}/api/voices", timeout=10).json()}:
        raise SystemExit(f"voz {voice!r} inexistente (ver tts/finetune/voces.tsv)")
    w = workflows[workflow_id]
    print(f"workflow {workflow_id} (engine {w['engine']}), voz {voice or w['voice'] or 'VLLM_TTS_VOICE'}")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in CSV_COLUMNS})


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://app:8011", help="URL del servicio `app` (default: red interna de compose)")
    p.add_argument("--workflow", default=config.WORKFLOW_ID, help=f"agente (workflow) a llamar (default WORKFLOW_ID: {config.WORKFLOW_ID})")
    p.add_argument("--voice", default=None, help="voz del TTS (default: la del workflow, agent.voice)")
    p.add_argument("--levels", default="1,2,4,8,16", help="niveles de concurrencia, separados por coma")
    p.add_argument("--turns", type=int, default=4, help="turnos de conversacion por llamada")
    p.add_argument("--callers-per-process", type=int, default=4,
                   help="callers por proceso hijo (default 4). Subirlo ahorra procesos pero satura el event loop; ver comentario de arquitectura en el codigo")
    p.add_argument("--stagger", type=float, default=0.25,
                   help="segundos entre el arranque de una llamada y la siguiente (default 0.25; 0 = todas juntas). Ojo: si la rampa supera lo que dura una llamada, el pico simultaneo real queda por debajo del nivel nominal -- el resumen lo reporta")
    args = p.parse_args()

    utterances = _load_utterances()
    missing = [c for c in ("short", "medium", "long") if c not in utterances]
    if missing:
        raise SystemExit(f"faltan categorias de audio {missing} en {AUDIO_DIR} -- corre: make loadtest-audio")
    utterances_spec = {k: [str(p) for p in v] for k, v in utterances.items()}
    _preflight(args.base_url, args.workflow, args.voice)

    run_id = str(int(time.time()))
    levels = [int(x) for x in args.levels.split(",")]
    all_rows: list[dict] = []
    out = RESULTS_DIR / f"loadtest_{run_id}.csv"
    latest = RESULTS_DIR / "latest.csv"

    def dump():
        _write_csv(out, all_rows)
        # El viewer (report.html) busca este nombre fijo por default -- se
        # sobreescribe en cada corrida para no obligar a elegir el archivo a mano.
        _write_csv(latest, all_rows)

    with tempfile.TemporaryDirectory(prefix="loadtest-") as tmp:
        for c in levels:
            print(f"\n--- oleada: {c} llamadas concurrentes, {args.turns} turnos c/u ---", flush=True)
            t0 = time.monotonic()
            try:
                rows = _run_level(args.base_url, run_id, c, args.turns, utterances_spec,
                                  args.callers_per_process, Path(tmp), args.stagger,
                                  args.workflow, args.voice)
            except KeyboardInterrupt:
                # Un sweep largo puede durar bastante; si se corta a mitad, lo
                # ya medido tiene que quedar en disco igual.
                print("\ninterrumpido: guardando lo que se midio hasta ahora", flush=True)
                dump()
                print(f"CSV parcial: {out}  (y {latest})")
                sys.stdout.flush()
                raise
            _print_level(rows, c, time.monotonic() - t0)
            all_rows.extend(rows)
            # Se escribe DESPUES DE CADA OLEADA, no al final: asi una oleada que
            # se cuelga o se corta no se lleva puestos los niveles anteriores
            # (y el reporte se puede ir mirando mientras el sweep sigue).
            dump()

    print(f"\nCSV completo: {out}  (y {latest})")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
