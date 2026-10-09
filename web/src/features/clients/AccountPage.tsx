import { Card, Group, Stack, Text, Title } from '@mantine/core';
import { useState } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { useCurrentUser } from '@/features/auth/api';
import { formatCallLimit, formatRetention, recentMonths } from '@/lib/format';
import { useClient } from './api';
import { ApiKeysSection } from './ApiKeysSection';
import { NumbersSection } from './NumbersSection';
import { UsageCard } from './UsageCard';

/** Lo que el plan fija ademas de los minutos: cuanto dura como maximo cada llamada y
 * cuanto se guarda el historial. */
function PlanCard({ clientId }: { clientId: string }) {
  const client = useClient(clientId);
  if (!client.data) return null;
  const c = client.data;
  return (
    <Card>
      <Title order={4} mb="sm">
        Plan
      </Title>
      <Group gap="xl">
        <Stack gap={2}>
          <Text size="xs" c="dimmed">
            Duración máxima por llamada
          </Text>
          <Text size="sm" fw={600}>
            {formatCallLimit(c.effective_max_call_seconds)}
          </Text>
        </Stack>
        <Stack gap={2}>
          <Text size="xs" c="dimmed">
            Historial de conversaciones
          </Text>
          <Text size="sm" fw={600}>
            {c.effective_retention_days == null
              ? 'Se guarda sin límite'
              : `Se guarda ${formatRetention(c.effective_retention_days)}`}
          </Text>
        </Stack>
      </Group>
    </Card>
  );
}

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
        <PlanCard clientId={me.client_id} />
        <NumbersSection clientId={me.client_id} canAssign={false} />
        <ApiKeysSection clientId={me.client_id} />
      </Stack>
    </>
  );
}
