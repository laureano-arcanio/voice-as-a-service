import { useState } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { useCurrentUser } from '@/features/auth/api';
import { recentMonths } from '@/lib/format';
import { ClientUsage } from './ClientUsage';

/** Consumos del cliente: lo que usó en el mes contra los límites de su plan. */
export function UsagePage() {
  const me = useCurrentUser();
  const [month, setMonth] = useState(() => recentMonths(1)[0]);
  if (!me.client_id) return null;
  return (
    <>
      <PageHeader title="Consumos" description="Llamadas, números y API de inferencia del mes contra tu plan." />
      <ClientUsage clientId={me.client_id} month={month} onMonth={setMonth} limitsName="plan" />
    </>
  );
}
