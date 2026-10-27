import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { PlanFeatureKey } from '@/api/types';
import { useMe } from '@/features/auth/api';

export const planFeaturesKey = ['plan', 'features'] as const;

/** Lo que incluye el plan del cliente (GET /plan/features). El admin no tiene plan: undefined. */
export function usePlanFeatures() {
  const { data: me } = useMe();
  return useQuery({
    queryKey: planFeaturesKey,
    queryFn: () => unwrap(api.GET('/api/v1/plan/features')),
    enabled: me?.role === 'client',
    staleTime: 60_000,
  });
}

export interface FeatureLock {
  /** El plan no la incluye (con varias claves: ninguna). */
  locked: boolean;
  reason: string | null;
  tierName: string;
}

/** Si el plan bloquea la funcion. Mientras carga, y para el admin, no bloquea: el corte de verdad es de la API. */
export function useFeatureLock(keys: PlanFeatureKey | PlanFeatureKey[]): FeatureLock {
  const plan = usePlanFeatures().data;
  const list = (Array.isArray(keys) ? keys : [keys]).map((k) => plan?.features?.[k]);
  const locked = list.every((f) => f && !f.enabled);
  return { locked, reason: locked ? (list[0]?.reason ?? null) : null, tierName: plan?.tier_name ?? '' };
}

/** Un admin que entró como el cliente (me.support): su plan y sus cobros son de solo lectura (el backend da 403). */
export function useSupportReadOnly(): boolean {
  return useMe().data?.support === true;
}
