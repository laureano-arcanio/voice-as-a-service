"""Google Analytics Data API: reporte por dia y UTM, guardado en ga_visits y cruzado con leads y campanas.

Auth con una cuenta de servicio (JSON en CRM_GA_CREDENTIALS) firmando el JWT con pyjwt, sin el SDK
de Google. La cuenta tiene que estar como Lector en la propiedad CRM_GA_PROPERTY_ID.
"""
import asyncio
import datetime
import json
import logging
import re
import time

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import local_today, settings
from ..db import get_sessionmaker, utcnow
from ..models import Campaign, GaVisit, Lead

logger = logging.getLogger(__name__)
SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class GaError(Exception):
    pass


def configured() -> bool:
    return bool(settings.ga_property_id and settings.ga_credentials)


def _token() -> str:
    try:
        with open(settings.ga_credentials) as fh:
            sa = json.load(fh)
    except OSError as e:
        raise GaError(f"no se pudo leer CRM_GA_CREDENTIALS: {e}") from e
    now = int(time.time())
    assertion = jwt.encode({"iss": sa["client_email"], "scope": SCOPE, "aud": TOKEN_URL, "iat": now,
                            "exp": now + 3600}, sa["private_key"], algorithm="RS256")
    r = httpx.post(TOKEN_URL, data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                    "assertion": assertion}, timeout=20)
    if r.status_code >= 400:
        raise GaError(f"token: {r.status_code} {r.text[:300]}")
    return r.json()["access_token"]


def run_report(start: datetime.date, end: datetime.date) -> list[dict]:
    if not configured():
        raise GaError("faltan CRM_GA_PROPERTY_ID y CRM_GA_CREDENTIALS")
    body = {
        "dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
        "dimensions": [{"name": n} for n in ("date", "sessionSourceMedium", "sessionCampaignName",
                                             "sessionManualAdContent")],
        "metrics": [{"name": n} for n in ("activeUsers", "sessions", "eventCount")],
        "dimensionFilter": {"filter": {"fieldName": "sessionSourceMedium",
                                       "stringFilter": {"matchType": "CONTAINS", "value": "email"}}},
        "limit": 10000,
    }
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{settings.ga_property_id}:runReport"
    r = httpx.post(url, json=body, headers={"Authorization": f"Bearer {_token()}"}, timeout=60)
    if r.status_code >= 400:
        raise GaError(f"runReport: {r.status_code} {r.text[:300]}")
    rows = []
    for row in r.json().get("rows", []):
        d = [x["value"] for x in row["dimensionValues"]]
        m = [int(float(x["value"])) for x in row["metricValues"]]
        rows.append({"date": datetime.date(int(d[0][:4]), int(d[0][4:6]), int(d[0][6:])), "source_medium": d[1],
                     "utm_campaign": d[2], "utm_content": d[3], "active_users": m[0], "sessions": m[1],
                     "events": m[2]})
    return rows


def base_campaign(utm_campaign: str) -> tuple[str, bool]:
    """follow_up_canales_4 -> (canales4, True)."""
    if utm_campaign.startswith("follow_up_"):
        rest = utm_campaign.removeprefix("follow_up_")
        return re.sub(r"_(\d+)$", r"\1", rest), True
    return utm_campaign, False


def store(s: Session, rows: list[dict]) -> dict:
    leads = {slug: lid for lid, slug in s.execute(select(Lead.id, Lead.slug))}
    camps = {slug: cid for cid, slug in s.execute(select(Campaign.id, Campaign.slug))}
    n = matched = 0
    for r in rows:
        v = s.scalar(select(GaVisit).where(GaVisit.date == r["date"], GaVisit.source_medium == r["source_medium"],
                                           GaVisit.utm_campaign == r["utm_campaign"],
                                           GaVisit.utm_content == r["utm_content"]))
        if not v:
            v = GaVisit(**{k: r[k] for k in ("date", "source_medium", "utm_campaign", "utm_content")})
            s.add(v)
        v.active_users, v.sessions, v.events, v.synced_at = r["active_users"], r["sessions"], r["events"], utcnow()
        camp, fu = base_campaign(r["utm_campaign"])
        v.lead_id, v.campaign_id, v.follow_up = leads.get(r["utm_content"]), camps.get(camp), fu
        n += 1
        matched += v.lead_id is not None
    s.commit()
    return {"rows": n, "matched": matched}


def sync(s: Session, start: datetime.date | None = None, end: datetime.date | None = None) -> dict:
    end = end or local_today()
    start = start or end - datetime.timedelta(days=3)
    return store(s, run_report(start, end))


def rematch(s: Session) -> int:
    """Vuelve a cruzar todas las visitas (despues de cargar leads o campanas)."""
    rows = [{"date": v.date, "source_medium": v.source_medium, "utm_campaign": v.utm_campaign,
             "utm_content": v.utm_content, "active_users": v.active_users, "sessions": v.sessions,
             "events": v.events} for v in s.scalars(select(GaVisit))]
    return store(s, rows)["matched"]


async def ga_loop() -> None:
    if not configured():
        logger.info("crm: GA sin configurar (CRM_GA_PROPERTY_ID, CRM_GA_CREDENTIALS)")
        return
    while True:
        try:
            with get_sessionmaker()() as s:
                await asyncio.to_thread(sync, s)
        except Exception:
            logger.exception("crm: sync de GA")
        await asyncio.sleep(settings.ga_interval_seconds)
