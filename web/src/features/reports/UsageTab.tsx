import { useState } from 'react';
import { EmptyState } from '@/components/QueryState';
import { useCurrentUser, useIsAdmin } from '@/features/auth/api';
import { ClientUsage } from '@/features/clients/ClientUsage';
import { recentMonths } from '@/lib/format';
import type { ReportQuery } from './types';

/**
 * Consumo del plan: minutos, llamadas, números y la API de inferencia, con el estado general arriba. Es del mes
 * de facturación (con su selector de mes), no del período de los filtros; el admin lo ve de un cliente.
 */
export function UsageTab({ query }: { query: ReportQuery }) {
  const isAdmin = useIsAdmin();
  const me = useCurrentUser();
  const [month, setMonth] = useState(() => recentMonths(1)[0]);
  const clientId = isAdmin ? query.client_id : (me.client_id ?? undefined);
  if (!clientId) return <EmptyState>Elegí un cliente para ver el consumo de su plan.</EmptyState>;
  return <ClientUsage clientId={clientId} month={month} onMonth={setMonth} limitsName="plan" />;
}
