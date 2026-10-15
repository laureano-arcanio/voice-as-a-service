import { Stack } from '@mantine/core';
import { PageHeader } from '@/components/PageHeader';
import { useCurrentUser } from '@/features/auth/api';
import { LlmConnectionsSection } from './LlmConnectionsSection';

/** Modelos de IA del cliente: sus conexiones (BYOK). El modelo de cada agente se elige en el agente. */
export function ModelsPage() {
  const me = useCurrentUser();
  if (!me.client_id) return null;
  return (
    <>
      <PageHeader
        title="Modelos"
        description="Tus conexiones a proveedores de IA. Cada agente elige cuál usar y desde qué turno."
      />
      <Stack gap="md">
        <LlmConnectionsSection clientId={me.client_id} />
      </Stack>
    </>
  );
}
