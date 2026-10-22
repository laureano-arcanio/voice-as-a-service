// Cliente de la API del CRM: key en localStorage, Authorization: Bearer y errores problem+json.
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSyncExternalStore } from 'react';
import { ApiError } from '@/api/errors';
import type {
  Activity,
  BulkDraftResult,
  Campaign,
  CampaignIn,
  ContactIn,
  Lead,
  LeadPatch,
  LeadSummary,
  LeadUpsert,
  Message,
  MessageChannel,
  MessageKind,
  Page,
  PersonIn,
  Preview,
  QueueStatus,
  Stats,
  Template,
  TemplateIn,
  TimelineItem,
  Today,
  UpsertResult,
} from './types';

// --- Key ---

const KEY_STORAGE = 'atentina-crm-key';
const listeners = new Set<() => void>();
let memoryKey: string | null = null;

function readKey(): string | null {
  try {
    return localStorage.getItem(KEY_STORAGE) ?? memoryKey;
  } catch {
    return memoryKey;
  }
}

export function setApiKey(key: string | null) {
  memoryKey = key;
  try {
    if (key) localStorage.setItem(KEY_STORAGE, key);
    else localStorage.removeItem(KEY_STORAGE);
  } catch {
    // Sin storage (ventana privada): queda en memoria.
  }
  listeners.forEach((l) => l());
}

export function useApiKey(): string | null {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    readKey,
    () => null,
  );
}

// --- Pedidos ---

type Query = Record<string, string | number | boolean | null | undefined>;

function qs(params?: Query): string {
  if (!params) return '';
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : '';
}

/** problem+json -> ApiError con el `detail` (y los errores de cada campo, si vienen). */
async function toError(r: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await r.json();
  } catch {
    // sin cuerpo
  }
  const obj = (body && typeof body === 'object' ? body : {}) as Record<string, unknown>;
  const detail = typeof obj.detail === 'string' && obj.detail ? obj.detail : `Error ${r.status}`;
  const errors = Array.isArray(obj.errors)
    ? (obj.errors as { field?: string; msg?: string }[]).map((e) => ({
        path: e.field ?? '',
        message: e.msg ?? '',
      }))
    : typeof obj.field === 'string'
      ? [{ path: obj.field, message: detail }]
      : [];
  return new ApiError(r.status, detail, undefined, errors);
}

export async function api<T>(method: string, path: string, body?: unknown, params?: Query): Promise<T> {
  const key = readKey();
  const r = await fetch(`/api${path}${qs(params)}`, {
    method,
    headers: {
      ...(key ? { Authorization: `Bearer ${key}` } : {}),
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (r.status === 401) {
    setApiKey(null);
    throw await toError(r);
  }
  if (!r.ok) throw await toError(r);
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

// --- Hooks ---

export interface LeadFilters {
  q?: string;
  stage?: string;
  tag?: string;
  industry?: string;
  kind?: string;
  campaign_id?: number | null;
  has_clicks?: boolean | null;
  pending?: 'draft' | 'queued' | 'follow_up';
  limit?: number;
  offset?: number;
}

export const LEADS_PAGE = 100;

export function useLeads(f: LeadFilters) {
  return useQuery({
    queryKey: ['crm', 'leads', f],
    queryFn: () => api<Page<LeadSummary>>('GET', '/leads', undefined, { ...f }),
    placeholderData: keepPreviousData,
  });
}

export function useLead(id: number) {
  return useQuery({ queryKey: ['crm', 'lead', id], queryFn: () => api<Lead>('GET', `/leads/${id}`) });
}

export function useTimeline(id: number) {
  return useQuery({
    queryKey: ['crm', 'timeline', id],
    queryFn: () => api<TimelineItem[]>('GET', `/leads/${id}/timeline`),
  });
}

export function useToday() {
  return useQuery({
    queryKey: ['crm', 'today'],
    queryFn: () => api<Today>('GET', '/today'),
    // Mientras se revisan los eventos en Resend, mas seguido: se ve cuando termina.
    refetchInterval: (q) => (q.state.data?.queue.events_running ? 3_000 : 60_000),
  });
}

export function useQueue() {
  return useQuery({
    queryKey: ['crm', 'queue'],
    queryFn: () => api<QueueStatus>('GET', '/queue'),
    refetchInterval: 15_000,
  });
}

export function useStats() {
  return useQuery({ queryKey: ['crm', 'stats'], queryFn: () => api<Stats>('GET', '/stats') });
}

export function useCampaigns() {
  return useQuery({ queryKey: ['crm', 'campaigns'], queryFn: () => api<Campaign[]>('GET', '/campaigns') });
}

export function useCampaign(id: number) {
  return useQuery({
    queryKey: ['crm', 'campaign', id],
    queryFn: () => api<Campaign>('GET', `/campaigns/${id}`),
  });
}

export function useTemplates(archived = false) {
  return useQuery({
    queryKey: ['crm', 'templates', archived],
    queryFn: () => api<Template[]>('GET', '/templates', undefined, { archived }),
  });
}

export interface MessageFilters {
  lead_id?: number;
  campaign_id?: number | null;
  status?: string | null;
  direction?: string | null;
  kind?: string | null;
  limit?: number;
  offset?: number;
}

export const MESSAGES_PAGE = 100;

export function useMessages(f: MessageFilters) {
  return useQuery({
    queryKey: ['crm', 'messages', f],
    queryFn: () => api<Page<Message>>('GET', '/messages', undefined, { ...f }),
    placeholderData: keepPreviousData,
  });
}

/** Cualquier cambio invalida todo el CRM: es chico y local, no vale la pena afinar. */
function useInvalidate() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ['crm'] });
}

function useCrmMutation<V, R>(fn: (v: V) => Promise<R>) {
  const invalidate = useInvalidate();
  return useMutation({ mutationFn: fn, onSuccess: () => invalidate() });
}

export const useUpsertLead = () => useCrmMutation((b: LeadUpsert) => api<UpsertResult>('POST', '/leads', b));

export const usePatchLead = () =>
  useCrmMutation(({ id, ...b }: LeadPatch & { id: number }) => api<Lead>('PATCH', `/leads/${id}`, b));

export const useAddContact = () =>
  useCrmMutation(({ leadId, ...b }: ContactIn & { leadId: number }) =>
    api('POST', `/leads/${leadId}/contacts`, b),
  );

export const usePatchContact = () =>
  useCrmMutation(({ id, ...b }: Partial<ContactIn> & { id: number }) => api('PATCH', `/contacts/${id}`, b));

export const useDeleteContact = () => useCrmMutation((id: number) => api('DELETE', `/contacts/${id}`));

export const useAddPerson = () =>
  useCrmMutation(({ leadId, ...b }: PersonIn & { leadId: number }) =>
    api('POST', `/leads/${leadId}/people`, b),
  );

export const useDeletePerson = () => useCrmMutation((id: number) => api('DELETE', `/people/${id}`));

export const useAddSource = () =>
  useCrmMutation(
    ({ leadId, ...b }: { leadId: number; url: string; seen_at?: string | null; note?: string }) =>
      api('POST', `/leads/${leadId}/sources`, b),
  );

export interface ActivityIn {
  kind: 'note' | 'call' | 'meeting' | 'linkedin' | 'task';
  text: string;
  at?: string | null;
  due_at?: string | null;
  done?: boolean;
}

export const useAddActivity = () =>
  useCrmMutation(({ leadId, ...b }: ActivityIn & { leadId: number }) =>
    api<Activity>('POST', `/leads/${leadId}/activities`, b),
  );

export const usePatchActivity = () =>
  useCrmMutation(({ id, ...b }: { id: number; done?: boolean; text?: string }) =>
    api<Activity>('PATCH', `/activities/${id}`, b),
  );

export const useInbound = () =>
  useCrmMutation(
    ({
      leadId,
      ...b
    }: {
      leadId: number;
      channel: MessageChannel;
      from_addr: string;
      subject: string;
      text: string;
      at?: string | null;
      auto_reply?: boolean;
    }) => api<Message>('POST', `/leads/${leadId}/inbound`, b),
  );

export const useCreateCampaign = () =>
  useCrmMutation((b: CampaignIn) => api<Campaign>('POST', '/campaigns', b));

export const usePatchCampaign = () =>
  useCrmMutation(({ id, ...b }: Partial<CampaignIn> & { id: number }) =>
    api<Campaign>('PATCH', `/campaigns/${id}`, b),
  );

export const useBulkDrafts = () =>
  useCrmMutation(
    ({
      campaignId,
      ...b
    }: {
      campaignId: number;
      lead_ids: number[];
      template_id: number;
      kind: MessageKind;
    }) => api<BulkDraftResult>('POST', `/campaigns/${campaignId}/drafts`, b),
  );

export const useFollowUpDrafts = () =>
  useCrmMutation((b: { lead_ids: number[]; template_id?: number | null }) =>
    api<BulkDraftResult>('POST', '/followups/drafts', b),
  );

export const useCheckEvents = () =>
  useCrmMutation(() => api<{ started: boolean; running: boolean }>('POST', '/events/check'));

export const useCreateTemplate = () =>
  useCrmMutation((b: TemplateIn) => api<Template>('POST', '/templates', b));

export const usePatchTemplate = () =>
  useCrmMutation(({ id, ...b }: Partial<TemplateIn> & { id: number }) =>
    api<Template>('PATCH', `/templates/${id}`, b),
  );

export const previewTemplate = (
  id: number,
  b: { lead_id: number; campaign_id?: number | null; kind: MessageKind },
) => api<Preview>('POST', `/templates/${id}/preview`, b);

export interface DraftIn {
  lead_id: number;
  campaign_id?: number | null;
  kind: MessageKind;
  template_id?: number | null;
  subject?: string | null;
  text?: string | null;
  to?: string | null;
}

export const useCreateDraft = () => useCrmMutation((b: DraftIn) => api<Message>('POST', '/messages', b));

export const useEditDraft = () =>
  useCrmMutation(({ id, ...b }: DraftIn & { id: number }) => api<Message>('PATCH', `/messages/${id}`, b));

/** Corregir una respuesta ya registrada (no cambia la etapa del lead). */
export const useEditInbound = () =>
  useCrmMutation(
    ({
      id,
      ...b
    }: {
      id: number;
      channel: MessageChannel;
      from_addr: string;
      subject: string;
      text: string;
    }) => api<Message>('PATCH', `/messages/${id}`, b),
  );

export const useAssignInbound = () =>
  useCrmMutation(({ id, lead_id }: { id: number; lead_id: number }) =>
    api<Message>('POST', `/inbox/${id}/assign`, { lead_id }),
  );

export const useIgnoreInbound = () => useCrmMutation((id: number) => api('POST', `/inbox/${id}/ignore`));

export const useApprove = () =>
  useCrmMutation((ids: number[]) => api<Message[]>('POST', '/messages/approve', { ids }));

export const useCancelMessage = () =>
  useCrmMutation((id: number) => api<Message>('POST', `/messages/${id}/cancel`));
