import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { WaCampaign, WaCampaignIn, WaCampaignPatch, WaRecipientsIn } from '@/api/types';

export const campaignKeys = {
  all: ['wa-campaigns'] as const,
  list: (clientId?: string) => ['wa-campaigns', 'list', clientId ?? 'all'] as const,
  detail: (id: string) => ['wa-campaigns', id] as const,
  recipients: (id: string, status: string | null, offset: number) =>
    ['wa-campaigns', id, 'recipients', status ?? 'all', offset] as const,
  optouts: (clientId?: string) => ['wa-optouts', clientId ?? 'all'] as const,
};

// Mientras una campaña envia, los numeros se refrescan solos.
const LIVE_MS = 5000;
const isLive = (c: WaCampaign | undefined) => c?.status === 'running';

export function useCampaigns(clientId?: string) {
  return useQuery({
    queryKey: campaignKeys.list(clientId),
    queryFn: () =>
      unwrap(api.GET('/api/v1/whatsapp/campaigns', { params: { query: { client_id: clientId } } })),
    refetchInterval: (q) => (q.state.data?.some(isLive) ? LIVE_MS : false),
  });
}

const path = (id: string) => ({ params: { path: { campaign_id: id } } });

export function useCampaign(id: string) {
  return useQuery({
    queryKey: campaignKeys.detail(id),
    queryFn: () => unwrap(api.GET('/api/v1/whatsapp/campaigns/{campaign_id}', path(id))),
    refetchInterval: (q) => (isLive(q.state.data) ? LIVE_MS : false),
  });
}

export function useRecipients(id: string, status: string | null, offset: number, live: boolean) {
  return useQuery({
    queryKey: campaignKeys.recipients(id, status, offset),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/whatsapp/campaigns/{campaign_id}/recipients', {
          params: { path: { campaign_id: id }, query: { status, offset, limit: RECIPIENTS_PAGE } },
        }),
      ),
    placeholderData: keepPreviousData,
    refetchInterval: live ? LIVE_MS : false,
  });
}

export const RECIPIENTS_PAGE = 50;

function useInvalidate() {
  const qc = useQueryClient();
  return () => void qc.invalidateQueries({ queryKey: campaignKeys.all });
}

export function useCreateCampaign() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: WaCampaignIn) => unwrap(api.POST('/api/v1/whatsapp/campaigns', { body })),
    onSuccess: invalidate,
  });
}

export function useUpdateCampaign(id: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: WaCampaignPatch) =>
      unwrap(api.PATCH('/api/v1/whatsapp/campaigns/{campaign_id}', { ...path(id), body })),
    onSuccess: invalidate,
  });
}

export function useAddRecipients(id: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: WaRecipientsIn) =>
      unwrap(api.POST('/api/v1/whatsapp/campaigns/{campaign_id}/recipients', { ...path(id), body })),
    onSuccess: invalidate,
  });
}

/** Iniciar, pausar o cancelar. Un fallo (plantilla pausada por Meta) tambien refresca. */
export function useCampaignAction(id: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (action: 'start' | 'pause' | 'cancel') => {
      if (action === 'start')
        return unwrap(api.POST('/api/v1/whatsapp/campaigns/{campaign_id}/start', path(id)));
      if (action === 'pause')
        return unwrap(api.POST('/api/v1/whatsapp/campaigns/{campaign_id}/pause', path(id)));
      return unwrap(api.POST('/api/v1/whatsapp/campaigns/{campaign_id}/cancel', path(id)));
    },
    onSettled: invalidate,
  });
}

export function useDeleteCampaign() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => unwrap(api.DELETE('/api/v1/whatsapp/campaigns/{campaign_id}', path(id))),
    onSuccess: invalidate,
  });
}

export function useOptouts(clientId?: string) {
  return useQuery({
    queryKey: campaignKeys.optouts(clientId),
    queryFn: () =>
      unwrap(api.GET('/api/v1/whatsapp/optouts', { params: { query: { client_id: clientId } } })),
  });
}

export function useAddOptout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { phone: string; client_id?: string | null }) =>
      unwrap(api.POST('/api/v1/whatsapp/optouts', { body })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['wa-optouts'] }),
  });
}

export function useRemoveOptout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ waId, clientId }: { waId: string; clientId: string }) =>
      unwrap(
        api.DELETE('/api/v1/whatsapp/optouts/{wa_id}', {
          params: { path: { wa_id: waId }, query: { client_id: clientId } },
        }),
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['wa-optouts'] }),
  });
}
