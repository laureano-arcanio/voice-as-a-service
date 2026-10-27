import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { components } from '@/api/schema';
import type { WaAccountIn, WaAccountPatch, WaRouteIn, WaSignupIn, WaTemplateIn } from '@/api/types';

/** Cuerpo de la conexion con la app propia (aun no esta en `@/api/types`). */
export type WaOwnAppIn = components['schemas']['WaOwnAppIn'];

export const waKeys = {
  all: ['wa-accounts'] as const,
  list: ['wa-accounts', 'list'] as const,
  config: ['wa-config'] as const,
  templates: (accountId: string) => ['wa-templates', accountId] as const,
};

/** Numeros de WhatsApp del cliente (o del cliente en soporte). El token, el PIN y el app secret
 * nunca vienen: solo has_token, has_pin y has_app_secret. */
export function useWaAccounts() {
  return useQuery({
    queryKey: waKeys.list,
    queryFn: () => unwrap(api.GET('/api/v1/whatsapp/accounts')),
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
      unwrap(api.PUT('/api/v1/whatsapp/accounts/{account_id}/routes', { ...accountPath(id), body: routes })),
    onSuccess: invalidate,
  });
}

/** Conecta un numero con la app de Meta del cliente. Con el mismo phone_number_id actualiza el
 * token y el secret (la URL del webhook y el verify token no cambian). */
export function useConnectOwnApp() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (body: WaOwnAppIn) => unwrap(api.POST('/api/v1/whatsapp/accounts/own-app', { body })),
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
