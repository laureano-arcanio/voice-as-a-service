import { MutationCache, QueryClient } from '@tanstack/react-query';
import { ApiError } from '@/api/errors';

export function createQueryClient() {
  const qc: QueryClient = new QueryClient({
    // Si una accion choca con la cuenta inactiva (se desactivo con la pantalla abierta),
    // se relee el cliente para que aparezca el aviso de solo lectura.
    mutationCache: new MutationCache({
      onError: (err) => {
        if (err instanceof ApiError && err.code === 'client_inactive')
          void qc.invalidateQueries({ queryKey: ['clients'] });
      },
    }),
    defaultOptions: {
      queries: {
        staleTime: 10_000,
        // Errores del cliente (4xx) no se reintentan; los de red o 5xx, hasta 2 veces.
        retry: (count, err) => !(err instanceof ApiError && err.status < 500) && count < 2,
      },
      mutations: { retry: false },
    },
  });
  return qc;
}
