"""Importacion inicial del CRM (docs/CRM_PLAN.md, seccion 9): una sola vez, por la API.

Lee el seguimiento en Markdown (docs/mercado/seguimiento.md, envios/*.csv y *.md, blacklist.md) y el
historial de Resend, y lo carga en el CRM con la key del usuario. Idempotente: leads por dominio (o
slug), mensajes por resend_id, campanas y plantillas por slug y nombre, actividades por texto.

Uso:
  python3 scripts/mercado/crm_import.py                      # en seco: reporte en scratch/crm/import-report.md
  python3 scripts/mercado/crm_import.py --apply --url http://127.0.0.1:8030 --key $CRM_API_KEY

El historial de Resend se baja con la key completa (scratch/.resend-setup-key) y queda en
scratch/crm/resend-emails.json (con el cuerpo de cada mail, en resend-bodies.json); --refresh los
vuelve a bajar.
"""
import argparse
import collections
import csv
import datetime
import glob
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
MERCADO = ROOT / "docs/mercado"
ENVIOS = MERCADO / "envios"
OUT = ROOT / "scratch/crm"
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
URL = re.compile(r"https?://[^\s)\];,|]+")
PHONE = re.compile(r"\+?\d[\d\s().-]{6,}\d")
MONTHS = {m: i + 1 for i, m in enumerate(
    ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"])}
YEAR = 2026
# Hosts compartidos: no sirven como dominio del lead (dedupe por dominio).
SHARED_HOSTS = {"facebook.com", "instagram.com", "linktr.ee", "linkedin.com", "google.com", "sites.google.com",
                "wixsite.com", "blogspot.com", "wordpress.com", "gmail.com", "hotmail.com", "yahoo.com.ar",
                "yahoo.com", "outlook.com"}
FREE_MAIL = {"gmail.com", "hotmail.com", "yahoo.com", "yahoo.com.ar", "outlook.com", "live.com", "hotmail.com.ar"}
TRANSACTIONAL = re.compile(r"^(Llamada por el link|Llamada de |Activá|Pedido de demo|Tu cuenta|Recibimos tu pago|"
                           r"test|verificar cuenta|Resumen|Te asignamos el n)", re.IGNORECASE)

STAGE_MAP = {"enviado": "contactado", "seguimiento enviado": "seguimiento", "respondió": "respondio",
             "respondio": "respondio", "charla agendada": "charla_agendada", "charla hecha": "charla_hecha",
             "sin respuesta": "sin_respuesta", "no interesa": "no_interesa", "descartado": "descartado",
             "borrador": "nuevo", "follow-up enviado": "respondio", "no acepta": "sin_respuesta", "propuesta": "propuesta", "piloto": "piloto"}

# Campanas: utm_campaign -> (nombre, fecha, archivo de textos del primer mail, segmento).
CAMPAIGNS = {
    "primeros10": ("Primeros 10, uno o dos por rubro (sin UTM)", "2026-10-02", "2026-10-02-primeros-10.md",
                   "Contactos #1 a #11, uno o dos por rubro"),
    "tanda1b": ("Tanda 1, segundo envío con texto de IA", "2026-10-05", "2026-10-05-tanda1-reenvio.md",
                "Contactos #1 a #11, segundo envío al ★"),
    "tanda2": ("Segunda tanda, texto de IA", "2026-10-05", "2026-10-02-segunda-tanda.md", "Contactos #12 a #21"),
    "tanda3": ("Tercera tanda, texto de IA", "2026-10-05", "2026-10-05-tercera-tanda.md", "Contactos #22 a #41"),
    "tanda4": ("Cuarta tanda: mutuales de ayuda económica de Córdoba", "2026-10-05", "2026-10-05-cuarta-tanda-a.md",
               "Mutuales de ayuda económica de Córdoba (#42 a #61)"),
    "tanda5": ("Quinta tanda: mutuales del interior este y sur de Córdoba", "2026-10-05",
               "2026-10-05-quinta-tanda-g1.md", "Mutuales del interior de Córdoba (#62 a #91)"),
    "canales1": ("Canales: aliados (software para mutuales, BPO, contact center)", "2026-10-06",
                 "2026-10-06-canales-a.md", "Aliados, contactos #92 a #111"),
    "canales2": ("Software e IA (partners)", "2026-10-07", "2026-10-07-software-ia-partners.md",
                 "Consultoras e integradores que ya venden IA (#112 a #138)"),
    "canales3": ("Software e IA (partners), tanda 2", "2026-10-08", "2026-10-07-software-ia-partners-2.md",
                 "Partners, #139 a #203 (S41 a S62 el 14-oct, con prueba de asunto «Consulta»)"),
    "canales4": ("Software e IA (partners), tanda 3: «Llamadas de voz»", "2026-10-15",
                 "2026-10-07-software-ia-partners-3.md", "Partners, #204 a #268"),
    "canales5": ("Software con producto propio (ERP, contable, jurídico, agro)", "2026-10-15",
                 "2026-10-15-erp-contable.md", "#272 a #291"),
    "canales6": ("Software con producto propio, tanda 2", "2026-10-15", "2026-10-15-erp-contable-2.md",
                 "#292 a #341 (E1 a E50, por Resend)"),
}
FOLLOW_UP = {
    "name": "Seguimiento: llamada de 5 minutos", "kind": "follow_up", "subject": "(Re: asunto del primer mail)",
    "body": "Hola:\n\n¿Les parece una llamada de 5 minutos? Les cuento la propuesta y ven si vale la pena seguir "
            "hablando.\n\nMás información en {{link}}\n\nSaludos,\nLaureano",
    "body_personal": "{{saludo}}\n\n¿Te parece una llamada de 5 minutos? Te cuento la propuesta y ves si vale la "
                     "pena seguir hablando.\n\nMás información en {{link}}\n\nSaludos,\nLaureano",
}
# Reporte de GA que pego el usuario el 21-oct, fila sin contacto: va como visita sin lead.
GA_EXTRA = [{"date": "2026-10-21", "source_medium": "email / (not set)", "utm_campaign": "(not set)",
             "utm_content": "(not set)", "active_users": 5, "events": 28}]


# --- Utilidades ---

def norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def slugify(text: str) -> str:
    return norm(text).replace(" ", "-")[:60] or "lead"


def domain_of(url: str | None) -> str | None:
    if not url:
        return None
    v = re.sub(r"^[a-z]+://", "", url.strip().lower()).split("/")[0].split("?")[0].split(":")[0]
    v = v.removeprefix("www.")
    return v if "." in v else None


def parse_date(text: str | None) -> str | None:
    """'7-oct-2026', '7-oct', '2026-03-26' -> ISO. El año por defecto es 2026."""
    if not text:
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return m.group(0)
    m = re.search(r"(\d{1,2})-(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\w*(?:-(\d{4}))?", text.lower())
    if m:
        try:
            return datetime.date(int(m.group(3) or YEAR), MONTHS[m.group(2)], int(m.group(1))).isoformat()
        except ValueError:
            return None
    return None


def md_cells(line: str) -> list[str]:
    """Celdas de una fila de tabla Markdown, respetando '\\|' y los '|' dentro de `codigo`."""
    s = line.strip()
    s = s.removeprefix("|")
    s = s.removesuffix("|")
    cells, cur, code = [], "", False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            cur += "|"
            i += 2
            continue
        if ch == "`":
            code = not code
        if ch == "|" and not code:
            cells.append(cur.strip())
            cur = ""
        else:
            cur += ch
        i += 1
    cells.append(cur.strip())
    return cells


def table(lines: list[str], header_start: str) -> list[list[str]]:
    i = next(n for n, l in enumerate(lines) if l.startswith(header_start))
    rows = []
    for l in lines[i + 2:]:
        if not l.startswith("|"):
            break
        rows.append(md_cells(l))
    return rows


def plain(cell: str) -> str:
    """Saca links Markdown y backticks: '[`x`](y)' -> 'x'."""
    c = re.sub(r"\[([^\]]*)\]\(([^)]*)\)", r"\1", cell or "")
    return c.replace("`", "").replace("**", "").strip()


def empty(cell: str | None) -> bool:
    return not cell or cell.strip() in ("—", "-", "")


# --- Lectura del Markdown y los CSV ---

class Plan:
    def __init__(self):
        self.leads: dict[str, dict] = {}     # legacy_ref -> lead (payload del upsert)
        self.by_email: dict[str, str] = {}   # email -> legacy_ref
        self.by_domain: dict[str, str] = {}
        self.by_name: dict[str, str] = {}
        self.campaign_of: dict[str, str] = {}
        self.activities: list[tuple[str, dict]] = []
        self.blocks: list[dict] = []
        self.dnc: set[str] = set()
        self.ga: list[dict] = list(GA_EXTRA)
        self.templates: list[dict] = []
        self.messages: list[dict] = []
        self.problems: list[str] = []
        self.notes: list[str] = []

    def add_email(self, ref: str, email: str) -> None:
        self.by_email.setdefault(email.lower(), ref)


def read_contacts(plan: Plan, lines: list[str]) -> None:
    for c in table(lines, "| # | Empresa | Rubro, lugar | Tipo | Email |"):
        if len(c) == 12 and "" in c[6:9]:
            c.pop(c.index("", 6))       # "||" de mas (fila #271)
        if len(c) != 11:
            plan.problems.append(f"Contactos: fila con {len(c)} celdas: {c[:2]}")
            continue
        ref, name, rubro, tipo, email, web, first, fu, resp, estado, nxt = c
        ref = ref.lstrip("#")
        emails = EMAIL.findall(email)
        site = (URL.findall(web) or [None])[0] or (None if empty(web) else "https://" + plain(web).strip("/"))
        stage = STAGE_MAP.get(plain(estado).lower())
        if not stage:
            plan.problems.append(f"#{ref} {name}: estado desconocido {estado!r} (queda nuevo)")
            stage = "nuevo"
        lead = {"legacy_ref": ref, "name": plain(name), "website": site, "description": plain(rubro),
                "kind": "canal" if "canal" in tipo.lower() else "cliente" if "cliente" in tipo.lower() else None,
                "stage": stage, "next_action": None if empty(nxt) else plain(nxt), "tags": [], "contacts": [],
                "people": [], "sources": [], "_notes": [], "_resp": None if empty(resp) else plain(resp),
                "_first": plain(first), "_fu": plain(fu), "_md_stage": plain(estado)}
        for i, e in enumerate(emails):
            lead["contacts"].append({"kind": "email", "value": e.lower(), "is_primary": i == 0})
            plan.add_email(ref, e)
        plan.leads[ref] = lead
        plan.by_name.setdefault(norm(lead["name"]), ref)


def read_utm(plan: Plan, lines: list[str]) -> None:
    for c in table(lines, "| # | Empresa | utm_campaign | utm_content |"):
        ref = c[0].lstrip("#")
        if ref in plan.leads:
            plan.leads[ref]["slug"] = c[3]
            plan.campaign_of[ref] = c[2]
            plan.leads[ref]["tags"].append(c[2])
        else:
            plan.problems.append(f"Links con UTM: #{ref} no está en Contactos")


def assign_domains(plan: Plan) -> None:
    seen: dict[str, str] = {}
    for ref, lead in plan.leads.items():
        d = domain_of(lead.get("website"))
        if d and (d in SHARED_HOSTS or any(d.endswith("." + h) for h in SHARED_HOSTS)):
            d = None    # el CRM lo guarda como web sin dominio (dedupe por slug)
        if d and d in seen:
            plan.problems.append(f"#{ref} {lead['name']}: mismo dominio que #{seen[d]} ({d}); la web va a notas")
            lead["_notes"].append(f"Web: {lead['website']} (mismo dominio que #{seen[d]})")
            lead["website"] = None
            d = None
        if d:
            seen[d] = ref
            plan.by_domain[d] = ref
        if not lead.get("slug"):
            lead["slug"] = slugify(lead["name"])


def find_lead(plan: Plan, *, emails=(), web=None, name=None) -> str | None:
    for e in emails:
        if e.lower() in plan.by_email:
            return plan.by_email[e.lower()]
    d = domain_of(web)
    if d and d in plan.by_domain:
        return plan.by_domain[d]
    for e in emails:
        dom = e.split("@")[-1].lower()
        if dom not in FREE_MAIL and dom in plan.by_domain:
            return plan.by_domain[dom]
    if name and norm(name) in plan.by_name:
        return plan.by_name[norm(name)]
    return None


def label_of(tipo: str) -> str | None:
    t = norm(tipo)
    return "persona" if t.startswith("persona") else "area" if t.startswith("area") else \
        "atencion" if t.startswith("atencion") else None


def found_emails(text: str) -> list[dict]:
    """'a@b (persona, Nombre, cargo, https://x (7-oct-2026)); c@d (atención, ...)' -> lista."""
    out = []
    for m in re.finditer(r"([\w.+-]+@[\w-]+(?:\.[\w-]+)+)\s*\(", text or ""):
        depth, j = 1, m.end()
        while j < len(text) and depth:
            depth += {"(": 1, ")": -1}.get(text[j], 0)
            j += 1
        inner = text[m.end():j - 1]
        parts = [p.strip() for p in inner.split(",")]
        url = (URL.findall(inner) or [None])[0]
        person = None
        if label_of(parts[0]) == "persona" and len(parts) > 1 and not parts[1].startswith("http"):
            person = parts[1]
            title = parts[2] if len(parts) > 2 and not parts[2].startswith("http") and not parse_date(parts[2]) else None
        else:
            title = None
        out.append({"email": m.group(1).lower(), "label": label_of(parts[0]), "person": person, "title": title,
                    "url": url, "date": parse_date(inner)})
    return out


def read_csvs(plan: Plan) -> None:
    for f in sorted(glob.glob(str(ENVIOS / "*.csv"))):
        name = Path(f).name
        if "linkedin-salud" in name:
            plan.notes.append(f"{name}: cuentas de LinkedIn sin contactar, no se importan")
            continue
        with open(f, encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        for row in rows:
            row = {k: (v or "").strip() for k, v in row.items() if k}
            emails = EMAIL.findall(row.get("email", "") + " " + row.get("emails_encontrados", ""))
            ref = find_lead(plan, emails=emails, web=row.get("web"), name=row.get("empresa"))
            if not ref:
                plan.notes.append(f"{name} {row.get('n')} {row.get('empresa')}: sin contacto en el seguimiento (no se envió)")
                continue
            lead = plan.leads[ref]
            src_url = (URL.findall(row.get("url_donde_figura_el_email", "")) or [None])[0]
            src_date = parse_date(row.get("fuente_fecha"))
            if src_url:
                lead["sources"].append({"url": src_url, "seen_at": src_date, "note": row.get("fuente_fecha")[:300] or None})
            for u in URL.findall(row.get("fuente_fecha", "")):
                lead["sources"].append({"url": u, "seen_at": parse_date(row["fuente_fecha"])})
            if row.get("ciudad_provincia"):
                city, _, prov = row["ciudad_provincia"].partition(",")
                prov = prov.strip() or (re.search(r"\(([^)]+)\)", city) or [None, None])[1]
                lead["city"] = re.sub(r"\s*\([^)]*\)", "", city).strip() or None
                lead["province"] = prov
            if row.get("pais"):
                lead["country"] = row["pais"]
            if row.get("rubro") and not lead.get("industry"):
                lead["industry"] = row["rubro"][:100]
            for k, label in (("por_que_encaja", "Por qué encaja"), ("gancho", "Gancho")):
                if row.get(k) and row[k] not in ("—", "-"):
                    lead["_notes"].append(f"{label}: {row[k]}")
            # Persona del email principal
            if norm(row.get("email_tipo", "")).startswith("persona") and row.get("contacto_nombre_cargo"):
                pname, _, ptitle = row["contacto_nombre_cargo"].partition(",")
                lead["people"].append({"name": pname.strip(), "title": ptitle.strip() or None,
                                       "is_decision_maker": True, "source_url": src_url, "source_seen_at": src_date})
                for c in lead["contacts"]:
                    if c["value"] == row.get("email", "").lower():
                        c["person"], c["label"] = pname.strip(), "persona"
            for e in found_emails(row.get("emails_encontrados", "")):
                c = {"kind": "email", "value": e["email"], "label": e["label"], "source_url": e["url"] or src_url,
                     "source_seen_at": e["date"]}
                if e["person"]:
                    c["person"] = e["person"]
                    lead["people"].append({"name": e["person"], "title": e["title"], "source_url": e["url"],
                                           "source_seen_at": e["date"]})
                lead["contacts"].append(c)
                plan.add_email(ref, e["email"])
            for col, kind in (("telefonos", "phone"), ("whatsapp", "whatsapp")):
                for ph in PHONE.findall(re.sub(r"https?://\S+", "", row.get(col, ""))):
                    if len(re.sub(r"\D", "", ph)) >= 8:
                        lead["contacts"].append({"kind": kind, "value": ph.strip(), "source_url": src_url or lead.get("website")})
            for col in ("linkedin", "linkedin_persona"):
                for u in URL.findall(row.get(col, "")):
                    lead["contacts"].append({"kind": "linkedin", "value": u.rstrip(".")})
            for u in URL.findall(row.get("formulario", "")):
                lead["contacts"].append({"kind": "form", "value": u})


def read_blacklist(plan: Plan) -> None:
    lines = (MERCADO / "blacklist.md").read_text().split("\n")
    for c in table(lines, "| # | Empresa | Email | Rebotó"):
        for e in EMAIL.findall(c[2]):
            plan.blocks.append({"value": e.lower(), "reason": "bounce", "note": f"#{c[0]} {plain(c[1])}: rebotó ({c[3]})"})
    for c in table(lines, "| # | Empresa | Email | Motivo"):
        ref = c[0].lstrip("#")
        emails = EMAIL.findall(c[2])
        if "todas" in c[2] or not emails:
            plan.dnc.add(ref)
        for e in emails:
            plan.blocks.append({"value": e.lower(), "reason": "opt_out", "note": f"#{ref}: {c[3]}"})


def read_ga(plan: Plan, lines: list[str]) -> None:
    """Las filas son acumulados por fecha de reporte: por (campana, contenido) va solo la mas reciente."""
    rows = {}
    for c in table(lines, "| # | Empresa | Campaña / contenido | Usuarios |"):
        camp, _, content = plain(c[2]).partition("/")
        camp, content = camp.strip(), content.strip()
        medium = "email / organic" if "organic" in content else "email / (not set)"
        content = content.split()[0] if content else content
        users = int(re.sub(r"\D", "", c[3]) or 0)
        second = int(re.sub(r"\D", "", c[4]) or 0)
        is_events = "ev" in c[4]
        date = parse_date(c[5])
        if not date:
            plan.problems.append(f"GA: fila sin fecha {c[:3]}")
            continue
        row = {"date": date, "source_medium": medium, "utm_campaign": camp, "utm_content": content,
               "active_users": users, "sessions": 0 if is_events else second, "events": second if is_events else 0}
        key = (camp, content, medium)
        if key not in rows or rows[key]["date"] < date:
            rows[key] = row
    plan.ga += rows.values()


def read_conversations(plan: Plan, text: str) -> None:
    sec = text.split("\n## Conversaciones", 1)[1].split("\n## ", 1)[0]
    for m in re.finditer(r"^### (.+?)\n(.*?)(?=^### |\Z)", sec, re.MULTILINE | re.DOTALL):
        head, body = m.group(1), m.group(2).strip()
        ref = re.search(r"\(#(\d+)\)", head)
        if not ref or ref.group(1) not in plan.leads:
            if "<fecha>" not in head:
                plan.problems.append(f"Conversación sin contacto: {head}")
            continue
        date = parse_date(head) or "2026-10-09"
        plan.activities.append((ref.group(1), {"kind": "meeting", "text": f"{head}\n\n{body}",
                                               "at": f"{date}T12:00:00-03:00"}))


def read_linkedin(plan: Plan, lines: list[str]) -> None:
    for c in table(lines, "| # | Empresa | Rubro, lugar | Tipo | Persona, cargo |"):
        lref, empresa, rubro, tipo, persona, _vinculo, perfil, _, sent, fu, resp, estado, nxt = (c + [""] * 13)[:13]
        mention = re.search(r"#(\d+)", nxt)
        ref = (mention.group(1) if mention and mention.group(1) in plan.leads else None) or \
            find_lead(plan, name=plain(empresa))
        text = (f"LinkedIn {lref}: {plain(persona) if not empty(persona) else 'página de la empresa'}"
                f" · estado {plain(estado)} · enviado {plain(sent)} · seguimiento {plain(fu)}"
                f"{' · respuesta: ' + plain(resp) if not empty(resp) else ''} · próxima acción: {plain(nxt)}")
        if not ref:
            ref = lref
            plan.leads[ref] = {"legacy_ref": lref, "name": plain(empresa), "slug": slugify(plain(empresa)),
                               "description": plain(rubro), "kind": "canal" if "canal" in tipo else "cliente",
                               "stage": STAGE_MAP.get(plain(estado).lower(), "nuevo"), "tags": ["linkedin"],
                               "contacts": [], "people": [], "sources": [], "_notes": [], "_resp": None,
                               "next_action": None if empty(nxt) else plain(nxt)}
            plan.by_name.setdefault(norm(plain(empresa)), ref)
        lead = plan.leads[ref]
        if "linkedin" not in lead["tags"]:
            lead["tags"].append("linkedin")
        if not empty(persona):
            pname, _, title = plain(persona).partition(",")
            lead["people"].append({"name": re.sub(r"\s*\(.*?\)", "", pname).strip(), "title": title.strip() or None,
                                   "linkedin_url": (URL.findall(perfil) or [None])[0]})
        for u in URL.findall(perfil):
            lead["contacts"].append({"kind": "linkedin", "value": u})
        at = parse_date(sent) or "2026-10-06"
        plan.activities.append((ref, {"kind": "linkedin", "text": text, "at": f"{at}T12:00:00-03:00"}))


def read_templates(plan: Plan) -> None:
    for slug, (name, date, md, _) in CAMPAIGNS.items():
        path = ENVIOS / md
        if not path.exists():
            plan.problems.append(f"Plantilla {slug}: falta {md}")
            continue
        text = path.read_text()
        sec = next((s for s in re.split(r"\n## ", text)
                    if "Texto:\n\n```" in s and "Asunto:\n\n```" in s), None)
        if not sec:
            plan.problems.append(f"Plantilla {slug}: {md} sin bloques Asunto/Texto")
            continue
        empresa = re.match(r"[\w-]+\.\s*(.+)", sec.split("\n")[0])
        empresa = empresa.group(1).strip() if empresa else ""
        subj = re.search(r"Asunto:\n\n```\n(.*?)\n```", sec, re.DOTALL).group(1).strip()
        body = re.search(r"Texto:\n\n```\n(.*?)\n```", sec, re.DOTALL).group(1).strip()
        body = re.sub(r"https://atentina\.com\.ar/\?\S+|https://atentina\.com\.ar/?", "{{link}}", body)
        lines = body.split("\n")
        if lines and lines[0].lower().startswith("hola"):
            lines[0] = "{{saludo}}"
        body = "\n".join(lines)
        short = re.sub(r"\s*\(.*?\)", "", empresa).strip()
        for n in {empresa, short} - {""}:
            body, subj = body.replace(n, "{{empresa}}"), subj.replace(n, "{{empresa}}")
        plan.templates.append({"name": f"{slug}: primer mail ({date})", "kind": "first", "subject": subj,
                               "body": body + f"\n\n(Modelo armado con el texto enviado a {empresa}; el resto de la "
                                              f"tanda tenía una frase propia por empresa.)",
                               "archived": date < "2026-10-15"})
    plan.templates.append(FOLLOW_UP)


# --- Resend ---

def resend_key() -> str:
    return (ROOT / "scratch/.resend-setup-key").read_text().strip().replace('"', "").removeprefix("RESEND_API_KEY=")


def resend_history(refresh: bool) -> list[dict]:
    OUT.mkdir(parents=True, exist_ok=True)
    cache = OUT / "resend-emails.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text())
    h = {"Authorization": f"Bearer {resend_key()}", "User-Agent": "atentina-crm-import"}
    out, after = [], None
    while True:
        r = httpx.get("https://api.resend.com/emails?limit=100" + (f"&after={after}" if after else ""), headers=h,
                      timeout=30)
        r.raise_for_status()
        d = r.json()
        out += d["data"]
        if not d.get("has_more") or not d["data"]:
            break
        after = d["data"][-1]["id"]
        time.sleep(0.6)
    cache.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def resend_bodies(ids: list[str], refresh: bool) -> dict[str, str]:
    """Texto de cada mail (GET /emails/{id}); ~2 pedidos por segundo, con cache."""
    cache = OUT / "resend-bodies.json"
    bodies = {} if refresh or not cache.exists() else json.loads(cache.read_text())
    todo = [i for i in ids if i not in bodies]
    h = {"Authorization": f"Bearer {resend_key()}", "User-Agent": "atentina-crm-import"}
    for n, rid in enumerate(todo):
        r = httpx.get(f"https://api.resend.com/emails/{rid}", headers=h, timeout=30)
        if r.status_code == 429:
            time.sleep(2)
            r = httpx.get(f"https://api.resend.com/emails/{rid}", headers=h, timeout=30)
        if r.status_code < 400:
            d = r.json()
            text = d.get("text") or re.sub(r"<[^>]+>", "", (d.get("html") or "").replace("</p>", "\n\n")
                                           .replace("<br>", "\n")).strip()
            bodies[rid] = text
        if n % 50 == 49:
            cache.write_text(json.dumps(bodies, ensure_ascii=False))
            print(f"  cuerpos de Resend: {n + 1}/{len(todo)}", file=sys.stderr)
        time.sleep(0.55)
    cache.write_text(json.dumps(bodies, ensure_ascii=False))
    return bodies


STATUS = {"delivered": "delivered", "bounced": "bounced", "suppressed": "bounced", "complained": "complained",
          "failed": "failed", "opened": "delivered", "clicked": "delivered", "sent": "sent",
          "delivery_delayed": "sent", "queued": "sent"}


def read_resend(plan: Plan, emails: list[dict], bodies: dict[str, str]) -> None:
    for e in sorted(emails, key=lambda x: x["created_at"]):
        if TRANSACTIONAL.match(e["subject"] or "") or "web@" in e["from"]:
            continue
        to = EMAIL.search(" ".join(e["to"]).lower())
        to = to.group(0) if to else ""
        ref = find_lead(plan, emails=[to])
        if not ref:
            plan.problems.append(f"Resend sin lead: {e['created_at'][:16]} {to} «{e['subject'][:60]}»")
            continue
        sent_at = e["created_at"].replace(" ", "T").split(".")[0] + "Z"
        kind = "follow_up" if re.match(r"^re:", e["subject"] or "", re.IGNORECASE) else "first"
        # Otro mail suelto (no "Re:") mas de 2 dias despues del primero: no es un primer mail.
        prev = [m for m in plan.messages if m["_ref"] == ref and m["kind"] == "first"]
        if kind == "first" and prev and sent_at[:10] > (datetime.date.fromisoformat(prev[0]["sent_at"][:10])
                                                         + datetime.timedelta(days=2)).isoformat():
            kind = "other"
        camp = plan.campaign_of.get(ref)
        if ref.isdigit() and int(ref) <= 11 and sent_at < "2026-10-03":
            camp = "primeros10"
        plan.messages.append({"_ref": ref, "_campaign": camp, "kind": kind, "direction": "out",
                              "from_addr": e["from"], "to_addr": to, "subject": e["subject"] or "(sin asunto)",
                              "text": bodies.get(e["id"], ""), "status": STATUS.get(e.get("last_event"), "sent"),
                              "resend_id": e["id"], "message_id": e.get("message_id"), "sent_at": sent_at,
                              "utm_campaign": None})


def stages_from_resend(plan: Plan) -> list[str]:
    """Resend manda: un seguimiento que salio sube la etapa de `contactado` a `seguimiento`."""
    out = []
    fu = {m["_ref"] for m in plan.messages if m["kind"] == "follow_up" and m["status"] != "bounced"}
    for ref in sorted(fu, key=lambda x: (len(x), x)):
        lead = plan.leads[ref]
        if lead["stage"] in ("nuevo", "contactado"):
            out.append(f"#{ref} {lead['name']}: {lead['stage']} -> seguimiento (hay «Re:» en Resend)")
            lead["stage"] = "seguimiento"
    return out


def stage_diffs(plan: Plan) -> list[str]:
    out = []
    by = collections.defaultdict(list)
    for m in plan.messages:
        by[m["_ref"]].append(m)
    for ref, lead in plan.leads.items():
        if ref.startswith("L"):
            continue
        msgs = by.get(ref, [])
        fus = [m for m in msgs if m["kind"] == "follow_up"]
        st = lead["stage"]
        if st in ("contactado", "seguimiento") and not msgs:
            out.append(f"#{ref} {lead['name']}: «{lead['_md_stage']}» en el .md, sin ningún mail en Resend")
        elif st == "seguimiento" and not fus:
            out.append(f"#{ref} {lead['name']}: «seguimiento enviado» en el .md, sin «Re:» en Resend")
        elif lead.get("_md_stage") == "enviado" and fus:
            out.append(f"#{ref} {lead['name']}: «enviado» en el .md, pero Resend tiene {len(fus)} «Re:» "
                       f"({', '.join(m['sent_at'][:10] for m in fus)})")
        firsts = [m for m in msgs if m["kind"] == "first"]
        if len(firsts) > 1:
            out.append(f"#{ref} {lead['name']}: {len(firsts)} primeros mails en Resend "
                       f"({'; '.join(m['sent_at'][:10] + ' «' + m['subject'][:30] + '»' for m in firsts)})")
        bounced = [m for m in msgs if m["status"] == "bounced"]
        if bounced and st not in ("descartado",):
            out.append(f"#{ref} {lead['name']}: rebotó {', '.join(sorted({m['to_addr'] for m in bounced}))} "
                       f"(etapa en el .md: {lead['_md_stage']}; al importar, si no queda otro email, pasa a descartado)")
    return out


def build(refresh: bool, bodies: bool) -> Plan:
    plan = Plan()
    text = (MERCADO / "seguimiento.md").read_text()
    lines = text.split("\n")
    read_contacts(plan, lines)
    read_utm(plan, lines)
    assign_domains(plan)
    read_csvs(plan)
    read_blacklist(plan)
    read_ga(plan, lines)
    read_conversations(plan, text)
    read_linkedin(plan, lines)
    read_templates(plan)
    emails = resend_history(refresh)
    commercial = [e["id"] for e in emails if not TRANSACTIONAL.match(e["subject"] or "") and "web@" not in e["from"]]
    read_resend(plan, emails, resend_bodies(commercial, refresh) if bodies else {})
    for ref, lead in plan.leads.items():
        if lead.get("_resp"):
            at = parse_date(lead["_resp"]) or "2026-10-15"
            plan.activities.append((ref, {"kind": "note", "text": f"Respuesta (del seguimiento.md): {lead['_resp']}",
                                          "at": f"{at}T12:00:00-03:00"}))
        if ref in plan.dnc:
            lead["do_not_contact"] = True
    return plan


def payload(lead: dict) -> dict:
    p = {k: v for k, v in lead.items() if not k.startswith("_") and v not in (None, [], "")}
    # Contactos sin duplicados (el primero gana; el ★ se conserva).
    seen, contacts = {}, []
    for c in lead["contacts"]:
        key = (c["kind"], c["value"].lower() if c["kind"] == "email" else re.sub(r"\D", "", c["value"])
               if c["kind"] in ("phone", "whatsapp") else c["value"])
        if key in seen:
            prev = seen[key]
            for k, v in c.items():
                if v and not prev.get(k):
                    prev[k] = v
            continue
        c = {k: v for k, v in c.items() if v not in (None, "")}
        seen[key] = c
        contacts.append(c)
    p["contacts"] = contacts
    people, names = [], set()
    for x in lead["people"]:
        if x["name"] and norm(x["name"]) not in names and len(x["name"]) < 120:
            names.add(norm(x["name"]))
            people.append({k: v for k, v in x.items() if v not in (None, "")})
    p["people"] = people
    srcs, urls = [], set()
    for x in lead["sources"]:
        if x["url"] not in urls:
            urls.add(x["url"])
            srcs.append({k: v for k, v in x.items() if v not in (None, "")})
    p["sources"] = srcs
    if lead["_notes"]:
        p["notes"] = "\n".join(dict.fromkeys(lead["_notes"]))
    p["tags"] = sorted(set(lead["tags"]))
    return p


# --- Reporte y carga ---

def report(plan: Plan, diffs: list[str]) -> str:
    leads = [payload(x) for x in plan.leads.values()]
    no_email = [f"#{x['legacy_ref']} {x['name']}" for x in leads
                if not any(c["kind"] == "email" for c in x["contacts"])]
    lines = [
        f"# Importación del CRM: reporte ({datetime.datetime.now(datetime.UTC):%Y-%m-%d %H:%M} UTC)", "",
        "| Qué | Cantidad |", "|---|---|",
        (f"| Leads | {len(leads)} (de Contactos {sum(1 for r in plan.leads if not r.startswith('L'))}, "
         f"solo LinkedIn {sum(1 for r in plan.leads if r.startswith('L'))}) |"),
        f"| Personas | {sum(len(x['people']) for x in leads)} |",
        (f"| Contactos | {sum(len(x['contacts']) for x in leads)} "
         f"({dict(collections.Counter(c['kind'] for x in leads for c in x['contacts']))}) |"),
        f"| Fuentes | {sum(len(x['sources']) for x in leads)} |",
        f"| Campañas | {len(CAMPAIGNS)} |", f"| Plantillas | {len(plan.templates)} |",
        (f"| Mensajes (Resend) | {len(plan.messages)} "
         f"({dict(collections.Counter(m['kind'] + '/' + m['status'] for m in plan.messages))}) |"),
        f"| Mensajes con cuerpo | {sum(1 for m in plan.messages if m['text'])} |",
        f"| Blocklist | {len(plan.blocks)} |", f"| No contactar | {len(plan.dnc)} |",
        f"| Visitas GA | {len(plan.ga)} |",
        f"| Actividades | {len(plan.activities)} ({dict(collections.Counter(a['kind'] for _, a in plan.activities))}) |",
        f"| Etapas (del .md, con los seguimientos de Resend) | {dict(collections.Counter(x['stage'] for x in leads))} |", "",
        f"## Leads sin email ({len(no_email)})", "", *[f"- {x}" for x in no_email], "",
        f"## Diferencias entre el .md y Resend ({len(diffs)})", "", *[f"- {x}" for x in diffs], "",
        f"## Problemas ({len(plan.problems)})", "", *[f"- {x}" for x in plan.problems], "",
        f"## Notas ({len(plan.notes)})", "", *[f"- {x}" for x in plan.notes], ""]
    return "\n".join(lines)


class Api:
    def __init__(self, url: str, key: str):
        self.c = httpx.Client(base_url=url.rstrip("/") + "/api", headers={"Authorization": f"Bearer {key}"},
                              timeout=60)

    def call(self, method: str, path: str, ok=(200, 201, 204), **kw):
        r = self.c.request(method, path, **kw)
        if r.status_code not in ok:
            raise RuntimeError(f"{method} {path}: {r.status_code} {r.text[:400]}")
        return r


def apply(plan: Plan, api: Api) -> dict:
    n = collections.Counter()
    # Campanas y plantillas (409 = ya estaba)
    for slug, (name, date, _, segment) in CAMPAIGNS.items():
        r = api.call("POST", "/campaigns", ok=(201, 409), json={"slug": slug, "name": name, "segment": segment,
                                                                 "started_at": date, "status": "done"})
        n["campañas nuevas" if r.status_code == 201 else "campañas existentes"] += 1
    camps = {c["slug"]: c["id"] for c in api.call("GET", "/campaigns").json()}
    for t in plan.templates:
        r = api.call("POST", "/templates", ok=(201, 409), json=t)
        n["plantillas nuevas" if r.status_code == 201 else "plantillas existentes"] += 1
    # Blocklist antes de los leads: los emails bloqueados quedan como bounced
    for b in plan.blocks:
        api.call("POST", "/blocklist", json=b)
        n["blocklist"] += 1
    ids: dict[str, int] = {}
    for ref, lead in plan.leads.items():
        r = api.call("POST", "/leads", json=payload(lead))
        ids[ref] = r.json()["lead"]["id"]
        n["leads " + r.json()["result"]] += 1
        if lead.get("do_not_contact"):
            api.call("PATCH", f"/leads/{ids[ref]}", json={"do_not_contact": True})
    for m in plan.messages:
        body = {k: v for k, v in m.items() if not k.startswith("_") and v is not None}
        body["lead_id"] = ids[m["_ref"]]
        if m["_campaign"] in camps:
            body["campaign_id"] = camps[m["_campaign"]]
        r = api.call("POST", "/messages/import", ok=(201, 409), json=body)
        n["mensajes nuevos" if r.status_code == 201 else "mensajes existentes"] += 1
    by_lead = collections.defaultdict(list)
    for ref, a in plan.activities:
        by_lead[ref].append(a)
    for ref, acts in by_lead.items():
        existing = {(x["data"]["kind"], x["data"]["text"]) for x in api.call("GET", f"/leads/{ids[ref]}/timeline").json()
                    if x["type"] == "activity"}
        for a in acts:
            if (a["kind"], a["text"]) in existing:
                n["actividades existentes"] += 1
                continue
            api.call("POST", f"/leads/{ids[ref]}/activities", json=a)
            n["actividades nuevas"] += 1
    r = api.call("POST", "/ga/visits", json=plan.ga).json()
    n["visitas GA"], n["visitas GA con lead"] = r["rows"], r["matched"]
    return dict(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--url", default="http://127.0.0.1:8030")
    ap.add_argument("--key", default="")
    ap.add_argument("--refresh", action="store_true", help="volver a bajar el historial de Resend")
    ap.add_argument("--sin-cuerpos", action="store_true", help="no bajar el texto de cada mail")
    args = ap.parse_args()
    plan = build(args.refresh, not args.sin_cuerpos)
    diffs = stage_diffs(plan)
    plan.notes += stages_from_resend(plan)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "import-report.md").write_text(report(plan, diffs))
    print(f"Reporte: {(OUT / 'import-report.md').relative_to(ROOT)}")
    if args.apply:
        if not args.key:
            sys.exit("Falta --key (CRM_API_KEY)")
        print(json.dumps(apply(plan, Api(args.url, args.key)), ensure_ascii=False, indent=1))
        print(json.dumps(Api(args.url, args.key).call("GET", "/stats").json(), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
