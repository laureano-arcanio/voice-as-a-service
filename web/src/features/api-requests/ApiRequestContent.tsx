import { Alert, Badge, Button, Drawer, Group, Stack, Text } from '@mantine/core';
import { IconDownload, IconTrash } from '@tabler/icons-react';
import type { ApiRequest, ApiRequestContent as Content } from '@/api/types';
import { confirmAction } from '@/components/confirm';
import { QueryState } from '@/components/QueryState';
import { formatBytes, formatDateTimeLong, prettyJson } from '@/lib/format';
import { API_KIND, API_SOURCE } from '@/lib/labels';
import { notifyError, notifySuccess } from '@/lib/notify';
import { apiAudioUrl, useApiRequestContent, useDeleteApiRequestContent } from './api';

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <Stack gap={4}>
      <Text className="label">{title}</Text>
      <pre className="code" style={{ maxHeight: 360, overflow: 'auto' }}>
        {prettyJson(value)}
      </pre>
    </Stack>
  );
}

function AudioBlock({
  id,
  which,
  title,
  bytes,
}: {
  id: string;
  which: 'input' | 'output';
  title: string;
  bytes: number;
}) {
  const url = apiAudioUrl(id, which);
  return (
    <Stack gap={4}>
      <Group justify="space-between" gap="sm">
        <Text className="label">
          {title} · {formatBytes(bytes)}
        </Text>
        <Button
          component="a"
          href={apiAudioUrl(id, which, true)}
          download
          size="compact-sm"
          variant="subtle"
          leftSection={<IconDownload size={14} />}
        >
          Descargar
        </Button>
      </Group>
      <audio controls preload="metadata" src={url} aria-label={title} style={{ width: '100%' }} />
    </Stack>
  );
}

function ContentBody({ r, c, onDeleted }: { r: ApiRequest; c: Content; onDeleted: () => void }) {
  const del = useDeleteApiRequestContent(r.client_id);
  const remove = async () => {
    const ok = await confirmAction({
      title: 'Borrar el contenido',
      message:
        'Se borran el pedido, la respuesta y el audio guardados. El pedido sigue en la lista, con su consumo. No se puede deshacer.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (!ok) return;
    del.mutate(r.id, {
      onSuccess: () => {
        notifySuccess('Contenido borrado.');
        onDeleted();
      },
      onError: (e) => notifyError(e, 'No se pudo borrar'),
    });
  };
  return (
    <Stack gap="md">
      {c.input_audio && (
        <AudioBlock id={r.id} which="input" title="Audio enviado" bytes={c.input_audio.bytes} />
      )}
      {c.output_audio && (
        <AudioBlock id={r.id} which="output" title="Audio generado" bytes={c.output_audio.bytes} />
      )}
      {c.truncated && (
        <Alert color="yellow">
          El audio guardado está cortado: el pedido superó el máximo que se guarda.
        </Alert>
      )}
      {c.request && <JsonBlock title="Pedido" value={c.request} />}
      {c.response && <JsonBlock title="Respuesta" value={c.response} />}
      <Group justify="flex-end">
        <Button
          color="red"
          variant="light"
          leftSection={<IconTrash size={14} />}
          onClick={remove}
          loading={del.isPending}
        >
          Borrar contenido
        </Button>
      </Group>
    </Stack>
  );
}

/** Contenido guardado de un pedido: pedido y respuesta en JSON, audio para escuchar y bajar, y borrar. */
export function ApiRequestContentDrawer({ r, onClose }: { r: ApiRequest | null; onClose: () => void }) {
  const q = useApiRequestContent(r?.id ?? '', !!r?.has_content);
  return (
    <Drawer opened={!!r} onClose={onClose} position="right" size="lg" title="Contenido del pedido">
      {r && (
        <Stack gap="md">
          <Group gap="xs">
            <Badge color="gray">{API_KIND[r.kind].label}</Badge>
            {r.source !== 'api' && (
              <Badge color={API_SOURCE[r.source].color}>{API_SOURCE[r.source].label}</Badge>
            )}
            <Text size="sm" c="dimmed" className="mono">
              {formatDateTimeLong(r.created_at)}
            </Text>
          </Group>
          {!r.has_content ? (
            <Text size="sm" c="dimmed">
              Sin contenido guardado.
            </Text>
          ) : (
            <QueryState query={q}>{(c) => <ContentBody r={r} c={c} onDeleted={onClose} />}</QueryState>
          )}
        </Stack>
      )}
    </Drawer>
  );
}
