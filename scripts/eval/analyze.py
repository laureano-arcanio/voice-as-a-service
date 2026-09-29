"""Resumen de un run del eval (docs/EVAL_LLM_PLAN.md): summary.json, report.html y
la tabla por consola. Junta conversaciones.jsonl con juez.jsonl si existe.

Uso: make eval-llm-report RUN=scripts/eval/runs/<run> [ARGS="--comparar scripts/eval/runs/<otro>"]
"""
import argparse
import html
import json
import statistics
from pathlib import Path

from .juez import DIMENSIONES, valida


def cargar(rundir: Path) -> tuple[dict, list[dict]]:
    run = json.loads((rundir / "run.json").read_text()) if (rundir / "run.json").exists() else {}
    convs = [json.loads(l) for l in (rundir / "conversaciones.jsonl").read_text().splitlines() if l.strip()]
    juez_path = rundir / "juez.jsonl"
    if juez_path.exists():
        juez = {j["id"]: j for j in (json.loads(l) for l in juez_path.read_text().splitlines() if l.strip())}
        for c in convs:
            c["juez"] = juez.get(c["id"])
    return run, convs


def _pct(xs: list[float], q: float) -> float | None:
    """Percentil con interpolacion lineal (p50 de [500, 700] = 600)."""
    if not xs:
        return None
    xs = sorted(xs)
    pos = q * (len(xs) - 1)
    lo, hi = int(pos), min(int(pos) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (pos - lo), 3)


def _r(x, n=1):
    return None if x is None else round(x, n)


def agregar(convs: list[dict]) -> dict:
    """Metricas agregadas de un conjunto de conversaciones."""
    ch = [c["checks"] for c in convs]
    n = len(ch)
    if not n:
        return {"n": 0}
    datos_total = sum(len(c["datos"]) for c in ch)
    ms = [m for c in ch for m in c.get("llm_turno_ms") or []]
    turnos = sum(c["turnos"] for c in ch)
    por_regla: dict[str, int] = {}
    for c in ch:
        for k, v in c.get("por_regla", {}).items():
            por_regla[k] = por_regla.get(k, 0) + v
    out = {
        "n": n, "errores": sum(bool(c.get("error")) for c in ch),
        "datos_total": datos_total,
        "datos_ok_pct": _r(100 * sum(c["datos_ok"] for c in ch) / datos_total) if datos_total else None,
        "datos_falta": sum(c["datos_falta"] for c in ch), "datos_mal": sum(c["datos_mal"] for c in ch),
        "inventados": sum(len(c["inventados"]) for c in ch),
        "outcome_ok_pct": _r(100 * sum(c["outcome_ok"] for c in ch) / n),
        "termino_pct": _r(100 * sum(c["termino"] for c in ch) / n),
        "turnos_medio": _r(turnos / n), "turnos_total": turnos,
        "repetidas": sum(c["repetidas"] for c in ch), "loops": sum(c["mismo_objetivo"] >= 2 for c in ch),
        "reglas_n": sum(c["reglas_n"] for c in ch),
        "reglas_por_10_turnos": _r(10 * sum(c["reglas_n"] for c in ch) / turnos, 2) if turnos else None,
        "por_regla": dict(sorted(por_regla.items(), key=lambda kv: -kv[1])),
        "largo_medio": _r(statistics.mean(c["largo_medio"] for c in ch if c["largo_medio"]) if any(c["largo_medio"] for c in ch) else 0),
        "audio_max_s": max((c["audio_max_s"] for c in ch), default=0),
        "llm_turno_ms_p50": _pct(ms, 0.5), "llm_turno_ms_p95": _pct(ms, 0.95),
        "problemas": sum(c["problemas"] for c in ch),
    }
    juez = [c["juez"] for c in convs if c.get("juez") and valida(c["juez"])]
    if juez:
        out["juez_n"] = len(juez)
        out["juez_sin_rubrica"] = sum(1 for c in convs if c.get("juez") and not valida(c["juez"]))
        for d in DIMENSIONES:
            vals = [j[d]["puntaje"] for j in juez if isinstance(j.get(d), dict) and isinstance(j[d].get("puntaje"), (int, float))]
            out[f"juez_{d}"] = _r(statistics.mean(vals), 2) if vals else None
        out["juez_alucinaciones"] = sum(len(j.get("alucinaciones") or []) for j in juez)
        out["juez_repreguntas"] = sum(j.get("repreguntas") or 0 for j in juez)
    return out


def por(convs: list[dict], clave) -> dict[str, dict]:
    grupos: dict[str, list] = {}
    for c in convs:
        grupos.setdefault(clave(c), []).append(c)
    return {k: agregar(v) for k, v in sorted(grupos.items())}


def resumen(rundir: Path) -> dict:
    run, convs = cargar(rundir)
    return {
        "run": run, "dir": str(rundir),
        "total": agregar(convs),
        "por_agente": por(convs, lambda c: c["grupo"]),
        "por_persona": por(convs, lambda c: c["persona"]),
        "matriz": {g: por([c for c in convs if c["grupo"] == g], lambda c: c["persona"]) for g in sorted({c["grupo"] for c in convs})},
        "peores": [{"id": c["id"], "problemas": c["checks"]["problemas"], "outcome": c["checks"]["outcome"],
                    "esperado": c["esperado"].get("outcome"), "datos_mal": c["checks"]["datos_mal"],
                    "datos_falta": c["checks"]["datos_falta"], "reglas": c["checks"]["reglas_n"], "error": c["error"]}
                   for c in sorted(convs, key=lambda c: -c["checks"]["problemas"])[:10]],
    }


# ---------- consola ----------

COLS = [("n", "n", "{}"), ("datos_ok_pct", "datos ok%", "{}"), ("datos_mal", "mal", "{}"), ("datos_falta", "falta", "{}"),
        ("outcome_ok_pct", "cierre ok%", "{}"), ("termino_pct", "terminó%", "{}"), ("turnos_medio", "turnos", "{}"),
        ("reglas_por_10_turnos", "reglas/10t", "{}"), ("repetidas", "repet", "{}"), ("loops", "loops", "{}"),
        ("llm_turno_ms_p50", "llm p50", "{}"), ("llm_turno_ms_p95", "p95", "{}"), ("juez_media", "juez", "{}")]


def _juez_media(a: dict):
    vals = [a.get(f"juez_{d}") for d in DIMENSIONES]
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def tabla(filas: dict[str, dict], titulo: str) -> str:
    anchos = [max(len(h), 9) for _, h, _ in COLS]
    out = [f"\n{titulo}", f"{'':18}" + " ".join(h.rjust(w) for (_, h, _), w in zip(COLS, anchos))]
    for nombre, a in filas.items():
        a = {**a, "juez_media": _juez_media(a)}
        out.append(f"{nombre[:18]:18}" + " ".join(("-" if a.get(k) is None else str(a.get(k))).rjust(w) for (k, _, _), w in zip(COLS, anchos)))
    return "\n".join(out)


def imprimir(s: dict) -> None:
    run = s["run"]
    llm = run.get("agente_llm") or {}
    print(f"\n=== {s['dir']}\nagente: {llm.get('model')}  engine: {run.get('engine')}  cliente: {run.get('cliente')}  "
          f"canal: {run.get('canal')}  seed: {run.get('seed')}  git: {run.get('git')}")
    print(tabla({"TOTAL": s["total"]}, "Total"))
    print(tabla(s["por_agente"], "Por agente"))
    print(tabla(s["por_persona"], "Por persona"))
    t = s["total"]
    if t.get("por_regla"):
        print("\nReglas rotas: " + ", ".join(f"{k} {v}" for k, v in t["por_regla"].items()))
    if t.get("juez_n"):
        print("Juez: " + "  ".join(f"{d} {t.get('juez_' + d)}" for d in DIMENSIONES)
              + f"  alucinaciones {t.get('juez_alucinaciones')}  repreguntas {t.get('juez_repreguntas')}")
    print("\nPeores conversaciones:")
    for p in s["peores"]:
        print(f"  {p['id']:38} problemas {p['problemas']:2}  cierre {p['outcome']} (esperado {'/'.join(p['esperado'] or [])})"
              f"  mal {p['datos_mal']} falta {p['datos_falta']} reglas {p['reglas']}{'  ERROR ' + p['error'] if p['error'] else ''}")


def comparar(a: dict, b: dict) -> str:
    """Tabla A contra B: total y por agente."""
    claves = [("datos_ok_pct", "datos ok%"), ("datos_mal", "mal"), ("inventados", "invent"), ("outcome_ok_pct", "cierre ok%"),
              ("termino_pct", "terminó%"), ("turnos_medio", "turnos"), ("reglas_por_10_turnos", "reglas/10t"),
              ("loops", "loops"), ("llm_turno_ms_p50", "llm p50"), ("juez_media", "juez")]
    filas = [("TOTAL", a["total"], b["total"])] + [(g, a["por_agente"].get(g, {}), b["por_agente"].get(g, {}))
                                                   for g in sorted(set(a["por_agente"]) | set(b["por_agente"]))]
    out = [f"\nComparación: A = {Path(a['dir']).name} ({(a['run'].get('agente_llm') or {}).get('model')})  "
           f"B = {Path(b['dir']).name} ({(b['run'].get('agente_llm') or {}).get('model')})",
           f"{'':18}" + "".join(f"{h:>22}" for _, h in claves)]
    for nombre, x, y in filas:
        x, y = {**x, "juez_media": _juez_media(x)}, {**y, "juez_media": _juez_media(y)}
        out.append(f"{nombre[:18]:18}" + "".join(f"{str(x.get(k, '-')):>10} /{str(y.get(k, '-')):>10}" for k, _ in claves))
    return "\n".join(out)


# ---------- html ----------

CSS = """body{font:14px/1.4 system-ui,sans-serif;max-width:1200px;margin:24px auto;padding:0 16px;color:#222}
table{border-collapse:collapse;margin:8px 0 20px;font-size:13px}th,td{border:1px solid #ddd;padding:4px 8px;text-align:right}
th:first-child,td:first-child{text-align:left}th{background:#f3f3f3}h2{margin-top:32px}.ok{color:#2a7}.mal{color:#c33}
details{margin:8px 0;border:1px solid #ddd;padding:6px 10px}summary{cursor:pointer;font-weight:600}
.t{white-space:pre-wrap;font-family:ui-monospace,monospace;font-size:12px;background:#fafafa;padding:8px}
.u{color:#555}.a{color:#124}small{color:#666}"""


def _td(v):
    return "-" if v is None else html.escape(str(v))


def tabla_html(filas: dict[str, dict], titulo: str) -> str:
    head = "".join(f"<th>{h}</th>" for _, h, _ in COLS)
    rows = []
    for nombre, a in filas.items():
        a = {**a, "juez_media": _juez_media(a)}
        rows.append(f"<tr><td>{html.escape(nombre)}</td>" + "".join(f"<td>{_td(a.get(k))}</td>" for k, _, _ in COLS) + "</tr>")
    return f"<h2>{titulo}</h2><table><tr><th></th>{head}</tr>{''.join(rows)}</table>"


def matriz_html(m: dict) -> str:
    personas = sorted({p for g in m.values() for p in g})
    head = "".join(f"<th>{html.escape(p)}</th>" for p in personas)
    rows = []
    for g, por_p in m.items():
        celdas = []
        for p in personas:
            a = por_p.get(p)
            if not a:
                celdas.append("<td>-</td>")
                continue
            cls = "ok" if a["outcome_ok_pct"] == 100 and a["datos_mal"] == 0 else ("mal" if a["outcome_ok_pct"] < 50 or a["datos_mal"] else "")
            celdas.append(f"<td class='{cls}'>cierre {a['outcome_ok_pct']}%<br>datos {a['datos_ok_pct']}%<br><small>reglas {a['reglas_n']}, turnos {a['turnos_medio']}</small></td>")
        rows.append(f"<tr><td>{html.escape(g)}</td>{''.join(celdas)}</tr>")
    return f"<h2>Agente × persona</h2><table><tr><th></th>{head}</tr>{''.join(rows)}</table>"


def conversacion_html(c: dict) -> str:
    ch, j = c["checks"], c.get("juez") or {}
    lineas = []
    for m in c["mensajes"]:
        cls = "a" if m["role"] == "assistant" else "u"
        lineas.append(f"<span class='{cls}'>{'A' if cls == 'a' else 'C'}: {html.escape(m['text'])}</span>")
    reglas = "".join(f"<li>turno {r['turno']}: {html.escape(r['regla'])} — <small>{html.escape(r['texto'])}</small></li>" for r in ch["reglas"])
    juez = ""
    if j and valida(j):
        juez = "<p><b>Juez:</b> " + " · ".join(f"{d} {j.get(d, {}).get('puntaje', '?')}" for d in DIMENSIONES) + \
               f"<br><small>{html.escape(j.get('resumen', ''))}</small>" + \
               (f"<br>alucinaciones: {html.escape('; '.join(j['alucinaciones']))}" if j.get("alucinaciones") else "") + "</p>"
    return (f"<details><summary>{html.escape(c['id'])} — problemas {ch['problemas']}, cierre {ch['outcome']} "
            f"(esperado {'/'.join(c['esperado'].get('outcome') or [])}), datos ok {ch['datos_ok']}/{len(ch['datos'])}, "
            f"reglas {ch['reglas_n']}, {ch['turnos']} turnos{', ERROR' if c['error'] else ''}</summary>"
            f"<p><small>{html.escape(c.get('resumen', ''))}</small></p>"
            f"<p>datos: {html.escape(json.dumps(ch['datos'], ensure_ascii=False))}<br>extraídos: {html.escape(json.dumps(c['fields'], ensure_ascii=False))}"
            f"{'<br>error: ' + html.escape(c['error']) if c['error'] else ''}</p>"
            f"{'<ul>' + reglas + '</ul>' if reglas else ''}{juez}<div class='t'>{'<br>'.join(lineas)}</div></details>")


def report_html(s: dict, convs: list[dict], comp: dict | None = None) -> str:
    run, t = s["run"], s["total"]
    llm = run.get("agente_llm") or {}
    ficha = "".join(f"<tr><td>{k}</td><td style='text-align:left'>{_td(v)}</td></tr>" for k, v in [
        ("fecha", run.get("fecha")), ("agente LLM", f"{llm.get('model')} @ {llm.get('base_url')}"),
        ("thinking / temperatura", f"{llm.get('thinking')} / {llm.get('temperature')}"), ("engine", run.get("engine")),
        ("cliente", f"{run.get('cliente')} {json.dumps(run.get('simulador'), ensure_ascii=False) if run.get('simulador') else ''}"),
        ("canal", run.get("canal")), ("seed / reps", f"{run.get('seed')} / {run.get('reps')}"),
        ("git", run.get("git")), ("workflows", json.dumps(run.get("workflows"), ensure_ascii=False)), ("notas", run.get("notas"))])
    reglas = "".join(f"<li>{html.escape(k)}: {v}</li>" for k, v in (t.get("por_regla") or {}).items())
    juez = ""
    if t.get("juez_n"):
        juez = "<h2>Juez</h2><p>" + " · ".join(f"{d} <b>{t.get('juez_' + d)}</b>" for d in DIMENSIONES) + \
               f"<br>alucinaciones {t.get('juez_alucinaciones')}, repreguntas {t.get('juez_repreguntas')} ({t['juez_n']} conversaciones)</p>"
    peores = "".join(conversacion_html(c) for c in sorted(convs, key=lambda c: -c["checks"]["problemas"]))
    comparacion = f"<h2>Comparación</h2><pre>{html.escape(comparar(s, comp))}</pre>" if comp else ""
    return (f"<!doctype html><html lang='es'><meta charset='utf-8'><title>Eval LLM {html.escape(Path(s['dir']).name)}</title>"
            f"<style>{CSS}</style><body><h1>Eval de calidad del LLM — {html.escape(Path(s['dir']).name)}</h1>"
            f"<table>{ficha}</table>{comparacion}{tabla_html({'TOTAL': t}, 'Total')}{tabla_html(s['por_agente'], 'Por agente')}"
            f"{tabla_html(s['por_persona'], 'Por persona')}{matriz_html(s['matriz'])}"
            f"{'<h2>Reglas de voz rotas</h2><ul>' + reglas + '</ul>' if reglas else ''}{juez}"
            f"<h2>Conversaciones, de peor a mejor</h2>{peores}</body></html>")


def resumir(rundir: Path, comparar_con: Path | None = None) -> dict:
    s = resumen(rundir)
    _, convs = cargar(rundir)
    comp = resumen(comparar_con) if comparar_con else None
    (rundir / "summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1))
    (rundir / "report.html").write_text(report_html(s, convs, comp))
    imprimir(s)
    if comp:
        print(comparar(s, comp))
    print(f"\n-> {rundir / 'summary.json'}\n-> {rundir / 'report.html'}")
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--comparar", default=None, help="otro run, para la tabla A contra B")
    args = ap.parse_args()
    resumir(Path(args.run), Path(args.comparar) if args.comparar else None)


if __name__ == "__main__":
    main()
