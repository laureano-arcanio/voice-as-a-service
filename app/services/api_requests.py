"""Pedidos a la API de inferencia, uno por uno (`api_requests`): la lista del admin (todos los
clientes) y la del cliente (los suyos), con tipo, key, estado, duracion y consumo.

Los limites se siguen controlando con el agregado diario (services/api_usage.py); esto es solo
para ver. Se anotan los pedidos que pasan el tope de pedidos por minuto: los que llegan al motor
(ok, cut, error) y los rechazados por el cupo del mes o el plan (rejected). Los 401, los de
alcance y los rate_limited no se guardan: no tienen tope y un cliente en loop llenaria la tabla.
"""
import datetime
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..models import ApiKey, ApiRequest, Client

KINDS = ("llm", "stt", "tts")
STATUSES = ("ok", "cut", "error", "rejected")
# api: la de inferencia. Las pruebas de voz (services/tts.py) se anotan aca pero no suman al cupo del plan.
SOURCES = ("api", "voice_test_panel", "voice_test_api", "voice_test_landing")


def log(s: Session, client_id: str, key_id: str | None, kind: str, status: str, **fields) -> None:
    s.add(ApiRequest(client_id=client_id, api_key_id=key_id, kind=kind, status=status, **fields))
    s.commit()


def _utc(day: datetime.date, tz: ZoneInfo) -> datetime.datetime:
    """00:00 local de `day`, en UTC sin zona (como se guarda)."""
    return datetime.datetime.combine(day, datetime.time(), tz).astimezone(datetime.UTC).replace(tzinfo=None)


@dataclass
class RequestFilter:
    client_id: str | None = None
    api_key_id: str | None = None
    kind: list[str] = field(default_factory=list)
    status: list[str] = field(default_factory=list)
    source: list[str] = field(default_factory=list)
    stream: bool | None = None
    date_from: datetime.date | None = None
    date_to: datetime.date | None = None     # inclusive
    tz: ZoneInfo = field(default_factory=lambda: ZoneInfo("UTC"))

    def where(self) -> list:
        conds = []
        if self.client_id:
            conds.append(ApiRequest.client_id == self.client_id)
        if self.api_key_id:
            conds.append(ApiRequest.api_key_id == self.api_key_id)
        if self.kind:
            conds.append(ApiRequest.kind.in_(self.kind))
        if self.status:
            conds.append(ApiRequest.status.in_(self.status))
        if self.source:
            conds.append(ApiRequest.source.in_(self.source))
        if self.stream is not None:
            conds.append(ApiRequest.stream.is_(self.stream))
        if self.date_from:
            conds.append(ApiRequest.created_at >= _utc(self.date_from, self.tz))
        if self.date_to:
            conds.append(ApiRequest.created_at < _utc(self.date_to + datetime.timedelta(days=1), self.tz))
        return conds


def page(s: Session, flt: RequestFilter, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    """Los pedidos del filtro, del mas nuevo al mas viejo, con el cliente y la key."""
    conds = flt.where()
    total = s.scalar(select(func.count()).select_from(ApiRequest).where(*conds)) or 0
    rows = s.execute(
        select(ApiRequest, Client.name, ApiKey.name, ApiKey.prefix)
        .join(Client, Client.id == ApiRequest.client_id)
        .outerjoin(ApiKey, ApiKey.id == ApiRequest.api_key_id)
        .where(*conds).order_by(ApiRequest.created_at.desc()).limit(limit).offset(offset)).all()
    items = [{**{c.name: getattr(r, c.name) for c in ApiRequest.__table__.columns},
              "client_name": client_name, "api_key_name": key_name, "api_key_prefix": prefix}
             for r, client_name, key_name, prefix in rows]
    return items, total


def summary(s: Session, flt: RequestFilter) -> dict:
    """Totales del filtro: pedidos por estado y por motor, consumo y duracion promedio de los ok."""
    ok = ApiRequest.status == "ok"
    row = s.execute(select(
        func.count(),
        *[func.count().filter(ApiRequest.status == st) for st in STATUSES],
        *[func.count().filter(ApiRequest.kind == k) for k in KINDS],
        func.coalesce(func.sum(ApiRequest.input_tokens), 0),
        func.coalesce(func.sum(ApiRequest.output_tokens), 0),
        func.coalesce(func.sum(case((ApiRequest.kind == "stt", ApiRequest.audio_seconds))), 0),
        func.coalesce(func.sum(case((ApiRequest.kind == "tts", ApiRequest.audio_seconds))), 0),
        func.avg(ApiRequest.duration_ms).filter(ok),
    ).where(*flt.where())).one()
    total, *rest = row
    by_status = dict(zip(STATUSES, rest[:len(STATUSES)], strict=True))
    rest = rest[len(STATUSES):]
    by_kind = dict(zip(KINDS, rest[:len(KINDS)], strict=True))
    in_tok, out_tok, stt_s, tts_s, avg_ms = rest[len(KINDS):]
    return {"requests": int(total), "by_status": {k: int(v) for k, v in by_status.items()},
            "by_kind": {k: int(v) for k, v in by_kind.items()},
            "input_tokens": int(in_tok), "output_tokens": int(out_tok),
            "stt_seconds": round(float(stt_s), 1), "tts_seconds": round(float(tts_s), 1),
            "avg_duration_ms": None if avg_ms is None else int(avg_ms)}
