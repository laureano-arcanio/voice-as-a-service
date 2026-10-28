import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { ContactIn, ContactPatch, OptoutChannel } from '@/api/types';

export type ArchivedFilter = 'false' | 'true' | 'all';

export interface ContactFilters {
  clientId?: string;
  q: string;
  archived: ArchivedFilter;
  offset: number;
}

export const CONTACTS_PAGE = 50;

export const contactKeys = {
  all: ['contacts'] as const,
  list: (f: ContactFilters) => ['contacts', 'list', f] as const,
  detail: (id: string) => ['contacts', 'detail', id] as const,
  campaigns: (id: string) => ['contacts', 'detail', id, 'campaigns'] as const,
  optouts: (clientId?: string) => ['contact-optouts', clientId ?? 'all'] as const,
  blocked: (clientId?: string) => ['blocked-numbers', clientId ?? 'all'] as const,
};

export function useContacts(f: ContactFilters) {
  return useQuery({
    queryKey: contactKeys.list(f),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/contacts', {
          params: {
            query: {
              client_id: f.clientId,
              q: f.q || undefined,
              archived: f.archived,
              offset: f.offset,
              limit: CONTACTS_PAGE,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

export function useContact(id: string) {
  return useQuery({
    queryKey: contactKeys.detail(id),
    queryFn: () => unwrap(api.GET('/api/v1/contacts/{contact_id}', { params: { path: { contact_id: id } } })),
  });
}

export function useContactCampaigns(id: string) {
  return useQuery({
    queryKey: contactKeys.campaigns(id),
    queryFn: () =>
      unwrap(api.GET('/api/v1/contacts/{contact_id}/campaigns', { params: { path: { contact_id: id } } })),
  });
}

/** Cambios en la agenda: refrescan listas, fichas y el uso del plan (contactos activos). */
function useInvalidate() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: contactKeys.all });
    void qc.invalidateQueries({ queryKey: ['campaigns', 'plan'] });
  };
}

/** Alta de un contacto (upsert por teléfono). Va solo, no en lista: así una fila rechazada (dato inválido o
 * tope del plan) vuelve como error con el motivo, en vez de un 200 con `invalid` que parece "ya existía". */
export function useUpsertContact(clientId?: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: ContactIn) =>
      unwrap(api.POST('/api/v1/contacts', { params: { query: { client_id: clientId } }, body })),
    onSuccess: invalidate,
  });
}

export function useImportContacts(clientId?: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: { csv: string }) =>
      unwrap(api.POST('/api/v1/contacts/import', { params: { query: { client_id: clientId } }, body })),
    onSuccess: invalidate,
  });
}

export function useUpdateContact(id: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: ContactPatch) =>
      unwrap(api.PATCH('/api/v1/contacts/{contact_id}', { params: { path: { contact_id: id } }, body })),
    onSuccess: invalidate,
  });
}

export function useArchiveContact() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, archive }: { id: string; archive: boolean }) =>
      archive
        ? unwrap(api.POST('/api/v1/contacts/{contact_id}/archive', { params: { path: { contact_id: id } } }))
        : unwrap(
            api.POST('/api/v1/contacts/{contact_id}/unarchive', { params: { path: { contact_id: id } } }),
          ),
    onSuccess: invalidate,
  });
}

/** Archiva en lote, por ids. */
export function useArchiveMany(clientId?: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: { contact_ids: string[] }) =>
      unwrap(api.POST('/api/v1/contacts/archive', { params: { query: { client_id: clientId } }, body })),
    onSuccess: invalidate,
  });
}

/** Desarchiva en lote: la API lo hace de a uno, y el tope del plan puede dejar a alguno afuera. */
export function useUnarchiveMany() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (ids: string[]) => {
      const results = await Promise.allSettled(
        ids.map((id) =>
          unwrap(
            api.POST('/api/v1/contacts/{contact_id}/unarchive', { params: { path: { contact_id: id } } }),
          ),
        ),
      );
      const failed = results.filter((r) => r.status === 'rejected');
      return { done: results.length - failed.length, failed: failed.length, firstError: failed[0]?.reason };
    },
    onSettled: invalidate,
  });
}

export function useOptouts(clientId?: string) {
  return useQuery({
    queryKey: contactKeys.optouts(clientId),
    queryFn: () =>
      unwrap(api.GET('/api/v1/contacts/optouts', { params: { query: { client_id: clientId } } })),
  });
}

export function useAddOptout(clientId?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { phone: string; channel: OptoutChannel }) =>
      unwrap(api.POST('/api/v1/contacts/optouts', { params: { query: { client_id: clientId } }, body })),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['contact-optouts'] }),
  });
}

export function useRemoveOptout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ phone, clientId, channel }: { phone: string; clientId: string; channel: OptoutChannel }) =>
      unwrap(
        api.DELETE('/api/v1/contacts/optouts/{phone}', {
          params: { path: { phone }, query: { client_id: clientId, channel } },
        }),
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['contact-optouts'] }),
  });
}

// ---- Numeros bloqueados: sus llamadas entrantes se cortan sin atender ----

export function useBlockedNumbers(clientId?: string) {
  return useQuery({
    queryKey: contactKeys.blocked(clientId),
    queryFn: () => unwrap(api.GET('/api/v1/blocked-numbers', { params: { query: { client_id: clientId } } })),
  });
}

/** clientId: el del numero (un admin lo indica; el cliente bloquea en lo suyo). */
export function useBlockNumber() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ phone, note, clientId }: { phone: string; note?: string; clientId?: string }) =>
      unwrap(
        api.POST('/api/v1/blocked-numbers', {
          params: { query: { client_id: clientId } },
          body: { phone, note: note ?? '' },
        }),
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['blocked-numbers'] }),
  });
}

export function useUnblockNumber() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ phone, clientId }: { phone: string; clientId: string }) =>
      unwrap(
        api.DELETE('/api/v1/blocked-numbers/{phone}', {
          params: { path: { phone }, query: { client_id: clientId } },
        }),
      ),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['blocked-numbers'] }),
  });
}
