"""Registro de accesos y cambios sobre datos de personas. El detalle no lleva datos clínicos."""
from sqlalchemy.orm import Session

from .models import AuditLog


def record(s: Session, tenant_id: str | None, action: str, *, user_id: str | None = None,
           person_id: str | None = None, detail: dict | None = None) -> AuditLog:
    """Agrega la fila a la sesión; hace el commit quien llama, junto con el cambio que registra."""
    row = AuditLog(tenant_id=tenant_id, user_id=user_id, action=action, person_id=person_id, detail=detail)
    s.add(row)
    return row
