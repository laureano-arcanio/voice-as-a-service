"""Modelos ORM. Importar este paquete registra todas las tablas en Base.metadata
(Alembic y create_schema lo necesitan)."""
from .agents import Agent, AgentVersion
from .calls import ACTIVE_CALL_STATUSES, CallMode, CallRow, CallStatus
from .contact import ContactRequest
from .conversations import ConversationRow
from .tenancy import (
    ApiKey,
    Client,
    PhoneNumber,
    Role,
    Tier,
    User,
    effective_max_call_seconds,
    effective_retention_days,
)
from .whatsapp import (
    WaAccount,
    WaCampaign,
    WaCampaignRecipient,
    WaMessage,
    WaOptout,
    WaThread,
)

__all__ = [
    "ACTIVE_CALL_STATUSES", "Agent", "AgentVersion", "ApiKey", "CallMode", "CallRow", "CallStatus", "Client",
    "ContactRequest", "ConversationRow", "PhoneNumber", "Role", "Tier", "User", "WaAccount", "WaCampaign",
    "WaCampaignRecipient", "WaMessage", "WaOptout", "WaThread", "effective_max_call_seconds",
    "effective_retention_days",
]
