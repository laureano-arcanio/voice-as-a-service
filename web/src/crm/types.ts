// Tipos de la API del CRM (crm/schemas.py, docs/CRM_API.md). Escritos a mano: el CRM es otra API.
// Las fechas con hora vienen en UTC sin zona ("2026-10-21T13:00:00"); las fechas solas, "2026-10-21".

export type Stage =
  | 'nuevo'
  | 'contactado'
  | 'seguimiento'
  | 'respondio'
  | 'charla_agendada'
  | 'charla_hecha'
  | 'propuesta'
  | 'piloto'
  | 'cliente'
  | 'sin_respuesta'
  | 'no_interesa'
  | 'descartado';

export type ContactKind = 'email' | 'phone' | 'whatsapp' | 'linkedin' | 'form';
export type ContactLabel = 'persona' | 'area' | 'atencion';
export type MessageKind = 'first' | 'follow_up' | 'other';
export type LeadKind = 'cliente' | 'canal';

export interface Source {
  id: number;
  url: string;
  title: string | null;
  seen_at: string | null;
  note: string | null;
}

export interface Person {
  id: number;
  name: string;
  title: string | null;
  is_decision_maker: boolean;
  linkedin_url: string | null;
  notes: string | null;
  source_id: number | null;
}

export interface ContactPoint {
  id: number;
  kind: ContactKind;
  value: string;
  label: ContactLabel | null;
  person_id: number | null;
  is_primary: boolean;
  status: string;
  verified_at: string | null;
  source_id: number | null;
}

export interface LeadSummary {
  id: number;
  slug: string;
  name: string;
  domain: string | null;
  website: string | null;
  description: string | null;
  kind: LeadKind | null;
  industry: string | null;
  tags: string[];
  city: string | null;
  province: string | null;
  stage: Stage;
  stage_changed_at: string;
  next_action: string | null;
  next_action_at: string | null;
  do_not_contact: boolean;
  legacy_ref: string | null;
  primary_email: string | null;
  last_out_at: string | null;
  last_in_at: string | null;
  ga_users: number;
}

export interface Lead extends LeadSummary {
  legal_name: string | null;
  country: string | null;
  notes: string | null;
  created_by: string;
  created_at: string;
  people: Person[];
  contacts: ContactPoint[];
  sources: Source[];
}

export interface Page<T> {
  total: number;
  items: T[];
}

export interface LeadPatch {
  name?: string;
  website?: string | null;
  legal_name?: string | null;
  description?: string | null;
  kind?: LeadKind | null;
  industry?: string | null;
  tags?: string[];
  country?: string | null;
  province?: string | null;
  city?: string | null;
  stage?: Stage;
  next_action?: string | null;
  next_action_at?: string | null;
  do_not_contact?: boolean;
  notes?: string | null;
}

export interface ContactIn {
  kind: ContactKind;
  value: string;
  label?: ContactLabel | null;
  person?: string | null;
  is_primary?: boolean | null;
  source_url?: string | null;
}

export interface PersonIn {
  name: string;
  title?: string | null;
  is_decision_maker?: boolean | null;
  linkedin_url?: string | null;
  source_url?: string | null;
}

export interface LeadUpsert extends LeadPatch {
  domain?: string | null;
  slug?: string | null;
  sources?: { url: string; seen_at?: string | null; title?: string | null; note?: string | null }[];
  people?: PersonIn[];
  contacts?: ContactIn[];
}

export interface UpsertResult {
  result: 'created' | 'updated';
  lead: Lead;
}

export interface CampaignStats {
  leads: number;
  first_sent: number;
  follow_up_sent: number;
  drafts: number;
  queued: number;
  bounced: number;
  replies: number;
  ga_users: number;
}

export interface Campaign {
  id: number;
  slug: string;
  name: string;
  channel: 'email' | 'linkedin' | 'phone';
  segment: string | null;
  from_addr: string | null;
  status: 'draft' | 'active' | 'done';
  started_at: string | null;
  notes: string | null;
  created_at: string;
  stats: Partial<CampaignStats>;
}

export interface CampaignIn {
  slug: string;
  name: string;
  channel?: 'email' | 'linkedin' | 'phone';
  segment?: string | null;
  from_addr?: string | null;
  status?: 'draft' | 'active' | 'done';
  started_at?: string | null;
  notes?: string | null;
}

export interface Template {
  id: number;
  name: string;
  kind: MessageKind;
  subject: string;
  body: string;
  body_personal: string | null;
  archived: boolean;
  updated_at: string;
}

export interface TemplateIn {
  name: string;
  kind: MessageKind;
  subject: string;
  body: string;
  body_personal?: string | null;
  archived?: boolean;
}

export interface Preview {
  to: string | null;
  subject: string;
  text: string;
}

export type MessageStatus =
  'draft' | 'queued' | 'sent' | 'delivered' | 'bounced' | 'complained' | 'failed' | 'canceled' | 'received';

export interface Message {
  id: number;
  lead_id: number;
  campaign_id: number | null;
  kind: MessageKind;
  direction: 'out' | 'in';
  from_addr: string | null;
  to_addr: string;
  subject: string;
  text: string;
  status: MessageStatus;
  resend_id: string | null;
  message_id: string | null;
  in_reply_to: string | null;
  utm_campaign: string | null;
  error: string | null;
  created_by: string;
  created_at: string;
  queued_at: string | null;
  sent_at: string | null;
  lead_name: string | null;
  campaign_slug: string | null;
}

export interface BulkDraftResult {
  created: Message[];
  skipped: { lead_id: number; reason: string }[];
}

export type ActivityKind = 'note' | 'call' | 'meeting' | 'linkedin' | 'task' | 'stage_change';

export interface Activity {
  id: number;
  lead_id: number;
  person_id: number | null;
  kind: ActivityKind;
  at: string;
  text: string;
  data: Record<string, unknown>;
  due_at: string | null;
  done: boolean;
  created_by: string;
}

export interface GaVisit {
  date: string;
  source_medium: string;
  utm_campaign: string;
  utm_content: string;
  active_users: number;
  sessions: number;
  events: number;
  lead_id: number | null;
  campaign_id: number | null;
  follow_up: boolean;
}

export type TimelineItem =
  | { type: 'message'; at: string; data: Message }
  | { type: 'activity'; at: string; data: Activity }
  | { type: 'visit'; at: string; data: GaVisit };

export interface QueueStatus {
  enabled: boolean;
  queued: number;
  sent_today: number;
  daily_max: number;
  in_hours: boolean;
  hours: string;
  window_seconds: number;
  next_at: string | null;
}

export interface FollowUpDue {
  lead: LeadSummary;
  campaign_id: number | null;
  campaign_slug: string | null;
  first_message_id: number;
  sent_at: string;
  business_days: number;
}

export interface Today {
  follow_ups_due: FollowUpDue[];
  drafts: Message[];
  tasks: Activity[];
  replies: Message[];
  next_actions: LeadSummary[];
  queue: QueueStatus;
}

export interface Stats {
  leads: number;
  by_stage: Record<Stage, number>;
  contacted: number;
  followed_up: number;
  replied: number;
  bounced_addresses: number;
  with_clicks: number;
  sent_last_7d: number;
}
