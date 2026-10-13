import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type {
  WaAccountIn,
  WaAccountPatch,
  WaOperatorIn,
  WaOperatorUpdate,
  WaRouteIn,
  WaSignupIn,
  WaTemplateIn,
} from '@/api/types';

export const waKeys = {
  all: ['wa-accounts'] as const,
  list: (clientId?: string) => ['wa-accounts', clientId ?? 'all'] as const,
  config: ['wa-config'] as const,
  templates: (accountId: string) => ['wa-templates', accountId] as const,
};

/** Numeros de WhatsApp: el admin ve todos; el usuario del cliente, los suyos. El token
 * y el PIN nunca vienen: solo has_token y has_pin. */
export function useWaAccounts(clientId?: string) {
  return useQuery({
    queryKey: waKeys.list(clientId),
    queryFn: () =>
      unwrap(api.GET('/api/v1/whatsapp/accounts', { params: { query: { client_id: clientId } } })),
  });
}

/** Datos para lanzar Embedded Signup (app_id, config_id). enabled=false trae el motivo. */
export function useWaConfig() {
  return useQuery({
    queryKey: waKeys.config,
    queryFn: () => unwrap(api.GET('/api/v1/whatsapp/config')),
    staleTime: 5 * 60_000,
  });
}

function useInvalidate() {
  const qc = useQueryClient();
  return () => void qc.invalidateQueries({ queryKey: waKeys.all });
}

const accountPath = (id: string) => ({ params: { path: { account_id: id } } });

export function useCreateWaAccount() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: WaAccountIn) => unwrap(api.POST('/api/v1/whatsapp/accounts', { body })),
    onSuccess: invalidate,
  });
}

export function useUpdateWaAccount() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: WaAccountPatch }) =>
      unwrap(api.PATCH('/api/v1/whatsapp/accounts/{account_id}', { ...accountPath(id), body })),
    onSuccess: invalidate,
  });
}

export function useDeactivateWaAccount() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.POST('/api/v1/whatsapp/accounts/{account_id}/deactivate', accountPath(id))),
    onSuccess: invalidate,
  });
}

/** Reemplaza el ruteo por contacto de la cuenta: esos contactos los atiende cada agente,
 * en los mensajes y las llamadas de WhatsApp, en vez del agente por defecto. */
export function useSetWaRoutes() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, routes }: { id: string; routes: WaRouteIn[] }) =>
      unwrap(
        api.PUT('/api/v1/whatsapp/accounts/{account_id}/routes', { ...accountPath(id), body: routes }),
      ),
    onSuccess: invalidate,
  });
}

/** Alta por Embedded Signup: el codigo vence a los 30 s, hay que mandarlo enseguida. */
export function useWaSignup() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: WaSignupIn) => unwrap(api.POST('/api/v1/whatsapp/signup', { body })),
    onSuccess: invalidate,
  });
}

/** Reintenta la suscripcion y el registro de una cuenta pendiente (PIN opcional). */
export function useRegisterWaAccount() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, pin }: { id: string; pin?: string | null }) =>
      unwrap(
        api.POST('/api/v1/whatsapp/accounts/{account_id}/register', {
          ...accountPath(id),
          body: { pin: pin || null },
        }),
      ),
    // Un 190 la deja desconectada aunque el pedido falle: refrescar igual.
    onSettled: invalidate,
  });
}

/** Relee el numero visible y la calidad en Meta. */
export function useRefreshWaAccount() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.POST('/api/v1/whatsapp/accounts/{account_id}/refresh', accountPath(id))),
    onSettled: invalidate,
  });
}

/** Plantillas de la WABA de la cuenta, en vivo desde Meta (no hay copia local). */
export function useWaTemplates(accountId: string | undefined) {
  return useQuery({
    queryKey: waKeys.templates(accountId ?? ''),
    queryFn: () =>
      unwrap(api.GET('/api/v1/whatsapp/accounts/{account_id}/templates', accountPath(accountId ?? ''))),
    enabled: !!accountId,
    staleTime: 30_000,
    retry: false,
  });
}

export function useCreateWaTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ accountId, body }: { accountId: string; body: WaTemplateIn }) =>
      unwrap(
        api.POST('/api/v1/whatsapp/accounts/{account_id}/templates', { ...accountPath(accountId), body }),
      ),
    onSuccess: (_, { accountId }) => void qc.invalidateQueries({ queryKey: waKeys.templates(accountId) }),
  });
}

// --- Operadores (docs/APPS_PLAN.md): el dueño de un negocio que le habla a su asistente por un
// numero compartido. Solo admin.

export const operatorKeys = {
  all: ['wa-operators'] as const,
};

export function useWaOperators(enabled = true) {
  return useQuery({
    queryKey: operatorKeys.all,
    queryFn: () => unwrap(api.GET('/api/v1/wa-operators')),
    enabled,
  });
}

function useInvalidateOperators() {
  const qc = useQueryClient();
  return () => void qc.invalidateQueries({ queryKey: operatorKeys.all });
}

export function useCreateWaOperator() {
  const invalidate = useInvalidateOperators();
  return useMutation({
    mutationFn: (body: WaOperatorIn) => unwrap(api.POST('/api/v1/wa-operators', { body })),
    onSuccess: invalidate,
  });
}

export function useUpdateWaOperator() {
  const invalidate = useInvalidateOperators();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: WaOperatorUpdate }) =>
      unwrap(api.PATCH('/api/v1/wa-operators/{op_id}', { params: { path: { op_id: id } }, body })),
    onSuccess: invalidate,
  });
}

export function useDeleteWaOperator() {
  const invalidate = useInvalidateOperators();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE('/api/v1/wa-operators/{op_id}', { params: { path: { op_id: id } } })),
    onSuccess: invalidate,
  });
}
