import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type {
  Campaign,
  CampaignChannel,
  CampaignContactsIn,
  CampaignIn,
  CampaignPatch,
  WaCampaignIn,
  WaRecipientsIn,
} from '@/api/types';

export const campaignKeys = {
  all: ['campaigns'] as const,
  list: (clientId?: string, channel?: CampaignChannel) =>
    ['campaigns', 'list', clientId ?? 'all', channel ?? 'all'] as const,
  detail: (id: string) => ['campaigns', 'detail', id] as const,
  stats: (id: string) => ['campaigns', 'detail', id, 'stats'] as const,
  contacts: (id: string, filter: ContactsFilter | null, offset: number) =>
    ['campaigns', 'detail', id, 'contacts', filter?.key ?? 'all', offset] as const,
  plan: () => ['campaigns', 'plan'] as const,
};

/** Mientras una campaña corre (o espera su hora), los numeros se refrescan solos: polling cada 5 s. */
export const LIVE_MS = 5000;
export const isLive = (c: Campaign | undefined) => c?.status === 'running' || c?.status === 'scheduled';

export function useCampaigns(clientId?: string, channel?: CampaignChannel) {
  return useQuery({
    queryKey: campaignKeys.list(clientId, channel),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/campaigns', { params: { query: { client_id: clientId, channel, limit: 500 } } }),
      ),
    refetchInterval: (q) => (q.state.data?.some(isLive) ? LIVE_MS : false),
  });
}

const path = (id: string) => ({ params: { path: { campaign_id: id } } });

export function useCampaign(id: string) {
  return useQuery({
    queryKey: campaignKeys.detail(id),
    queryFn: () => unwrap(api.GET('/api/v1/campaigns/{campaign_id}', path(id))),
    refetchInterval: (q) => (isLive(q.state.data) ? LIVE_MS : false),
  });
}

export function useCampaignStats(id: string, live: boolean) {
  return useQuery({
    queryKey: campaignKeys.stats(id),
    queryFn: () => unwrap(api.GET('/api/v1/campaigns/{campaign_id}/stats', path(id))),
    refetchInterval: live ? LIVE_MS : false,
  });
}

/** Lo que el plan del cliente permite en campañas y agenda. Un admin necesita elegir cliente. */
export function usePlan(enabled = true) {
  return useQuery({
    queryKey: campaignKeys.plan(),
    queryFn: () => unwrap(api.GET('/api/v1/campaigns/plan')),
    enabled,
  });
}

export const CAMPAIGN_CONTACTS_PAGE = 50;

/** Filtro de la tabla de contactos de una campaña: por estado del contacto o por resultado. */
export interface ContactsFilter {
  key: string;
  status?: 'pending' | 'in_progress' | 'retry' | 'done' | 'failed' | 'skipped';
  result?: string;
}

export function useCampaignContacts(
  id: string,
  filter: ContactsFilter | null,
  offset: number,
  live: boolean,
) {
  return useQuery({
    queryKey: campaignKeys.contacts(id, filter, offset),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/campaigns/{campaign_id}/contacts', {
          params: {
            path: { campaign_id: id },
            query: { status: filter?.status, result: filter?.result, offset, limit: CAMPAIGN_CONTACTS_PAGE },
          },
        }),
      ),
    placeholderData: keepPreviousData,
    refetchInterval: live ? LIVE_MS : false,
  });
}

function useInvalidate() {
  const qc = useQueryClient();
  return () => void qc.invalidateQueries({ queryKey: campaignKeys.all });
}

export function useCreateCampaign() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: CampaignIn) => unwrap(api.POST('/api/v1/campaigns', { body })),
    onSuccess: invalidate,
  });
}

/** WhatsApp: el alta con CSV posicional ({{1}}, {{2}}...) sigue entrando por el alias de /whatsapp/campaigns. */
export function useCreateWhatsAppCampaign() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: WaCampaignIn) => unwrap(api.POST('/api/v1/whatsapp/campaigns', { body })),
    onSuccess: invalidate,
  });
}

export function useUpdateCampaign(id: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: CampaignPatch) =>
      unwrap(api.PATCH('/api/v1/campaigns/{campaign_id}', { ...path(id), body })),
    onSuccess: invalidate,
  });
}

/** Suma contactos de la agenda (ids) o nuevos (lista, CSV con el formato de la agenda). */
export function useAddContacts(id: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: CampaignContactsIn) =>
      unwrap(api.POST('/api/v1/campaigns/{campaign_id}/contacts', { ...path(id), body })),
    onSuccess: invalidate,
  });
}

/** WhatsApp: el CSV posicional ({{1}}, {{2}}...) sigue entrando por el alias de /whatsapp/campaigns. */
export function useAddRecipients(id: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: WaRecipientsIn) =>
      unwrap(api.POST('/api/v1/whatsapp/campaigns/{campaign_id}/recipients', { ...path(id), body })),
    onSuccess: invalidate,
  });
}

export type CampaignAction = 'start' | 'resume' | 'pause' | 'cancel';

/** Iniciar, retomar, pausar o cancelar. Un fallo (plantilla pausada por Meta, plan) tambien refresca. */
export function useCampaignAction(id: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ action, registryChecked }: { action: CampaignAction; registryChecked?: boolean }) => {
      const body = registryChecked ? { no_call_registry_checked: true } : undefined;
      if (action === 'start')
        return unwrap(api.POST('/api/v1/campaigns/{campaign_id}/start', { ...path(id), body }));
      if (action === 'resume')
        return unwrap(api.POST('/api/v1/campaigns/{campaign_id}/resume', { ...path(id), body }));
      if (action === 'pause') return unwrap(api.POST('/api/v1/campaigns/{campaign_id}/pause', path(id)));
      return unwrap(api.POST('/api/v1/campaigns/{campaign_id}/cancel', path(id)));
    },
    onSettled: invalidate,
  });
}

export function useDeleteCampaign() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => unwrap(api.DELETE('/api/v1/campaigns/{campaign_id}', path(id))),
    onSuccess: invalidate,
  });
}

/** El reporte por contacto: la cookie de sesion viaja sola (mismo origen). */
export function reportUrl(id: string): string {
  return `/api/v1/campaigns/${id}/report.csv`;
}
