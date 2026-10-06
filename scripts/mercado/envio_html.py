"""Página local para copiar los mails de una tanda a Gmail con el link como texto.

Lee un `.md` de docs/mercado/envios/ (formato en su README) y genera un HTML con, por empresa,
botones para copiar destinatario, asunto y texto. El texto se copia con formato: el link largo
con UTM queda como "atentina.com.ar" enlazado al pegarlo en Gmail.

Uso: python3 scripts/mercado/envio_html.py docs/mercado/envios/<tanda>.md [...]
Salida: scratch/envios/<tanda>.html (abrir en el navegador).
"""

import html
import re
import sys
from pathlib import Path

LINK = re.compile(r"https://atentina\.com\.ar/\?\S+")
OUT = Path(__file__).resolve().parents[2] / "scratch" / "envios"

PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>{title}</title>
<style>
body {{ font: 15px/1.5 system-ui, sans-serif; background: #f4f6fa; color: #1b2433; margin: 0; padding: 24px 16px; }}
main {{ max-width: 760px; margin: 0 auto; }}
h1 {{ font-size: 20px; }}
section {{ background: #fff; border: 1px solid #dde3ec; border-radius: 10px; padding: 16px 20px; margin: 16px 0; }}
h2 {{ font-size: 16px; margin: 0 0 8px; }}
.row {{ display: flex; gap: 8px; align-items: center; margin: 6px 0; }}
.row code {{ flex: 1; background: #f4f6fa; padding: 4px 8px; border-radius: 6px; }}
.body {{ border: 1px solid #dde3ec; border-radius: 6px; padding: 8px 12px; margin-top: 8px; }}
.body p {{ margin: 0 0 12px; }}
button {{ font: inherit; font-size: 13px; padding: 4px 10px; border: 1px solid #2f5bd3; color: #2f5bd3; background: #fff; border-radius: 6px; cursor: pointer; }}
button.ok {{ background: #2f5bd3; color: #fff; }}
.note {{ color: #5a6577; font-size: 13px; }}
</style></head><body><main>
<h1>{title}</h1>
<p class="note">Copiar destinatario, asunto y texto, y pegar en Gmail. El texto se pega con el link como
"atentina.com.ar". Las respuestas en un hilo ("Re:") se pegan respondiendo el mail original.</p>
{sections}
</main>
<script>
function copy(btn, id, rich) {{
  const el = document.getElementById(id);
  const range = document.createRange();
  range.selectNodeContents(el);
  const sel = window.getSelection();
  sel.removeAllRanges(); sel.addRange(range);
  document.execCommand("copy");
  sel.removeAllRanges();
  btn.classList.add("ok"); btn.textContent = "Copiado";
}}
</script></body></html>
"""


def body_html(text: str) -> str:
    paras = []
    for p in text.split("\n\n"):
        # Se escapa cada tramo una sola vez: escapar el link ya escapado deja "&amp;amp;" en el href.
        out, last = [], 0
        for m in LINK.finditer(p):
            out.append(html.escape(p[last:m.start()]))
            out.append(f'<a href="{html.escape(m.group(0))}">atentina.com.ar</a>')
            last = m.end()
        out.append(html.escape(p[last:]))
        paras.append("<p>" + "".join(out).replace("\n", "<br>") + "</p>")
    return "".join(paras)


def build(md_path: Path) -> Path:
    md = md_path.read_text()
    title = md.splitlines()[0].lstrip("# ").strip()
    out = []
    for i, sec in enumerate(re.split(r"(?m)^(?=## [A-Z]?[0-9-]*[0-9]\. )", md)[1:]):
        name = sec.splitlines()[0][3:]
        get = lambda label: re.search(label + r":\n\n```\n(.*?)\n```", sec, re.S).group(1)
        para, asunto, texto = get("Para"), get("Asunto"), get("Texto")
        out.append(
            f"<section><h2>{html.escape(name)}</h2>"
            f'<div class="row"><code id="p{i}">{html.escape(para)}</code>'
            f'<button onclick="copy(this,\'p{i}\')">Copiar para</button></div>'
            f'<div class="row"><code id="a{i}">{html.escape(asunto)}</code>'
            f'<button onclick="copy(this,\'a{i}\')">Copiar asunto</button></div>'
            f'<div class="body" id="t{i}">{body_html(texto)}</div>'
            f'<div class="row"><button onclick="copy(this,\'t{i}\')">Copiar texto</button></div></section>'
        )
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / (md_path.stem + ".html")
    dest.write_text(PAGE.format(title=html.escape(title), sections="\n".join(out)))
    return dest


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(build(Path(arg)))
