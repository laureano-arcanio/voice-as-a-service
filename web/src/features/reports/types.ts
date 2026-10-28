// Respuestas de /api/v1/reports/* (docs/REPORTES_PLAN.md, 9.2). Iguales a los Report*Out de schema.d.ts
// (make openapi); se escriben aca para nombrarlos por reporte (ReportByName).

import type { components } from '@/api/schema';

export type ReportName =
  'summary' | 'calls' | 'outcomes' | 'messages' | 'transfers' | 'campaigns' | 'technical' | 'platform';

export type Channel = 'voice' | 'whatsapp' | 'web';

export interface ReportQuery {
  client_id?: string;
  agent_id?: string;
  channel?: Channel;
  date_from: string;
  date_to: string;
  include_tests?: boolean;
}

/** Celda del mapa de calor: dia de la semana (0 = lunes) y hora local. */
export interface HeatCell {
  weekday: number;
  hour: number;
  count: number;
}

// --- Resumen ---

export interface SummaryKpis {
  conversations: number;
  by_channel: { voice_in: number; voice_out: number; whatsapp: number; web: number };
  /** Atendidas por un agente: la base de los porcentajes. */
  with_agent: number;
  conversions: number;
  conversion_pct: number | null;
  goals: number;
  goal_pct: number | null;
  transfers: number;
  transfers_answered: number;
  transfer_pct: number | null;
  minutes: number;
  finished: number;
  failed: number;
  avg_duration: number | null;
  rejected_by_limit: number;
  wa_messages: number;
}

export interface SummaryDay {
  date: string;
  voice_in: number;
  voice_out: number;
  whatsapp: number;
  web: number;
  transfers: number;
  transfers_answered: number;
}

export interface SummaryReport {
  period: { date_from: string; date_to: string };
  kpis: SummaryKpis;
  previous: SummaryKpis;
  daily: SummaryDay[];
}

// --- Llamadas ---

export interface CallsReport {
  /** Las llamadas del período, con cualquier estado: lo que suman `by_type` y `ended`. */
  total: number;
  daily: {
    date: string;
    entrante: number;
    saliente: number;
    directa: number;
    web: number;
    prueba: number;
  }[];
  heatmap: HeatCell[];
  by_line: {
    phone_number_id: string;
    number: string;
    calls: number;
    minutes: number;
    conversion_pct: number | null;
  }[];
  by_agent: {
    agent_id: string;
    agent_name: string;
    calls: number;
    minutes: number;
    avg_duration: number | null;
    conversion_pct: number | null;
    goal_pct: number | null;
  }[];
  /** Siempre los tres tipos, en este orden: agent, direct (la hace una persona) y team (entrante al equipo). */
  by_type: {
    type: 'agent' | 'direct' | 'team';
    calls: number;
    minutes: number;
    avg_duration: number | null;
  }[];
  by_user: {
    user_id: string;
    user_name: string;
    direct: number;
    team: number;
    calls: number;
    minutes: number;
    avg_duration: number | null;
  }[];
  durations: { bucket: string; count: number }[];
  ended: { reason: string; count: number }[];
  early_hangups: number;
  callers: { new: number; returning: number; top: { phone: string; count: number; last_at: string }[] };
}

// --- Resultados ---

export interface OutcomesReport {
  conversion_daily: { date: string; complete: number; partial: number; empty: number }[];
  by_agent: {
    agent_id: string;
    agent_name: string;
    total: number;
    complete: number;
    partial: number;
    empty: number;
    goal: number;
  }[];
  outcomes: {
    agent_id: string;
    agent_name: string;
    outcome: string;
    label: string;
    goal: boolean;
    count: number;
  }[];
  funnel: { conversations: number; with_data: number; complete: number; goal: number };
  fields: {
    agent_id: string;
    agent_name: string;
    field: string;
    label: string;
    captured: number;
    total: number;
    pct: number | null;
  }[];
  by_version: {
    agent_id: string;
    agent_name: string;
    version: number;
    total: number;
    conversion_pct: number | null;
    goal_pct: number | null;
  }[];
}

// --- Mensajes ---

export interface MessagesReport {
  daily: {
    date: string;
    inbound: number;
    outbound: number;
    inbound_audio: number;
    outbound_audio: number;
    conversations: number;
  }[];
  heatmap: HeatCell[];
  delivery: { sent: number; delivered: number; read: number; failed: number };
  failures: { code: string | number | null; message: string | null; count: number }[];
  per_conversation_avg: number | null;
  conversion: { complete: number; partial: number; empty: number };
  accounts: {
    account_id: string;
    display_phone_number: string | null;
    status: string | null;
    quality_rating: string | null;
    messaging_limit: string | null;
    history: {
      at: string;
      status: string | null;
      quality_rating: string | null;
      messaging_limit: string | null;
    }[];
  }[];
}

// --- Transferencias ---

export interface TransfersReport {
  kpis: {
    requested: number;
    answered: number;
    not_answered: number;
    unavailable: number;
    answer_pct: number | null;
    avg_answer_seconds: number | null;
    minutes: number;
  };
  daily: { date: string; requested: number; answered: number }[];
  by_area: {
    area_id: string | null;
    name: string;
    requested: number;
    answered: number;
    not_answered: number;
    unavailable: number;
  }[];
  by_member: {
    team_member_id: string;
    name: string;
    attempts: number;
    answered: number;
    not_answered: number;
    avg_answer_seconds: number | null;
    minutes: number;
  }[];
  whatsapp: {
    assigned: number;
    first_reply: number;
    avg_first_reply_seconds: number | null;
    reassigned: number;
  };
}

// --- Campañas ---

export interface CampaignsReport {
  campaigns: {
    campaign_id: string;
    name: string;
    channel: string;
    status: string;
    contacts: number;
    attempts: number;
    reached: number;
    complete: number;
    goal: number;
    optouts: number;
    minutes: number;
  }[];
  no_contact: { reason: string; count: number }[];
  best_hours: { weekday: number; hour: number; attempts: number; reached: number }[];
}

// --- Tecnico (admin) ---

export interface TechnicalReport {
  latency_daily: {
    date: string;
    p50: number | null;
    p95: number | null;
    stt_p50: number | null;
    eou_p50: number | null;
    llm_p50: number | null;
    tts_p50: number | null;
  }[];
  by_provider: {
    provider: string;
    model: string | null;
    turns: number;
    avg_ms: number | null;
    errors: number;
  }[];
  tools: {
    tool_id: string | null;
    slug: string;
    type: string;
    runs: number;
    errors: number;
    error_pct: number | null;
    p50_ms: number | null;
    p95_ms: number | null;
    last_error: string | null;
    last_error_at: string | null;
  }[];
  turns_avg: number | null;
  errors: { reason: string; count: number }[];
  failed_summary_emails: number;
  tokens: { input: number; output: number; by_day: { date: string; input: number; output: number }[] };
}

// --- Plataforma (admin, todos los clientes) ---

export interface PlatformClientRow {
  client_id: string;
  name: string;
  tier: string | null;
  conversations: number;
  minutes: number;
  quota_pct: number | null;
  conversion_pct: number | null;
  errors: number;
  last_activity_at: string | null;
  delta_pct: number | null;
}

export interface PlatformReport {
  clients: PlatformClientRow[];
  alerts: { client_id: string; name: string; kind: 'near_quota' | 'inactive'; detail: string }[];
  business: {
    clients_by_tier: { tier: string; count: number }[];
    signups: { date: string; count: number }[];
    mrr_ars: number;
    payments_month_ars: number;
    past_due: number;
    free_to_paid: number;
  };
  operation: {
    peak_concurrency: { date: string; hour: number; peak: number }[];
    failures: { date: string; reason: string; count: number }[];
    rejected: { reason: string; count: number }[];
  };
}

export interface ReportByName {
  summary: SummaryReport;
  calls: CallsReport;
  outcomes: OutcomesReport;
  messages: MessagesReport;
  transfers: TransfersReport;
  campaigns: CampaignsReport;
  technical: TechnicalReport;
  platform: PlatformReport;
}

// Chequeo de tipos: la respuesta del schema de la API (make openapi) tiene que servir donde se usan estos
// tipos; si el backend cambia o saca un campo, falla `npm run typecheck`.
type Schemas = components['schemas'];
type Fits<A, B> = [A] extends [B] ? true : never;
export const reportTypesMatchApi: [
  Fits<Schemas['ReportSummaryOut'], SummaryReport>,
  Fits<Schemas['ReportCallsOut'], CallsReport>,
  Fits<Schemas['ReportOutcomesOut'], OutcomesReport>,
  Fits<Schemas['ReportMessagesOut'], MessagesReport>,
  Fits<Schemas['ReportTransfersOut'], TransfersReport>,
  Fits<Schemas['ReportCampaignsOut'], CampaignsReport>,
  Fits<Schemas['ReportTechnicalOut'], TechnicalReport>,
  Fits<Schemas['ReportPlatformOut'], PlatformReport>,
] = [true, true, true, true, true, true, true, true];
