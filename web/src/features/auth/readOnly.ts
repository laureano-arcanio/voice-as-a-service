import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import { clientKeys } from '@/features/clients/api';
import { useMe } from './api';

/**
 * Cuenta en solo lectura: el usuario de un cliente inactivo entra, ve y exporta su
 * historial, pero no consume (llamadas, texto con el agente, pruebas de voz, WhatsApp,
 * campañas) ni crea API keys (H12). La UI deshabilita esas acciones; la API igual las
 * rechaza (403 client_inactive). El admin nunca esta en solo lectura.
 */
export function useReadOnly(): boolean {
  const { data: me } = useMe();
  const clientId = me?.role === 'client' ? me.client_id : null;
  const client = useQuery({
    queryKey: clientKeys.detail(clientId ?? ''),
    queryFn: () =>
      unwrap(api.GET('/api/v1/clients/{client_id}', { params: { path: { client_id: clientId! } } })),
    enabled: !!clientId,
    staleTime: 60_000,
  });
  return !!clientId && client.data?.active === false;
}

/** Por que esta deshabilitada una accion en solo lectura (Tooltip). */
export const READ_ONLY_REASON = 'Tu cuenta está en solo lectura.';
