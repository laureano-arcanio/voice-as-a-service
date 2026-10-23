import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { HandoffAreaIn, HandoffAreaPatch, TeamMemberIn, TeamMemberPatch } from '@/api/types';

// Equipo del cliente y areas de derivacion (docs/DERIVACIONES_PLAN.md, 3 y 4.7). Un admin pasa
// client_id; sin el, ve los de todos los clientes.

export const teamKeys = {
  members: (clientId?: string) => ['team', 'members', clientId ?? 'all'] as const,
  areas: (clientId?: string) => ['team', 'areas', clientId ?? 'all'] as const,
  defaults: ['team', 'area-defaults'] as const,
};

export function useTeam(clientId?: string) {
  return useQuery({
    queryKey: teamKeys.members(clientId),
    queryFn: () => unwrap(api.GET('/api/v1/team', { params: { query: { client_id: clientId } } })),
  });
}

/** Un area como llega de la API (las franjas, como listas de "HH:MM"). */
export type AreaRow = NonNullable<ReturnType<typeof useAreas>['data']>[number];

export function useAreas(clientId?: string) {
  return useQuery({
    queryKey: teamKeys.areas(clientId),
    queryFn: () => unwrap(api.GET('/api/v1/handoff-areas', { params: { query: { client_id: clientId } } })),
  });
}

/** Temas de musica de espera para la derivacion (handoff.hold_music.track del agente). */
export function useHoldMusic() {
  return useQuery({
    queryKey: ['team', 'hold-music'],
    queryFn: async () => (await unwrap(api.GET('/api/v1/hold-music'))).tracks,
    staleTime: 5 * 60_000,
  });
}

/** Mensajes por defecto de un area y las variables que aceptan. */
export function useAreaDefaults() {
  return useQuery({
    queryKey: teamKeys.defaults,
    queryFn: () => unwrap(api.GET('/api/v1/handoff-areas/defaults')),
    staleTime: Infinity,
  });
}

/** Borrar o cambiar una persona tambien cambia las areas (salen de su lista). */
function useInvalidate() {
  const qc = useQueryClient();
  return () => void qc.invalidateQueries({ queryKey: ['team'] });
}

export function useSaveMember(clientId?: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, body }: { id?: string; body: TeamMemberIn & TeamMemberPatch }) =>
      id
        ? unwrap(api.PATCH('/api/v1/team/{member_id}', { params: { path: { member_id: id } }, body }))
        : unwrap(api.POST('/api/v1/team', { params: { query: { client_id: clientId } }, body })),
    onSuccess: invalidate,
  });
}

export function useDeleteMember() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE('/api/v1/team/{member_id}', { params: { path: { member_id: id } } })),
    onSuccess: invalidate,
  });
}

export function useSaveArea(clientId?: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, body }: { id?: string; body: HandoffAreaIn & HandoffAreaPatch }) =>
      id
        ? unwrap(api.PATCH('/api/v1/handoff-areas/{area_id}', { params: { path: { area_id: id } }, body }))
        : unwrap(api.POST('/api/v1/handoff-areas', { params: { query: { client_id: clientId } }, body })),
    onSuccess: invalidate,
  });
}

export function useDeleteArea() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE('/api/v1/handoff-areas/{area_id}', { params: { path: { area_id: id } } })),
    onSuccess: invalidate,
  });
}
