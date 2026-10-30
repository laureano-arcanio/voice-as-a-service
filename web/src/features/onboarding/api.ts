import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';

export const onboardingKey = ['onboarding'] as const;

/** Estado del asistente de primera vez: si hay agentes, rubro, celular y llamadas de prueba usadas. */
export function useOnboarding(enabled = true) {
  return useQuery({
    enabled,
    queryKey: onboardingKey,
    queryFn: () => unwrap(api.GET('/api/v1/onboarding')),
  });
}

function useInvalidate() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: onboardingKey });
    void qc.invalidateQueries({ queryKey: ['agents'] });
  };
}

/** Sin invalidar al terminar: el asistente se desmontaría antes de navegar. Lo hace quien llama (`done`). */
export function useCreateFirstAgent() {
  const invalidate = useInvalidate();
  const mutation = useMutation({
    mutationFn: (body: { industry: string; voice: string; website?: string }) =>
      unwrap(api.POST('/api/v1/onboarding/agent', { body })),
  });
  return { ...mutation, done: invalidate };
}

export function useSendPhoneCode() {
  return useMutation({
    mutationFn: (phone: string) => unwrap(api.POST('/api/v1/onboarding/phone/code', { body: { phone } })),
  });
}

export function useVerifyPhone() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { challenge: string; code: string }) =>
      unwrap(api.POST('/api/v1/onboarding/phone/verify', { body })),
    onSuccess: (status) => qc.setQueryData(onboardingKey, status),
  });
}

export function useCallMe() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (agentId: string) =>
      unwrap(api.POST('/api/v1/onboarding/call-me', { body: { agent_id: agentId } })),
    onSuccess: invalidate,
  });
}

/** Llamada de prueba por el navegador (POST /calls sin teléfono) y las credenciales para entrar. */
export async function startBrowserCall(agentId: string) {
  const started = await unwrap(api.POST('/api/v1/calls', { body: { agent_id: agentId } }));
  const creds = await unwrap(
    api.POST('/api/v1/calls/{conversation_id}/join', {
      params: { path: { conversation_id: started.conversation_id } },
    }),
  );
  return { conversationId: started.conversation_id, ...creds };
}

export async function hangUpCall(conversationId: string) {
  await api.POST('/api/v1/calls/{conversation_id}/hangup', {
    params: { path: { conversation_id: conversationId } },
  });
}
