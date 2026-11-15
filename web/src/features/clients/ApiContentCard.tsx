import { Button, Card, Group, Select, Stack, Switch, Text, Title } from '@mantine/core';
import { useState } from 'react';
import type { ApiContentSettings } from '@/api/types';
import { QueryState } from '@/components/QueryState';
import { formatBytes, formatNumber } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useApiContent, useUpdateApiContent } from './api';

const RETENTION = [
  { value: '7', label: '7 días' },
  { value: '30', label: '30 días' },
  { value: '90', label: '90 días' },
  { value: '180', label: '180 días' },
  { value: '365', label: '365 días' },
  { value: 'forever', label: 'Indefinido' },
];

type Days = 7 | 30 | 90 | 180 | 365;

function ApiContentForm({ clientId, data }: { clientId: string; data: ApiContentSettings }) {
  const update = useUpdateApiContent(clientId);
  const savedRetention = data.retention_days == null ? 'forever' : String(data.retention_days);
  const [enabled, setEnabled] = useState(data.enabled);
  const [retention, setRetention] = useState(savedRetention);
  const dirty = enabled !== data.enabled || retention !== savedRetention;

  const save = () =>
    update.mutate(
      { enabled, retention_days: retention === 'forever' ? null : (Number(retention) as Days) },
      {
        onSuccess: (r) =>
          notifySuccess(
            r.enabled ? 'Se guarda el contenido de la API.' : 'Ya no se guarda el contenido de la API.',
          ),
        onError: (e) => notifyError(e, 'No se pudo guardar'),
      },
    );

  return (
    <Stack gap="md">
      <Switch
        label="Guardar el contenido de la API y de las pruebas de voz"
        description="Pedido y respuesta de LLM, el audio de la transcripción y el de la síntesis. Apagado, no se guarda lo que llegue desde ahora."
        checked={enabled}
        onChange={(e) => setEnabled(e.currentTarget.checked)}
      />
      <Select
        label="Se borra a los"
        description="Rige también para lo ya guardado."
        data={RETENTION}
        value={retention}
        onChange={(v) => setRetention(v ?? savedRetention)}
        allowDeselect={false}
        w={220}
      />
      {retention === 'forever' && (
        <Text size="sm" c="yellow.7">
          No vence: ocupa disco hasta que lo borres.
        </Text>
      )}
      <Text size="sm" c="dimmed">
        {data.stored_requests
          ? `Guardado: ${formatNumber(data.stored_requests, 0)} ${data.stored_requests === 1 ? 'pedido' : 'pedidos'}, ${formatBytes(data.stored_bytes)}.`
          : 'Todavía no hay nada guardado.'}{' '}
        Se ve y se borra pedido por pedido en Uso de la API.
      </Text>
      <Group justify="flex-end">
        <Button onClick={save} disabled={!dirty} loading={update.isPending}>
          Guardar
        </Button>
      </Group>
    </Stack>
  );
}

/** Contenido de la API de inferencia y de las pruebas de voz: interruptor y vencimiento, con lo que ocupa.
 * Lo edita el cliente y el admin (también entrando como el cliente). */
export function ApiContentCard({ clientId }: { clientId: string }) {
  const q = useApiContent(clientId);
  return (
    <Card>
      <Title order={4} mb={4}>
        Contenido de la API
      </Title>
      <Text size="sm" c="dimmed" mb="md">
        Atentina guarda lo que mandan y reciben tus sistemas por la API de inferencia, y las pruebas de voz,
        para que puedas revisarlo.
      </Text>
      <QueryState query={q}>
        {(data) => <ApiContentForm key={clientId} clientId={clientId} data={data} />}
      </QueryState>
    </Card>
  );
}
