"""Errores de dominio: la API los devuelve como application/problem+json (crm/main.py)."""


class CrmError(Exception):
    status = 400
    title = "Pedido invalido"

    def __init__(self, detail: str, field: str | None = None):
        super().__init__(detail)
        self.detail, self.field = detail, field


class Invalid(CrmError):
    status = 422
    title = "Datos invalidos"


class NotFound(CrmError):
    status = 404
    title = "No existe"


class Conflict(CrmError):
    status = 409
    title = "Conflicto"


class Forbidden(CrmError):
    status = 403
    title = "No permitido"
