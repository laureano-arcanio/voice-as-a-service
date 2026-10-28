"""Agenda de contactos y campañas unificadas (docs/features/CAMPANAS.md, fase 1).

- contacts, contact_optouts, campaigns y campaign_contacts nuevas.
- Los datos de WhatsApp se copian a las nuevas y se borran las viejas (wa_campaigns,
  wa_campaign_recipients, wa_optouts): las campañas con channel='whatsapp' conservan su id; cada
  wa_id distinto de un cliente es un contacto (+ el wa_id, source 'campaign'); los destinatarios
  guardan los parametros de la plantilla en vars['params']; las bajas quedan con channel
  'whatsapp'. Estados: sending -> in_progress, sent -> done con result 'sent'.
- tiers: campaign_channels (los existentes quedan con ["whatsapp"]), max_campaigns_per_month,
  max_campaign_contacts, max_campaign_concurrency, max_contacts y campaign_followup; sin topes.
- call_logs: campaign_contact_id y sip_status.
- Fase 4: campaigns.no_call_confirmed_at, el seguimiento por WhatsApp de campaign_contacts
  (followup_sent_at, followup_error, followup_conversation_id) y campaign_callbacks (outbox del webhook).

Downgrade: vuelve a las tablas de WhatsApp con sus datos (scheduled -> draft, done -> sent). Se
pierden la agenda de contactos, las campañas de voz y lo que solo existe en las nuevas.

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-19
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

JSONDoc = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
CHUNK = 1000

TIER_CHECKS = {
    "max_campaigns_per_month": "ck_tiers_campaigns_month",
    "max_campaign_contacts": "ck_tiers_campaign_contacts",
    "max_campaign_concurrency": "ck_tiers_campaign_concurrency",
    "max_contacts": "ck_tiers_contacts",
}
# Estado viejo de un destinatario de WhatsApp -> (status, result) nuevo.
NEW_STATUS = {"pending": ("pending", None), "sending": ("in_progress", None), "sent": ("done", "sent"),
              "failed": ("failed", None), "skipped": ("skipped", None)}


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _tables():
    """Las tablas viejas y las nuevas, solo con las columnas que se copian."""
    dt = sa.DateTime
    old_campaigns = sa.table("wa_campaigns", sa.column("id"), sa.column("client_id"))
    old_recipients = sa.table(
        "wa_campaign_recipients", sa.column("id"), sa.column("campaign_id"), sa.column("wa_id"), sa.column("name"),
        sa.column("params", JSONDoc), sa.column("status"), sa.column("error", JSONDoc), sa.column("wamid"),
        sa.column("sent_at", dt), sa.column("conversation_id"), sa.column("replied_at", dt),
        sa.column("created_at", dt))
    contacts = sa.table("contacts", sa.column("id"), sa.column("created_at", dt), sa.column("updated_at", dt),
                        sa.column("client_id"), sa.column("phone"), sa.column("name"), sa.column("attributes", JSONDoc),
                        sa.column("tags", JSONDoc), sa.column("source"))
    members = sa.table(
        "campaign_contacts", sa.column("id"), sa.column("campaign_id"), sa.column("contact_id"),
        sa.column("vars", JSONDoc), sa.column("status"), sa.column("result"), sa.column("error", JSONDoc),
        sa.column("conversation_id"), sa.column("created_at", dt), sa.column("wamid"), sa.column("sent_at", dt),
        sa.column("replied_at", dt), sa.column("attempts", sa.Integer))
    return old_campaigns, old_recipients, contacts, members


def _create_campaign_tables() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("name", sa.String(128), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("attributes", JSONDoc, nullable=False),
        sa.Column("tags", JSONDoc, nullable=False),
        sa.Column("source", sa.String(16), nullable=False, server_default="manual"),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("client_id", "phone", name="uq_contacts_client_phone"),
        sa.CheckConstraint(_in("source", ("manual", "csv", "api", "campaign", "inbound")), name="ck_contacts_source"),
    )
    op.create_index("ix_contacts_client_archived", "contacts", ["client_id", "archived_at"])

    op.create_table(
        "contact_optouts",
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("phone", sa.String(20), primary_key=True),
        sa.Column("channel", sa.String(16), primary_key=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(_in("channel", ("whatsapp", "voice", "all")), name="ck_contact_optouts_channel"),
        sa.CheckConstraint(_in("source", ("keyword", "outcome", "manual")), name="ck_contact_optouts_source"),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("status_reason", sa.String(255), nullable=True),
        sa.Column("rate_per_minute", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("window_start", sa.Integer(), nullable=False, server_default="9"),
        sa.Column("window_end", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("weekdays", JSONDoc, nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("purpose", sa.String(16), nullable=True),
        sa.Column("no_call_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_campaigns_created_by_users"),
                  nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("callback_url", sa.String(512), nullable=True),
        sa.Column("callback_secret", sa.Text(), nullable=True),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("wa_accounts.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("template_name", sa.String(512), nullable=True),
        sa.Column("template_language", sa.String(16), nullable=True),
        sa.Column("template_category", sa.String(32), nullable=False, server_default=""),
        sa.Column("template_body", sa.Text(), nullable=False, server_default=""),
        sa.Column("template_params", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("template_param_names", JSONDoc, nullable=True),
        sa.Column("from_number_id", sa.String(36), sa.ForeignKey("phone_numbers.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("voice", sa.String(64), nullable=True),
        sa.Column("concurrency", sa.Integer(), nullable=True),
        sa.Column("max_attempts", sa.Integer(), nullable=True),
        sa.Column("retry_minutes", sa.Integer(), nullable=True),
        sa.Column("retry_on", JSONDoc, nullable=True),
        sa.Column("followup", JSONDoc, nullable=True),
        sa.CheckConstraint(_in("channel", ("whatsapp", "voice")), name="ck_campaigns_channel"),
        sa.CheckConstraint(_in("status", ("draft", "scheduled", "running", "paused", "done", "cancelled")),
                           name="ck_campaigns_status"),
        sa.CheckConstraint("purpose IS NULL OR " + _in("purpose", ("comercial", "cobranza", "turnos", "aviso")),
                           name="ck_campaigns_purpose"),
        sa.CheckConstraint("rate_per_minute > 0", name="ck_campaigns_rate"),
        sa.CheckConstraint("window_start >= 0 AND window_start <= 23 AND window_end >= 1 AND window_end <= 24 "
                           "AND window_start < window_end", name="ck_campaigns_window"),
        sa.CheckConstraint("channel <> 'whatsapp' OR (account_id IS NOT NULL AND template_name IS NOT NULL "
                           "AND template_language IS NOT NULL)", name="ck_campaigns_whatsapp_fields"),
        sa.CheckConstraint("channel <> 'voice' OR concurrency IS NOT NULL", name="ck_campaigns_voice_fields"),
        sa.CheckConstraint("concurrency IS NULL OR concurrency >= 1", name="ck_campaigns_concurrency"),
    )
    op.create_index("ix_campaigns_client_id", "campaigns", ["client_id"])
    op.create_index("ix_campaigns_account_id", "campaigns", ["account_id"])

    op.create_table(
        "campaign_contacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.String(36), sa.ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("vars", JSONDoc, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("result", sa.String(16), nullable=True),
        sa.Column("error", JSONDoc, nullable=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("wamid", sa.String(128), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("replied_at", sa.DateTime(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("followup_status", sa.String(16), nullable=True),
        sa.Column("followup_wamid", sa.String(128), nullable=True),
        sa.Column("followup_sent_at", sa.DateTime(), nullable=True),
        sa.Column("followup_error", JSONDoc, nullable=True),
        sa.Column("followup_conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="SET NULL"),
                  nullable=True),
        sa.CheckConstraint(_in("status", ("pending", "in_progress", "retry", "done", "failed", "skipped")),
                           name="ck_campaign_contacts_status"),
        sa.CheckConstraint("followup_status IS NULL OR " + _in(
            "followup_status", ("pending", "in_progress", "sent", "failed", "skipped")),
            name="ck_campaign_contacts_followup_status"),
        sa.CheckConstraint("result IS NULL OR " + _in("result", (
            "sent", "delivered", "read", "replied", "answered", "no_answer", "busy", "voicemail", "invalid",
            "rejected", "failed")), name="ck_campaign_contacts_result"),
        sa.UniqueConstraint("campaign_id", "contact_id", name="uq_campaign_contacts_campaign_contact"),
    )
    op.create_index("ix_campaign_contacts_campaign_status", "campaign_contacts", ["campaign_id", "status"])
    op.create_index("ix_campaign_contacts_contact_sent", "campaign_contacts", ["contact_id", "sent_at"])
    op.create_index("ix_campaign_contacts_wamid", "campaign_contacts", ["wamid"])
    op.create_index("ix_campaign_contacts_campaign_followup", "campaign_contacts", ["campaign_id", "followup_status"])

    op.create_table(
        "campaign_callbacks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_contact_id", sa.String(36), sa.ForeignKey("campaign_contacts.id", ondelete="CASCADE"),
                  nullable=True),
        sa.Column("event", sa.String(24), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(_in("event", ("contact.finished", "contact.followup", "campaign.finished")),
                           name="ck_campaign_callbacks_event"),
        sa.CheckConstraint(_in("status", ("pending", "sent", "failed")), name="ck_campaign_callbacks_status"),
    )
    op.create_index("ix_campaign_callbacks_campaign_id", "campaign_callbacks", ["campaign_id"])
    op.create_index("ix_campaign_callbacks_status_next", "campaign_callbacks", ["status", "next_attempt_at"])


def _create_whatsapp_tables() -> None:
    """Las de la migracion 0008, para el downgrade."""
    op.create_table(
        "wa_campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("wa_accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("template_name", sa.String(512), nullable=False),
        sa.Column("template_language", sa.String(16), nullable=False),
        sa.Column("template_category", sa.String(32), nullable=False, server_default=""),
        sa.Column("template_body", sa.Text(), nullable=False, server_default=""),
        sa.Column("template_params", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("status_reason", sa.String(255), nullable=True),
        sa.Column("rate_per_minute", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("window_start", sa.Integer(), nullable=False, server_default="9"),
        sa.Column("window_end", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("created_by", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_wa_campaigns_created_by_users"),
                  nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'running', 'paused', 'done', 'cancelled')",
                           name="ck_wa_campaigns_status"),
        sa.CheckConstraint("rate_per_minute > 0", name="ck_wa_campaigns_rate"),
        sa.CheckConstraint("window_start >= 0 AND window_start <= 23 AND window_end >= 1 AND window_end <= 24 "
                           "AND window_start < window_end", name="ck_wa_campaigns_window"),
    )
    op.create_index("ix_wa_campaigns_client_id", "wa_campaigns", ["client_id"])
    op.create_index("ix_wa_campaigns_account_id", "wa_campaigns", ["account_id"])
    op.create_table(
        "wa_campaign_recipients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("wa_campaigns.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("wa_id", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=True),
        sa.Column("params", JSONDoc, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("error", JSONDoc, nullable=True),
        sa.Column("wamid", sa.String(128), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("replied_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'sending', 'sent', 'failed', 'skipped')",
                           name="ck_wa_campaign_recipients_status"),
        sa.UniqueConstraint("campaign_id", "wa_id", name="uq_wa_campaign_recipients_campaign_waid"),
    )
    op.create_index("ix_wa_campaign_recipients_campaign_status", "wa_campaign_recipients", ["campaign_id", "status"])
    op.create_index("ix_wa_campaign_recipients_waid_sent", "wa_campaign_recipients", ["wa_id", "sent_at"])
    op.create_index("ix_wa_campaign_recipients_wamid", "wa_campaign_recipients", ["wamid"])
    op.create_table(
        "wa_optouts",
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("wa_id", sa.String(32), primary_key=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def _chunks(rows: list, size: int = CHUNK):
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


def upgrade() -> None:
    with op.batch_alter_table("tiers") as batch:
        batch.add_column(sa.Column("campaign_channels", JSONDoc, nullable=False, server_default=sa.text("'[]'")))
        for name in TIER_CHECKS:
            batch.add_column(sa.Column(name, sa.Integer(), nullable=True))
        batch.add_column(sa.Column("campaign_followup", sa.Boolean(), nullable=False, server_default=sa.false()))
        for name, check in TIER_CHECKS.items():
            batch.create_check_constraint(check, f"{name} IS NULL OR {name} >= 0")
    # Los clientes que ya usan campañas de WhatsApp no se cortan: despues se ajusta plan por plan.
    op.execute(sa.text("""UPDATE tiers SET campaign_channels = '["whatsapp"]'"""))

    _create_campaign_tables()
    conn = op.get_bind()

    # Campañas: mismo id, channel 'whatsapp' (weekdays NULL: todos los dias, como antes).
    op.execute(sa.text(
        "INSERT INTO campaigns (id, created_at, updated_at, client_id, agent_id, name, channel, status, "
        "status_reason, rate_per_minute, window_start, window_end, created_by, started_at, finished_at, "
        "account_id, template_name, template_language, template_category, template_body, template_params) "
        "SELECT id, created_at, updated_at, client_id, agent_id, name, 'whatsapp', status, status_reason, "
        "rate_per_minute, window_start, window_end, created_by, started_at, finished_at, account_id, "
        "template_name, template_language, template_category, template_body, template_params FROM wa_campaigns"))

    # Un contacto por cada wa_id distinto de cada cliente; los destinatarios apuntan a el.
    old_campaigns, old_recipients, contacts, members = _tables()
    rows = conn.execute(
        sa.select(old_recipients, old_campaigns.c.client_id.label("client_id"))
        .select_from(old_recipients.join(old_campaigns, old_campaigns.c.id == old_recipients.c.campaign_id))
        .order_by(old_recipients.c.created_at, old_recipients.c.id)).all()
    contact_ids: dict[tuple[str, str], str] = {}
    new_contacts: dict[tuple[str, str], dict] = {}
    for r in rows:
        key = (r.client_id, r.wa_id)
        if key not in contact_ids:
            contact_ids[key] = str(uuid.uuid4())
            new_contacts[key] = {"id": contact_ids[key], "created_at": r.created_at, "updated_at": r.created_at,
                                 "client_id": r.client_id, "phone": "+" + r.wa_id, "name": r.name,
                                 "attributes": {}, "tags": [], "source": "campaign"}
        elif not new_contacts[key]["name"] and r.name:
            new_contacts[key]["name"] = r.name
    for chunk in _chunks(list(new_contacts.values())):
        conn.execute(sa.insert(contacts), chunk)
    members_rows = []
    for r in rows:
        status, result = NEW_STATUS[r.status]
        vars_ = {"params": list(r.params or [])}
        if r.name:
            vars_["nombre"] = r.name
        members_rows.append({
            "id": r.id, "campaign_id": r.campaign_id, "contact_id": contact_ids[(r.client_id, r.wa_id)],
            "vars": vars_, "status": status, "result": result, "error": r.error, "conversation_id": r.conversation_id,
            "created_at": r.created_at, "wamid": r.wamid, "sent_at": r.sent_at, "replied_at": r.replied_at,
            "attempts": 0})
    for chunk in _chunks(members_rows):
        conn.execute(sa.insert(members), chunk)

    op.execute(sa.text(
        "INSERT INTO contact_optouts (client_id, phone, channel, source, created_at) "
        "SELECT client_id, '+' || wa_id, 'whatsapp', source, created_at FROM wa_optouts"))

    op.drop_table("wa_campaign_recipients")
    op.drop_table("wa_campaigns")
    op.drop_table("wa_optouts")

    with op.batch_alter_table("call_logs") as batch:
        batch.add_column(sa.Column("campaign_contact_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("sip_status", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_call_logs_campaign_contact_id", "campaign_contacts", ["campaign_contact_id"],
                                 ["id"], ondelete="SET NULL")
        batch.create_index("ix_call_logs_campaign_contact_id", ["campaign_contact_id"])


def downgrade() -> None:
    with op.batch_alter_table("call_logs") as batch:
        batch.drop_index("ix_call_logs_campaign_contact_id")
        batch.drop_constraint("fk_call_logs_campaign_contact_id", type_="foreignkey")
        batch.drop_column("sip_status")
        batch.drop_column("campaign_contact_id")

    _create_whatsapp_tables()
    conn = op.get_bind()
    _, old_recipients, contacts, members = _tables()

    # Solo las campañas de WhatsApp vuelven (las de voz no tienen donde). scheduled -> draft.
    op.execute(sa.text(
        "INSERT INTO wa_campaigns (id, created_at, updated_at, client_id, account_id, agent_id, name, "
        "template_name, template_language, template_category, template_body, template_params, status, "
        "status_reason, rate_per_minute, window_start, window_end, created_by, started_at, finished_at) "
        "SELECT id, created_at, updated_at, client_id, account_id, agent_id, name, template_name, "
        "template_language, template_category, template_body, template_params, "
        "CASE WHEN status = 'scheduled' THEN 'draft' ELSE status END, status_reason, rate_per_minute, "
        "window_start, window_end, created_by, started_at, finished_at FROM campaigns WHERE channel = 'whatsapp'"))

    campaigns = sa.table("campaigns", sa.column("id"), sa.column("channel"))
    rows = conn.execute(
        sa.select(members, contacts.c.phone.label("phone"), contacts.c.name.label("contact_name"))
        .select_from(members.join(contacts, contacts.c.id == members.c.contact_id)
                     .join(campaigns, campaigns.c.id == members.c.campaign_id))
        .where(campaigns.c.channel == "whatsapp")
        .order_by(members.c.created_at, members.c.id)).all()
    old_status = {"pending": "pending", "retry": "pending", "in_progress": "sending", "done": "sent",
                  "failed": "failed", "skipped": "skipped"}
    out = [{"id": r.id, "campaign_id": r.campaign_id, "wa_id": r.phone.removeprefix("+"), "name": r.contact_name,
            "params": list((r.vars or {}).get("params") or []), "status": old_status[r.status], "error": r.error,
            "wamid": r.wamid, "sent_at": r.sent_at, "conversation_id": r.conversation_id,
            "replied_at": r.replied_at, "created_at": r.created_at} for r in rows]
    for chunk in _chunks(out):
        conn.execute(sa.insert(old_recipients), chunk)

    # Una baja por wa_id: la de WhatsApp y la de todos los canales valen para WhatsApp.
    op.execute(sa.text(
        "INSERT INTO wa_optouts (client_id, wa_id, source, created_at) "
        "SELECT client_id, substr(phone, 2), min(source), min(created_at) FROM contact_optouts "
        "WHERE channel IN ('whatsapp', 'all') GROUP BY client_id, phone"))

    op.drop_table("campaign_callbacks")
    op.drop_table("campaign_contacts")
    op.drop_table("campaigns")
    op.drop_table("contact_optouts")
    op.drop_table("contacts")

    with op.batch_alter_table("tiers") as batch:
        for check in TIER_CHECKS.values():
            batch.drop_constraint(check, type_="check")
        for name in ("campaign_followup", *TIER_CHECKS, "campaign_channels"):
            batch.drop_column(name)
