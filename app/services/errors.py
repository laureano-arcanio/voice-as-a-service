"""Errores de negocio. La API los traduce a HTTP (app/api/errors.py)."""


class ServiceError(Exception):
    status_code = 400
    default_code = "error"

    def __init__(self, message: str, code: str | None = None, details: list[dict] | None = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        # Errores puntuales (ej. por campo de la definicion de un agente): [{path, message}].
        self.details = details or []


class NotFound(ServiceError):
    status_code = 404
    default_code = "not_found"


class Forbidden(ServiceError):
    status_code = 403
    default_code = "forbidden"


class Conflict(ServiceError):
    status_code = 409
    default_code = "conflict"


class Invalid(ServiceError):
    status_code = 422
    default_code = "invalid"


class QuotaExceeded(ServiceError):
    """Limite del tier. code: concurrency_limit, calls_per_hour, calls_per_day, calls_per_month,
    inbound_minutes, outbound_minutes, client_inactive o number_suspended."""
    status_code = 429
    default_code = "quota_exceeded"


class Upstream(ServiceError):
    """Fallo un servicio externo (LiveKit, TTS)."""
    status_code = 502
    default_code = "upstream_error"
