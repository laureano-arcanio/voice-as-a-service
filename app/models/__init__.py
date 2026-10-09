"""Modelos ORM. Importar este paquete registra todas las tablas en Base.metadata
(Alembic y create_schema lo necesitan)."""
from .agents import Agent, AgentVersion
from .calls import ACTIVE_CALL_STATUSES, CallMode, CallRow, CallStatus
from .contact import ContactRequest
from .conversations import ConversationRow
from .tenancy import (
    ApiKey,
    ApiUsageDaily,
    Client,
    ClientLimitAdjustment,
    PhoneNumber,
    Role,
    Tier,
    User,
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
    "ACTIVE_CALL_STATUSES", "Agent", "AgentVersion", "ApiKey", "ApiUsageDaily", "CallMode", "CallRow", "CallStatus", "Client",
    "ClientLimitAdjustment", "ContactRequest", "ConversationRow", "PhoneNumber", "Role", "Tier", "User", "WaAccount", "WaCampaign",
    "WaCampaignRecipient", "WaMessage", "WaOptout", "WaThread",
]
