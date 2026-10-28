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


def service_token(credentials: str, scope: str) -> str:
    """Token de la cuenta de servicio (JSON en `credentials`) para `scope`. Lo usa tambien gcal."""
    try:
        with open(credentials) as fh:
            sa = json.load(fh)
    except OSError as e:
        raise GaError(f"no se pudo leer las credenciales de la cuenta de servicio: {e}") from e
    now = int(time.time())
    assertion = jwt.encode({"iss": sa["client_email"], "scope": scope, "aud": TOKEN_URL, "iat": now,
                            "exp": now + 3600}, sa["private_key"], algorithm="RS256")
    r = httpx.post(TOKEN_URL, data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                    "assertion": assertion}, timeout=20)
    if r.status_code >= 400:
        raise GaError(f"token: {r.status_code} {r.text[:300]}")
    return r.json()["access_token"]


def _token() -> str:
    return service_token(settings.ga_credentials, SCOPE)


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


# --- Reporte del sitio (pagina Sitio web del CRM) ---
# Solo el pais de CRM_GA_COUNTRY: el resto es casi todo robots (28 dias al 23-oct-2026: 271 usuarios
# de EE.UU. contra 122 de Argentina). Se consulta en vivo y se guarda SITE_TTL segundos.
SITE_TTL = 600
_site_cache: dict[tuple[int, datetime.date], tuple[float, dict]] = {}


def _req(start: datetime.date, end: datetime.date, dims: list[str], mets: list[str], limit: int = 0,
         country: bool = True, compare: datetime.date | None = None) -> dict:
    ranges = [{"startDate": start.isoformat(), "endDate": end.isoformat(), "name": "actual"}]
    if compare:
        ranges.append({"startDate": (compare - (end - start)).isoformat(), "endDate": compare.isoformat(),
                       "name": "anterior"})
    r = {"dateRanges": ranges, "dimensions": [{"name": d} for d in dims],
         "metrics": [{"name": m} for m in mets]}
    if country:
        r["dimensionFilter"] = {"filter": {"fieldName": "country", "stringFilter": {"value": settings.ga_country}}}
    if limit:
        r |= {"limit": limit, "orderBys": [{"metric": {"metricName": mets[0]}, "desc": True}]}
    return r


def _batch(token: str, requests: list[dict]) -> list[list[tuple[list[str], list[float]]]]:
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{settings.ga_property_id}:batchRunReports"
    r = httpx.post(url, json={"requests": requests}, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    if r.status_code >= 400:
        raise GaError(f"batchRunReports: {r.status_code} {r.text[:300]}")
    return [[([x["value"] for x in row.get("dimensionValues", [])], [float(x["value"]) for x in row["metricValues"]])
             for row in rep.get("rows", [])] for rep in r.json()["reports"]]


TOTALS = ("activeUsers", "newUsers", "sessions", "screenPageViews", "engagementRate", "averageSessionDuration")
TOTAL_KEYS = ("users", "new_users", "sessions", "views", "engagement_rate", "avg_session_seconds")


def site_report(days: int, refresh: bool = False) -> dict:
    if not configured():
        raise GaError("faltan CRM_GA_PROPERTY_ID y CRM_GA_CREDENTIALS")
    end = local_today()
    key = (days, end)
    hit = _site_cache.get(key)
    if hit and not refresh and time.monotonic() - hit[0] < SITE_TTL:
        return hit[1]
    start = end - datetime.timedelta(days=days - 1)
    token = _token()
    totals, by_day, channels, pages, cities = _batch(token, [
        _req(start, end, [], list(TOTALS), compare=start - datetime.timedelta(days=1)),
        _req(start, end, ["date"], ["activeUsers", "sessions", "screenPageViews"]),
        _req(start, end, ["sessionDefaultChannelGroup"], ["sessions", "activeUsers"], limit=20),
        _req(start, end, ["pagePath"], ["screenPageViews", "activeUsers"], limit=20),
        _req(start, end, ["city"], ["activeUsers"], limit=10),
    ])
    sources, devices, everyone = _batch(token, [
        _req(start, end, ["sessionSourceMedium"], ["sessions", "activeUsers"], limit=10),
        _req(start, end, ["deviceCategory"], ["activeUsers"], limit=10),
        _req(start, end, [], ["activeUsers"], country=False),
    ])

    def tot(name: str) -> dict:
        # Con dos rangos GA agrega la dimension dateRange; sin filas (sin visitas), todo en 0.
        m = next((m for d, m in totals if d and d[-1] == name), [0.0] * len(TOTALS))
        return {k: (round(v, 4) if k in ("engagement_rate", "avg_session_seconds") else int(v))
                for k, v in zip(TOTAL_KEYS, m, strict=True)}

    daily = {d[0]: m for d, m in by_day}
    out = {
        "country": settings.ga_country, "days": days, "start": start.isoformat(), "end": end.isoformat(),
        "updated_at": utcnow().isoformat(),
        "totals": tot("actual"), "previous": tot("anterior"),
        "all_users": int(everyone[0][1][0]) if everyone else 0,
        "by_day": [{"day": d.isoformat(), "users": int(m[0]), "sessions": int(m[1]), "views": int(m[2])}
                   for d in (start + datetime.timedelta(days=i) for i in range(days))
                   for m in [daily.get(d.strftime("%Y%m%d"), [0, 0, 0])]],
        "channels": [{"channel": d[0], "sessions": int(m[0]), "users": int(m[1])} for d, m in channels],
        "pages": [{"path": d[0], "views": int(m[0]), "users": int(m[1])} for d, m in pages],
        "cities": [{"city": d[0], "users": int(m[0])} for d, m in cities],
        "sources": [{"source_medium": d[0], "sessions": int(m[0]), "users": int(m[1])} for d, m in sources],
        "devices": [{"device": d[0], "users": int(m[0])} for d, m in devices],
    }
    _site_cache[key] = (time.monotonic(), out)
    return out


# --- Desglose de un item de la pagina Sitio web (canal, fuente/medio, pagina, ciudad o dispositivo) ---
# GA no da visitantes sueltos: el detalle mas fino son las sesiones por dia y por combinacion de
# fuente/medio, campana, utm_content, pagina de entrada, ciudad y dispositivo. Tope de GA: 9
# dimensiones contando las del filtro (pais y el item), asi que entran 7.
DETAIL_DIMS = {"channel": "sessionDefaultChannelGroup", "source": "sessionSourceMedium", "page": "pagePath",
               "city": "city", "device": "deviceCategory"}
DETAIL_FIELDS = ("date", "sessionSourceMedium", "sessionCampaignName", "sessionManualAdContent",
                 "landingPagePlusQueryString", "city", "deviceCategory")
DETAIL_LIMIT = 2000
_detail_cache: dict[tuple, tuple[float, list]] = {}


def _detail_rows(kind: str, value: str, days: int, refresh: bool) -> tuple[datetime.date, datetime.date, list]:
    end = local_today()
    start = end - datetime.timedelta(days=days - 1)
    key = (kind, value, days, end)
    hit = _detail_cache.get(key)
    if hit and not refresh and time.monotonic() - hit[0] < SITE_TTL:
        return start, end, hit[1]
    req = _req(start, end, list(DETAIL_FIELDS), ["sessions", "screenPageViews", "userEngagementDuration"],
               limit=DETAIL_LIMIT)
    item = {"filter": {"fieldName": DETAIL_DIMS[kind], "stringFilter": {"matchType": "EXACT", "value": value}}}
    req["dimensionFilter"] = {"andGroup": {"expressions": [req["dimensionFilter"], item]}}
    rows = _batch(_token(), [req])[0]
    _detail_cache[key] = (time.monotonic(), rows)
    return start, end, rows


def _blank(v: str) -> str | None:
    """Vacios y marcadores de GA ("(not set)", "(direct)", "(ai-assistant)") a None."""
    return None if not v or v.startswith("(") else v


def _utm(page: str, name: str) -> str | None:
    """utm_* de la URL de entrada. Recupera los links con "&amp;" (tanda 2), que GA no atribuye."""
    m = re.search(rf"[?&;]{name}=([^&#]+)", page)
    return m.group(1) if m else None


def site_detail(s: Session, kind: str, value: str, days: int, refresh: bool = False) -> dict:
    """Sesiones de un item, con el lead (utm_content) y la campana (utm_campaign) cruzados con el CRM."""
    if not configured():
        raise GaError("faltan CRM_GA_PROPERTY_ID y CRM_GA_CREDENTIALS")
    start, end, rows = _detail_rows(kind, value, days, refresh)
    leads = {slug: (lid, name) for lid, slug, name in s.execute(select(Lead.id, Lead.slug, Lead.name))}
    camps = {slug: name for slug, name in s.execute(select(Campaign.slug, Campaign.name))}
    visits = []
    for d, m in rows:
        content = _blank(d[3]) or _utm(d[4], "utm_content")
        campaign = _blank(d[2]) or _utm(d[4], "utm_campaign")
        lead = leads.get(content) if content else None
        camp, follow_up = base_campaign(campaign) if campaign else (None, False)
        visits.append({
            "day": f"{d[0][:4]}-{d[0][4:6]}-{d[0][6:]}", "source_medium": d[1], "utm_campaign": campaign,
            "campaign_name": camps.get(camp), "follow_up": follow_up, "utm_content": content,
            "lead_id": lead[0] if lead else None, "lead_name": lead[1] if lead else None,
            "landing_page": _blank(d[4]), "city": _blank(d[5]), "device": d[6],
            "sessions": int(m[0]), "views": int(m[1]), "engagement_seconds": int(m[2])})
    visits.sort(key=lambda v: (v["day"], v["sessions"]), reverse=True)

    def group(field: str) -> list[dict]:
        acc: dict = {}
        for v in visits:
            g = acc.setdefault(v[field], {field: v[field], "sessions": 0, "views": 0, "engagement_seconds": 0})
            for k in ("sessions", "views", "engagement_seconds"):
                g[k] += v[k]
        return sorted(acc.values(), key=lambda g: g["sessions"], reverse=True)

    # Empresas: por utm_content (las que vinieron de un link nuestro), con o sin lead en el CRM.
    companies: dict = {}
    for v in visits:
        if not v["utm_content"]:
            continue
        c = companies.setdefault(v["utm_content"], {
            "utm_content": v["utm_content"], "lead_id": v["lead_id"], "lead_name": v["lead_name"],
            "sessions": 0, "views": 0, "engagement_seconds": 0, "first_day": v["day"], "last_day": v["day"],
            "campaigns": [], "cities": []})
        for k in ("sessions", "views", "engagement_seconds"):
            c[k] += v[k]
        c["first_day"] = min(c["first_day"], v["day"])
        label = v["campaign_name"] or v["utm_campaign"]
        if label and (label, v["follow_up"]) not in [(x["name"], x["follow_up"]) for x in c["campaigns"]]:
            c["campaigns"].append({"name": label, "follow_up": v["follow_up"]})
        if v["city"] and v["city"] not in c["cities"]:
            c["cities"].append(v["city"])
    return {
        "kind": kind, "value": value, "country": settings.ga_country, "days": days,
        "start": start.isoformat(), "end": end.isoformat(), "truncated": len(rows) >= DETAIL_LIMIT,
        "totals": {k: sum(v[k] for v in visits) for k in ("sessions", "views", "engagement_seconds")},
        "companies": sorted(companies.values(), key=lambda c: c["last_day"], reverse=True),
        "sources": group("source_medium"), "landing_pages": group("landing_page"),
        "visits": visits,
    }


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
