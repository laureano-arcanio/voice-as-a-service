"""Modelos ORM. Importar este paquete registra todas las tablas en Base.metadata
(Alembic y create_schema lo necesitan)."""
from .agents import Agent, AgentVersion
from .billing import BillingPayment, Subscription
from .call_links import CallLink
from .calls import ACTIVE_CALL_STATUSES, BlockedNumber, CallMode, CallRow, CallStatus
from .campaigns import (
    Campaign,
    CampaignCallback,
    CampaignContact,
    Contact,
    ContactOptout,
)
from .contact import ContactRequest
from .conversations import ConversationRow
from .handoff import Event, HandoffArea, HandoffAreaMember, HandoffLeg, TeamMember
from .legal import ConsumerRequest, LegalAcceptance
from .llm import LlmConnection
from .oauth import McpToolUsage, OAuthClient, OAuthCode, OAuthGrant, OAuthToken
from .tenancy import (
    ApiKey,
    ApiRequest,
    ApiUsageDaily,
    Client,
    ClientBranding,
    ClientLimitAdjustment,
    PhoneNumber,
    Role,
    Tier,
    User,
)
from .tools import AgentSecret, ClientSecret, ClientTool, Credential, ToolVersion
from .whatsapp import (
    WaAccount,
    WaMessage,
    WaRoute,
    WaThread,
)

__all__ = [
    "ACTIVE_CALL_STATUSES",
    "Agent",
    "AgentSecret",
    "AgentVersion",
    "ApiKey",
    "ApiRequest",
    "ApiUsageDaily",
    "BillingPayment",
    "BlockedNumber",
    "CallLink",
    "CallMode",
    "CallRow",
    "CallStatus",
    "Campaign",
    "CampaignCallback",
    "CampaignContact",
    "Client",
    "ClientSecret",
    "ClientTool",
    "Credential",
    "ClientBranding",
    "ClientLimitAdjustment",
    "ConsumerRequest",
    "Contact",
    "ContactOptout",
    "ContactRequest",
    "ConversationRow",
    "Event",
    "HandoffArea",
    "HandoffAreaMember",
    "HandoffLeg",
    "LegalAcceptance",
    "LlmConnection",
    "OAuthClient",
    "OAuthCode",
    "McpToolUsage",
    "OAuthGrant",
    "OAuthToken",
    "PhoneNumber",
    "Role",
    "Subscription",
    "TeamMember",
    "Tier",
    "ToolVersion",
    "User",
    "WaAccount",
    "WaMessage",
    "WaRoute",
    "WaThread",
]
