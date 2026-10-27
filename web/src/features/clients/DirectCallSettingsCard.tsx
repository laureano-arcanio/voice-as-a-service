import { Button, Card, Group, Stack, Switch, Text, Title } from '@mantine/core';
import { useState } from 'react';
import type { DirectCallSettings } from '@/features/phone/types';
import { PlanGate } from '@/components/PlanGate';
import { QueryState } from '@/components/QueryState';
import { useDirectCallSettings, useUpdateDirectCallSettings } from '@/features/phone/api';
import { notifyError, notifySuccess } from '@/lib/notify';

function DirectCallSettingsForm({ clientId, data }: { clientId: string; data: DirectCallSettings }) {
  const update = useUpdateDirectCallSettings(clientId);
  const [notice, setNotice] = useState(data.recording_notice);
  const dirty = notice !== data.recording_notice;

  const save = () =>
    update.mutate(
      { recording_notice: notice },
      {
        onSuccess: (r) => {
          setNotice(r.recording_notice);
          notifySuccess(
            r.recording_notice
              ? 'Las llamadas del equipo avisan que se graban.'
              : 'Las llamadas del equipo ya no avisan que se graban.',
          );
        },
        onError: (e) => notifyError(e, 'No se pudo guardar'),
      },
    );

  return (
    <Stack gap="md">
      <Switch
        label="Avisar que la llamada se graba"
        description="Al empezar una llamada del equipo (las que hacen desde el panel y las que atienden), suena «Esta llamada está siendo grabada.»"
        checked={notice}
        onChange={(e) => setNotice(e.currentTarget.checked)}
      />
      <Text size="sm" c="dimmed">
        Las llamadas del equipo se graban siempre. El aviso es opcional, y avisar a quien llama y tener su
        consentimiento es responsabilidad de tu empresa.
      </Text>
      <Group justify="flex-end">
        <Button onClick={save} disabled={!dirty} loading={update.isPending}>
          Guardar
        </Button>
      </Group>
    </Stack>
  );
}

/** Aviso de grabación de las llamadas directas del equipo (siempre se graban; el aviso es opcional). */
export function DirectCallSettingsCard({ clientId }: { clientId: string }) {
  const q = useDirectCallSettings(clientId);
  return (
    <Card>
      <Title order={4} mb={4}>
        Llamadas del equipo
      </Title>
      <Text size="sm" c="dimmed" mb="md">
        Las que las personas del equipo hacen desde el panel y las que atienden en un número del equipo.
      </Text>
      <PlanGate feature="direct_calls" what="llamadas directas">
        <QueryState query={q}>
          {(data) => <DirectCallSettingsForm key={clientId} clientId={clientId} data={data} />}
        </QueryState>
      </PlanGate>
    </Card>
  );
}
