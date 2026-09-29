import { QueryClient } from '@tanstack/react-query';
import { ApiError } from '@/api/errors';

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 10_000,
        // Errores del cliente (4xx) no se reintentan; los de red o 5xx, hasta 2 veces.
        retry: (count, err) => !(err instanceof ApiError && err.status < 500) && count < 2,
      },
      mutations: { retry: false },
    },
  });
}
