import { Stack } from '@mantine/core';
import { PageHeader } from '@/components/PageHeader';
import { useCurrentUser } from '@/features/auth/api';
import { CallEmailsCard } from './CallEmailsCard';
import { DirectCallSettingsCard } from './DirectCallSettingsCard';
import { NumbersSection } from './NumbersSection';

/** Cuenta del usuario de un cliente: sus numeros (agente y etiqueta editables) y el resumen de llamadas por email.
 * El consumo del plan, en Reportes; las API keys, en /developers. */
export function AccountPage() {
  const me = useCurrentUser();
  if (!me.client_id) return null;
  return (
    <>
      <PageHeader title="Números" description={me.client_name ?? undefined} />
      <Stack gap="md">
        <NumbersSection clientId={me.client_id} canAssign={false} />
        <CallEmailsCard clientId={me.client_id} />
        <DirectCallSettingsCard clientId={me.client_id} />
      </Stack>
    </>
  );
}
