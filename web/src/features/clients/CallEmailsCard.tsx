import { Button, Card, Group, Stack, Switch, TagsInput, Text, Title } from '@mantine/core';
import { useState } from 'react';
import type { CallEmails } from '@/api/types';
import { QueryState } from '@/components/QueryState';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useCallEmails, useUpdateCallEmails } from './api';

function CallEmailsForm({ clientId, data }: { clientId: string; data: CallEmails }) {
  const update = useUpdateCallEmails(clientId);
  const [enabled, setEnabled] = useState(data.enabled);
  const saved = data.recipients ?? [];
  const [recipients, setRecipients] = useState<string[]>(saved);
  const dirty = enabled !== data.enabled || recipients.join('\n') !== saved.join('\n');
  const defaults = data.default_recipients.length
    ? `Vacío: a los usuarios de la cuenta (${data.default_recipients.join(', ')}).`
    : 'Vacío: a los usuarios de la cuenta (todavía no hay ninguno).';

  const save = () =>
    update.mutate(
      { enabled, recipients },
      {
        onSuccess: (r) => {
          setRecipients(r.recipients ?? []);
          notifySuccess(r.enabled ? 'Resúmenes por email prendidos.' : 'Resúmenes por email apagados.');
        },
        onError: (e) => notifyError(e, 'No se pudo guardar'),
      },
    );

  return (
    <Stack gap="md">
      <Switch
        label="Recibir el resumen de cada llamada"
        description="Apagado, ningún agente de la cuenta lo manda."
        checked={enabled}
        onChange={(e) => setEnabled(e.currentTarget.checked)}
      />
      <TagsInput
        label="A quién le llega"
        description={defaults}
        placeholder="email@empresa.com"
        value={recipients}
        onChange={setRecipients}
        maxTags={10}
        splitChars={[',', ' ', ';']}
        disabled={!enabled}
        clearable
      />
      <Text size="sm" c="dimmed">
        {data.agents.length
          ? `Lo mandan: ${data.agents.join(', ')}.`
          : 'Ningún agente lo tiene prendido: se prende en el editor del agente, sección Voz.'}
      </Text>
      <Group justify="flex-end">
        <Button onClick={save} disabled={!dirty} loading={update.isPending}>
          Guardar
        </Button>
      </Group>
    </Stack>
  );
}

/** Resumen por email de cada llamada (datos, resultado y conversación): el cliente lo apaga para todos sus
 * agentes y elige a quién le llega. Cada agente lo prende en su definición. */
export function CallEmailsCard({ clientId }: { clientId: string }) {
  const q = useCallEmails(clientId);
  return (
    <Card>
      <Title order={4} mb={4}>
        Resumen de llamadas por email
      </Title>
      <Text size="sm" c="dimmed" mb="md">
        Al terminar cada llamada, Atentina manda los datos que tomó el agente, el resultado y la conversación.
      </Text>
      <QueryState query={q}>
        {(data) => <CallEmailsForm key={clientId} clientId={clientId} data={data} />}
      </QueryState>
    </Card>
  );
}
