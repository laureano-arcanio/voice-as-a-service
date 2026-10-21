"""Manda por Resend los mails de una tanda de docs/mercado/envios/, de a uno, con pausas irregulares.

Lee las secciones `## N.` o `### N.` con Para / Asunto / Texto (formato en envios/README.md) y manda
los primeros `--cantidad` que no salieron todavía. Uno por ventana de `--ventana` segundos (120), en
un momento al azar dentro de cada ventana y con al menos 30 s entre dos mails: el dominio no tiene
reputación y una ráfaga parece spam.

- Hilo: si el historial de Resend (`--hilos`, scratch/resend/emails.json) tiene el 1.er mail a esa
  dirección con el mismo asunto, manda `In-Reply-To` y `References` con su message_id.
- Retoma: lo enviado queda en `<tanda>.enviados.jsonl` (en scratch/envios/); al volver a correr se
  saltea. Un error no corta la tanda: queda en el log y se reintenta en la próxima corrida.
- Antes de cada mail busca la dirección en docs/mercado/blacklist.md.
- Sin `--enviar` solo muestra qué mandaría (prueba en seco).

Uso: python3 scripts/mercado/enviar_seguimientos.py docs/mercado/envios/<tanda>.md [--cantidad 50] [--enviar]
"""

import argparse
import html
import json
import random
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
RESEND_URL = "https://api.resend.com/emails"
LINK = re.compile(r"https://atentina\.com\.ar/\?\S+")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
MIN_GAP = 30


def load_key():
    for line in (ROOT / ".env").read_text().splitlines():
        m = re.match(r"\s*RESEND_API_KEY\s*=\s*(.+)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return ""


def block(sec, label):
    m = re.search(label + r":\n\n```\n(.*?)\n```", sec, re.S)
    return m.group(1) if m else None


def parse(md):
    mails = []
    for sec in re.split(r"(?m)^(?=#{2,3} \d+\. )", md.read_text()):
        m = re.match(r"#{2,3} (\d+)\. (.+)", sec)
        to, subject, text = block(sec, "Para"), block(sec, "Asunto"), block(sec, "Texto")
        if m and to and subject and text:
            mails.append({"n": int(m.group(1)), "empresa": m.group(2).strip(), "to": to.strip(),
                          "subject": subject.strip(), "text": text.strip("\n")})
    return mails


def to_html(text):
    out = []
    for p in text.split("\n\n"):
        seg, last = [], 0
        for m in LINK.finditer(p):
            seg.append(html.escape(p[last:m.start()]))
            seg.append(f'<a href="{html.escape(m.group(0))}">atentina.com.ar</a>')
            last = m.end()
        seg.append(html.escape(p[last:]))
        out.append("<p>" + "".join(seg).replace("\n", "<br>") + "</p>")
    return "".join(out)


def threads(path):
    """Dirección y asunto original -> message_id del último mail con ese asunto."""
    if not path.exists():
        return {}
    out = {}
    for e in sorted(json.loads(path.read_text()), key=lambda e: e["created_at"]):
        if not e.get("message_id"):
            continue
        for r in e["to"]:
            m = EMAIL.search(r.lower())
            if m:
                out[(m.group(0), e["subject"].strip())] = e["message_id"]
    return out


def fmt(s):
    s = max(0, int(s))
    return f"{s // 60}:{s % 60:02d}"


def bar(done, total, width=30):
    k = int(width * done / total) if total else width
    return "[" + "#" * k + "." * (width - k) + f"] {done}/{total}"


def wait_until(t, label):
    tty = sys.stdout.isatty()
    while (left := t - time.time()) > 0:
        if tty:
            print(f"\r    {label}: próximo en {fmt(left)} ", end="", flush=True)
        time.sleep(min(1, left))
    if tty:
        print("\r" + " " * 70 + "\r", end="", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tanda", type=Path)
    ap.add_argument("--cantidad", type=int, default=50)
    ap.add_argument("--ventana", type=int, default=120, help="segundos por mail")
    ap.add_argument("--desde", default="Laureano Arcanio <laureano@atentina.net>")
    ap.add_argument("--hilos", type=Path, default=ROOT / "scratch/resend/emails.json")
    ap.add_argument("--enviar", action="store_true", help="sin esto, prueba en seco")
    args = ap.parse_args()

    log = ROOT / "scratch/envios" / (args.tanda.stem + ".enviados.jsonl")
    sent = set()
    if log.exists():
        for line in log.read_text().splitlines():
            r = json.loads(line)
            if r.get("estado") == "enviado":
                sent.add(r["to"].lower())
    blacklist = set(EMAIL.findall((ROOT / "docs/mercado/blacklist.md").read_text().lower()))
    hilos = threads(args.hilos)

    mails = [m for m in parse(args.tanda) if m["to"].lower() not in sent]
    todo = []
    for m in mails:
        if m["to"].lower() in blacklist:
            print(f"  salteado #{m['n']} {m['empresa']}: {m['to']} está en la blacklist")
            continue
        todo.append(m)
    todo = todo[:args.cantidad]
    if not todo:
        sys.exit("Nada para mandar: todo enviado o salteado.")

    key = load_key()
    if args.enviar and not key:
        sys.exit("No hay RESEND_API_KEY en .env")
    n = len(todo)
    print(f"{'ENVÍO' if args.enviar else 'PRUEBA EN SECO'}: {n} mails desde {args.desde}, "
          f"uno cada {args.ventana} s (~{fmt(n * args.ventana)} en total). Ya enviados antes: {len(sent)}.")

    t0 = time.time()
    last = None
    ok = fail = 0
    for i, m in enumerate(todo):
        orig = re.sub(r"^re:\s*", "", m["subject"], flags=re.I)
        mid = hilos.get((m["to"].lower(), orig))
        hilo = "en el hilo" if mid else "sin hilo"
        if args.enviar:
            start = t0 + i * args.ventana
            at = random.uniform(start, start + args.ventana)
            if last is not None:
                at = max(at, last + MIN_GAP)
            wait_until(at, bar(i, n))
        else:
            print(f"--- #{m['n']} {m['empresa']} | {m['to']} | {m['subject']} | {hilo}\n{m['text']}\n")
            continue
        body = {"from": args.desde, "to": [m["to"]], "subject": m["subject"],
                "text": m["text"], "html": to_html(m["text"])}
        if mid:
            body["headers"] = {"In-Reply-To": mid, "References": mid}
        rec = {"n": m["n"], "empresa": m["empresa"], "to": m["to"], "hora": time.strftime("%Y-%m-%d %H:%M:%S")}
        try:
            r = httpx.post(RESEND_URL, json=body, headers={"Authorization": f"Bearer {key}"}, timeout=20)
            if r.status_code >= 400:
                rec |= {"estado": "error", "detalle": f"{r.status_code} {r.text[:200]}"}
            else:
                rec |= {"estado": "enviado", "id": r.json().get("id"), "hilo": bool(mid)}
        except httpx.HTTPError as e:
            rec |= {"estado": "error", "detalle": str(e)}
        last = time.time()
        with log.open("a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        ok += rec["estado"] == "enviado"
        fail += rec["estado"] == "error"
        eta = t0 + n * args.ventana - time.time()
        marca = "ok   " if rec["estado"] == "enviado" else "ERROR"
        print(f"{bar(i + 1, n)} {time.strftime('%H:%M:%S')} {marca} #{m['n']} {m['empresa'][:40]} <{m['to']}> "
              f"({hilo}){' ' + rec.get('detalle', '') if fail and rec['estado'] == 'error' else ''}"
              f" · falta ~{fmt(eta)}", flush=True)
    if args.enviar:
        print(f"FIN: {ok} enviados, {fail} con error. Log: {log.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
