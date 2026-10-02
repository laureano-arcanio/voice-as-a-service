import { Stack } from '@mantine/core';
import { useState } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { useCurrentUser } from '@/features/auth/api';
import { recentMonths } from '@/lib/format';
import { ApiKeysSection } from './ApiKeysSection';
import { NumbersSection } from './NumbersSection';
import { UsageCard } from './UsageCard';

/** Cuenta del usuario de un cliente: consumo, API keys y sus numeros (agente y etiqueta editables). */
export function AccountPage() {
  const me = useCurrentUser();
  const [month, setMonth] = useState(() => recentMonths(1)[0]);
  if (!me.client_id) return null;
  return (
    <>
      <PageHeader title="Mi cuenta" description={me.client_name ?? undefined} />
      <Stack gap="md">
        <UsageCard clientId={me.client_id} month={month} onMonth={setMonth} limitsName="plan" />
        <NumbersSection clientId={me.client_id} canAssign={false} />
        <ApiKeysSection clientId={me.client_id} />
      </Stack>
    </>
  );
}
