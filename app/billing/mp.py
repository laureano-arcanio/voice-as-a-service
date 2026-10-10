"""Cliente de la API de Mercado Pago para las suscripciones (preapproval) y la firma del webhook.

Probado contra el sandbox el 10-oct-2026 (docs/SUSCRIPCIONES_PLAN.md, 6.2): una suscripcion
`authorized` con `card_token_id` cobra el primer mes en el momento; una tarjeta rechazada falla al
crearla (400 CC_VAL_*); la cancelacion se escribe `cancelled` y es final.
"""
import hashlib
import hmac
import logging
from dataclasses import dataclass

import httpx

from ..config import settings
from ..services.errors import Invalid, Upstream

logger = logging.getLogger(__name__)
TIMEOUT = 20


def enabled() -> bool:
    return bool(settings.mp_billing_access_token and settings.mp_billing_public_key)


class CardRejected(Invalid):
    default_code = "card_rejected"


@dataclass
class Preapproval:
    id: str
    status: str                     # pending, authorized, paused, cancelled
    next_payment_date: str | None   # ISO con zona
    amount: float
    external_reference: str
    raw: dict

    @classmethod
    def of(cls, d: dict) -> "Preapproval":
        return cls(id=d["id"], status=d.get("status", ""), next_payment_date=d.get("next_payment_date"),
                   amount=float((d.get("auto_recurring") or {}).get("transaction_amount") or 0),
                   external_reference=d.get("external_reference") or "", raw=d)


class Client:
    """Sincronico (lo usan los endpoints sync y el barrido en un thread)."""

    def __init__(self, token: str | None = None, base_url: str | None = None, transport=None):
        self.http = httpx.Client(base_url=base_url or settings.mp_api_url, timeout=TIMEOUT, transport=transport,
                                 headers={"Authorization": f"Bearer {token or settings.mp_billing_access_token}"})

    def _call(self, method: str, path: str, **kw) -> dict:
        try:
            r = self.http.request(method, path, **kw)
        except httpx.HTTPError as e:
            raise Upstream("No se pudo conectar con Mercado Pago. Probá de nuevo en un rato.") from e
        if r.status_code >= 500:
            logger.warning("mp %s %s: %s %s", method, path, r.status_code, r.text[:300])
            raise Upstream("Mercado Pago no respondió. Probá de nuevo en un rato.")
        data = r.json() if r.content else {}
        if r.status_code >= 400:
            logger.info("mp %s %s: %s %s", method, path, r.status_code, str(data)[:300])
            raise _rejection(data)
        return data

    def create_subscription(self, *, reason: str, external_reference: str, payer_email: str, card_token_id: str,
                            amount: int, back_url: str) -> Preapproval:
        return Preapproval.of(self._call("POST", "/preapproval", json={
            "reason": reason, "external_reference": external_reference, "payer_email": payer_email,
            "card_token_id": card_token_id, "status": "authorized", "back_url": back_url,
            "auto_recurring": {"frequency": 1, "frequency_type": "months", "transaction_amount": amount,
                               "currency_id": "ARS"}}))

    def get_subscription(self, preapproval_id: str) -> Preapproval:
        return Preapproval.of(self._call("GET", f"/preapproval/{preapproval_id}"))

    def set_amount(self, preapproval_id: str, amount: int) -> Preapproval:
        """Rige desde el proximo debito (no cobra la diferencia)."""
        return Preapproval.of(self._call("PUT", f"/preapproval/{preapproval_id}", json={
            "auto_recurring": {"transaction_amount": amount, "currency_id": "ARS"}}))

    def cancel(self, preapproval_id: str) -> Preapproval:
        return Preapproval.of(self._call("PUT", f"/preapproval/{preapproval_id}", json={"status": "cancelled"}))

    def subscription_payments(self, preapproval_id: str) -> list[dict]:
        """Cuotas (authorized payments) de la suscripcion, con el pago de cada una."""
        # Sin `limit`: MP rechaza 50 ("Invalid value for limit"); el default trae las 12 ultimas.
        return self._call("GET", "/authorized_payments/search",
                          params={"preapproval_id": preapproval_id}).get("results", [])

    def authorized_payment(self, authorized_payment_id: str) -> dict:
        return self._call("GET", f"/authorized_payments/{authorized_payment_id}")

    def payment(self, payment_id: str) -> dict:
        return self._call("GET", f"/v1/payments/{payment_id}")


def _rejection(data: dict) -> Invalid:
    message = str(data.get("message") or "")
    if "cvv" in message.lower():
        # El token se genero sin el codigo de seguridad (MP lo marca opcional en Mastercard, Mastercard
        # Prepaid y Naranja) y la suscripcion lo exige: el formulario siempre lo pide (landing y panel).
        return CardRejected("Falta el código de seguridad de la tarjeta. Ingresalo y probá de nuevo.",
                            "card_cvv_required")
    if message.startswith("CC_VAL") or "card" in message.lower():
        return CardRejected("La tarjeta fue rechazada. Probá con otra o revisá los datos.")
    return Invalid("Mercado Pago rechazó la operación. Probá de nuevo o escribinos.", "mp_rejected")


def valid_signature(header: str | None, request_id: str | None, data_id: str | None,
                    secret: str | None = None) -> bool:
    """x-signature: `ts=...,v1=<hmac>`. El manifiesto es `id:<data.id>;request-id:<x-request-id>;ts:<ts>;`
    (sin las partes que no vengan; data.id en minusculas si es alfanumerico), HMAC-SHA256 con la clave
    secreta del webhook."""
    secret = secret if secret is not None else settings.mp_billing_webhook_secret
    if not secret or not header:
        return False
    parts = dict(p.strip().split("=", 1) for p in header.split(",") if "=" in p)
    ts, v1 = parts.get("ts"), parts.get("v1")
    if not ts or not v1:
        return False
    manifest = ""
    if data_id:
        manifest += f"id:{data_id.lower() if not data_id.isdigit() else data_id};"
    if request_id:
        manifest += f"request-id:{request_id};"
    manifest += f"ts:{ts};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)
