"""Modelos ORM. Importar este paquete registra todas las tablas en Base.metadata
(Alembic y create_schema lo necesitan)."""
from .agents import Agent, AgentVersion
from .apps import App, AppJobRun, AppLink
from .billing import BillingPayment, Subscription
from .call_links import CallLink
from .calls import ACTIVE_CALL_STATUSES, CallMode, CallRow, CallStatus
from .campaigns import (
    Campaign,
    CampaignCallback,
    CampaignContact,
    Contact,
    ContactOptout,
)
from .contact import ContactRequest
from .conversations import ConversationRow
from .llm import LlmConnection
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
    WaMessage,
    WaOperator,
    WaRoute,
    WaThread,
)

__all__ = [
    "ACTIVE_CALL_STATUSES",
    "Agent",
    "AgentVersion",
    "ApiKey",
    "ApiUsageDaily",
    "App",
    "AppJobRun",
    "AppLink",
    "BillingPayment",
    "CallLink",
    "CallMode",
    "CallRow",
    "CallStatus",
    "Campaign",
    "CampaignCallback",
    "CampaignContact",
    "Client",
    "ClientLimitAdjustment",
    "Contact",
    "ContactOptout",
    "ContactRequest",
    "ConversationRow",
    "LlmConnection",
    "PhoneNumber",
    "Role",
    "Subscription",
    "Tier",
    "User",
    "WaAccount",
    "WaMessage",
    "WaOperator",
    "WaRoute",
    "WaThread",
]
