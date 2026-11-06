"""Páginas del panel: HTML estático con panel.js, que trae los datos de /panel/api. El formulario sale de
tenants.form_html, sin scripts propios, porque la CSP no los deja correr."""
import html
import re
from pathlib import Path
from string import Template
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from .. import admin_ops
from ..auth import SESSION_COOKIE, DbSession, is_admin, session_user
from ..db import utcnow
from ..models import ConversationChoice, Person, RecordLink, Tenant, User
from .persons import get_active_person

router = APIRouter()

TEMPLATES = Path(__file__).parent / "templates"
_LAYOUT = Template((TEMPLATES / "layout.html").read_text(encoding="utf-8"))
_LOGIN = Template((TEMPLATES / "login.html").read_text(encoding="utf-8"))
_LIST = (TEMPLATES / "list.html").read_text(encoding="utf-8")
_PERSON = Template((TEMPLATES / "person.html").read_text(encoding="utf-8"))
_HEADER = Template((TEMPLATES / "header.html").read_text(encoding="utf-8"))
# Páginas del admin: cascarones que admin.js llena con /admin/api.
_ADMIN_LIST = (TEMPLATES / "admin_list.html").read_text(encoding="utf-8")
_ADMIN_TENANT = Template((TEMPLATES / "admin_tenant.html").read_text(encoding="utf-8"))
_ADMIN_PERSONS = Template((TEMPLATES / "admin_persons.html").read_text(encoding="utf-8"))
_ADMIN_PERSON = Template((TEMPLATES / "admin_person.html").read_text(encoding="utf-8"))

HOME = "/personas"
ADMIN_HOME = "/admin"
# Rutas a las que se puede volver después del login. Solo estas: nada externo, ni //otro, ni /\otro.
_NEXT_ALLOWED = re.compile(r"/personas(/nueva|/[0-9a-f-]{36})?|/c/[A-Za-z0-9_-]{1,64}"
                           r"|/admin(/espacios/[0-9a-f-]{36}(/fichas(/[0-9a-f-]{36})?)?)?")
_TOKEN = re.compile(r"[A-Za-z0-9_-]{1,64}")
# La de main.py, más form-action: el formulario del tenant no puede enviar a otro sitio.
PAGE_CSP = "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'; form-action 'self'"


def safe_next(value: str | None) -> str:
    return value if value and _NEXT_ALLOWED.fullmatch(value) else HOME


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def _html(title: str, page: str, content: str, *, header: str = "", status: int = 200,
          script: str = "panel.js") -> HTMLResponse:
    body = _LAYOUT.substitute(title=_esc(title), page=page, header=header, content=content, script=script)
    return HTMLResponse(body, status_code=status, headers={"Content-Security-Policy": PAGE_CSP})


def _header(s: Session, user: User, home: str = HOME) -> str:
    tenant = s.get(Tenant, user.tenant_id)
    return _HEADER.substitute(tenant=_esc(tenant.name), email=_esc(user.email), home=home)


def _to_login(path: str) -> RedirectResponse:
    return RedirectResponse(f"/login?next={quote(safe_next(path), safe='')}", status_code=303)


def _not_found(s: Session, user: User, home: str = HOME) -> HTMLResponse:
    """Igual para lo que no existe y lo que es de otro tenant: no confirma nada."""
    label = "Ir a los espacios" if home == ADMIN_HOME else "Ir a las fichas"
    content = f'<div class="card empty"><h1>No encontramos esta página</h1><a href="{home}">{label}</a></div>'
    return _html("No encontrada", "error", content, header=_header(s, user, home), status=404,
                 script="admin.js" if home == ADMIN_HOME else "panel.js")


def _user(request: Request, s: Session) -> User | None:
    return session_user(s, request.cookies.get(SESSION_COOKIE))


def _to_admin() -> RedirectResponse:
    """El tenant admin no tiene fichas propias: sus usuarios van al panel del admin."""
    return RedirectResponse(ADMIN_HOME, status_code=303)


@router.get("/")
def home() -> RedirectResponse:
    return RedirectResponse(HOME, status_code=303)


@router.get("/login")
def login_page(request: Request, s: DbSession, next: str | None = None):  # noqa: A002
    target = safe_next(next)
    if _user(request, s) is not None:
        return RedirectResponse(target, status_code=303)
    return _html("Ingresar", "login", _LOGIN.substitute(next=_esc(target)))


@router.get("/personas")
def list_page(request: Request, s: DbSession):
    user = _user(request, s)
    if user is None:
        return _to_login(HOME)
    if is_admin(s, user):
        return _to_admin()
    return _html("Fichas", "list", _LIST, header=_header(s, user))


def _form_page(s: Session, user: User, person_id: str, title: str) -> HTMLResponse:
    tenant = s.get(Tenant, user.tenant_id)
    if tenant.form_html is None or tenant.form_schema is None or tenant.manifest is None:
        content = ('<div class="card empty"><h1>Falta el formulario</h1>'
                   "<p>Este espacio todavía no tiene formulario cargado. Pedile a quien administra Registros que lo cargue.</p>"
                   f'<a href="{HOME}">Volver a las fichas</a></div>')
        return _html(title, "error", content, header=_header(s, user))
    # form_html es dato del tenant, cargado por CLI: va tal cual.
    content = _PERSON.substitute(person_id=_esc(person_id), form=tenant.form_html)
    return _html(title, "person", content, header=_header(s, user))


@router.get("/personas/nueva")
def new_page(request: Request, s: DbSession):
    user = _user(request, s)
    if user is None:
        return _to_login("/personas/nueva")
    if is_admin(s, user):
        return _to_admin()
    return _form_page(s, user, "", "Nueva ficha")


@router.get("/personas/{person_id}")
def person_page(person_id: str, request: Request, s: DbSession):
    user = _user(request, s)
    if user is None:
        return _to_login(f"/personas/{person_id}")
    if is_admin(s, user):
        return _to_admin()
    if get_active_person(s, user.tenant_id, person_id) is None:
        return _not_found(s, user)
    return _form_page(s, user, person_id, "Ficha")


def _link_page(s: Session, user: User, persons: list[Person]) -> HTMLResponse:
    rows = "".join(
        f'<li><a href="/personas/{_esc(p.id)}">{_esc(p.name)}</a>'
        f'<span class="badge {"ok" if p.al_dia else "warn"}">{"Al día" if p.al_dia else "No está al día"}</span></li>'
        for p in persons
    )
    content = (f'<div class="card"><h1>Fichas de este teléfono</h1>'
               f'<p class="muted">Este teléfono está en {len(persons)} fichas. Elegí cuál abrir.</p>'
               f'<ul class="link-list">{rows}</ul></div>')
    return _html("Fichas de este teléfono", "link", content, header=_header(s, user))


@router.get("/c/{token}")
def open_link(token: str, request: Request, s: DbSession):
    """Sin sesión, al login: la respuesta no dice si el token existe ni de quién es."""
    user = _user(request, s)
    if user is None:
        return _to_login(f"/c/{token}")
    if is_admin(s, user):
        return _to_admin()
    link = s.get(RecordLink, token) if _TOKEN.fullmatch(token) else None
    if link is None or link.tenant_id != user.tenant_id:
        return _not_found(s, user)
    if link.expires_at <= utcnow():
        return RedirectResponse(HOME, status_code=303)
    person_ids = list(link.person_ids or [])
    chosen = s.scalar(select(ConversationChoice.person_id).where(
        ConversationChoice.tenant_id == user.tenant_id,
        ConversationChoice.conversation_id == link.conversation_id,
    ))
    if chosen:
        person_ids = [chosen]
    persons = list(s.scalars(select(Person).where(Person.tenant_id == user.tenant_id, Person.id.in_(person_ids),
                                                  Person.active).order_by(Person.name)))
    if not persons:  # todas de baja
        return RedirectResponse(HOME, status_code=303)
    for person in persons:
        audit.record(s, user.tenant_id, "link_open", user_id=user.id, person_id=person.id,
                     detail={"conversation_id": link.conversation_id})
    s.commit()
    if len(persons) == 1:
        return RedirectResponse(f"/personas/{persons[0].id}", status_code=303)
    return _link_page(s, user, persons)


# --- Admin ---


def _admin_gate(request: Request, s: Session, path: str) -> tuple[User | None, Response | None]:
    """Misma regla que AdminUser: sin sesión, al login con `next`; un usuario de cliente recibe 404."""
    user = _user(request, s)
    if user is None:
        return None, _to_login(path)
    if not is_admin(s, user):
        return None, _not_found(s, user)
    return user, None


def _admin_html(s: Session, user: User, title: str, page: str, content: str) -> HTMLResponse:
    return _html(title, page, content, header=_header(s, user, ADMIN_HOME), script="admin.js")


def _admin_tenant(s: Session, user: User, tenant_id: str) -> Tenant | HTMLResponse:
    """Espacio administrable; el tenant admin y lo que no existe dan el mismo 404."""
    try:
        return admin_ops.tenant_by_id(s, tenant_id)
    except admin_ops.NotFound:
        return _not_found(s, user, ADMIN_HOME)


@router.get("/admin")
def admin_page(request: Request, s: DbSession):
    user, early = _admin_gate(request, s, ADMIN_HOME)
    return early or _admin_html(s, user, "Espacios", "admin-list", _ADMIN_LIST)


@router.get("/admin/espacios/{tenant_id}")
def admin_tenant_page(tenant_id: str, request: Request, s: DbSession):
    user, early = _admin_gate(request, s, f"{ADMIN_HOME}/espacios/{tenant_id}")
    if early:
        return early
    tenant = _admin_tenant(s, user, tenant_id)
    if isinstance(tenant, HTMLResponse):
        return tenant
    return _admin_html(s, user, tenant.name, "admin-tenant", _ADMIN_TENANT.substitute(tenant_id=tenant.id))


@router.get("/admin/espacios/{tenant_id}/fichas")
def admin_persons_page(tenant_id: str, request: Request, s: DbSession):
    user, early = _admin_gate(request, s, f"{ADMIN_HOME}/espacios/{tenant_id}/fichas")
    if early:
        return early
    tenant = _admin_tenant(s, user, tenant_id)
    if isinstance(tenant, HTMLResponse):
        return tenant
    return _admin_html(s, user, f"Fichas de {tenant.name}", "admin-persons", _ADMIN_PERSONS.substitute(tenant_id=tenant.id))


@router.get("/admin/espacios/{tenant_id}/fichas/{person_id}")
def admin_person_page(tenant_id: str, person_id: str, request: Request, s: DbSession):
    user, early = _admin_gate(request, s, f"{ADMIN_HOME}/espacios/{tenant_id}/fichas/{person_id}")
    if early:
        return early
    tenant = _admin_tenant(s, user, tenant_id)
    if isinstance(tenant, HTMLResponse):
        return tenant
    if get_active_person(s, tenant.id, person_id) is None:
        return _not_found(s, user, ADMIN_HOME)
    return _admin_html(s, user, "Ficha", "admin-person",
                       _ADMIN_PERSON.substitute(tenant_id=tenant.id, person_id=_esc(person_id)))
