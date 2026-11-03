import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Menu,
  Modal,
  Progress,
  ScrollArea,
  Stack,
  Table,
  Text,
  Tooltip,
} from '@mantine/core';
import { IconDownload, IconFileText, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';
import { confirmAction } from '@/components/confirm';
import { CopyIcon } from '@/components/Copy';
import { EmptyState, QueryState } from '@/components/QueryState';
import { useClientUsage } from '@/features/clients/api';
import { useMe } from '@/features/auth/api';
import { voiceName } from '@/features/voices/names';
import { formatDateTime, formatDuration, toMonth } from '@/lib/format';
import { notifyError } from '@/lib/notify';
import {
  AUDIO_FORMATS,
  audioUrl,
  downloadText,
  isActive,
  useDeleteStudioItem,
  useStudioItem,
  useStudioItems,
  type StudioItem,
  type StudioKind,
} from './api';

/** Lo que le queda al cliente este mes: el Estudio gasta los mismos minutos que las entrantes. */
export function MinutesLeft({ refresh }: { refresh: boolean }) {
  const { data: me } = useMe();
  const usage = useClientUsage(me?.client_id ?? undefined, toMonth(new Date()), refresh ? 3000 : false);
  const left = usage.data?.inbound.remaining_minutes;
  return (
    <Text size="xs" c="dimmed">
      Se descuenta de los minutos entrantes de tu plan
      {left != null && `: te quedan ${left} este mes`}.
    </Text>
  );
}

function TextModal({ id, onClose }: { id: string | null; onClose: () => void }) {
  const item = useStudioItem(id);
  return (
    <Modal opened={!!id} onClose={onClose} title={item.data?.title ?? 'Texto'} size="lg">
      <QueryState query={item}>
        {(data) => (
          <Stack gap="sm">
            <ScrollArea.Autosize mah={420}>
              <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
                {data.text || 'No se reconoció texto en este audio.'}
              </Text>
            </ScrollArea.Autosize>
            {data.text && (
              <Group justify="flex-end" gap="xs">
                <CopyIcon value={data.text} label="Copiar el texto" />
                <Button
                  variant="default"
                  size="compact-sm"
                  leftSection={<IconDownload size={14} />}
                  onClick={() => downloadText(data.text!, data.title)}
                >
                  Descargar .txt
                </Button>
              </Group>
            )}
          </Stack>
        )}
      </QueryState>
    </Modal>
  );
}

function Status({ item }: { item: StudioItem }) {
  if (item.status === 'failed')
    return (
      <Tooltip label={item.error ?? ''} disabled={!item.error} withArrow multiline w={260}>
        <Badge color="red">Falló</Badge>
      </Tooltip>
    );
  if (item.status === 'queued') return <Badge color="gray">En cola</Badge>;
  if (item.status === 'processing')
    return <Progress value={Math.max(item.progress, 3)} w={90} aria-label="Progreso" animated />;
  return null;
}

function Actions({ item, onText, readOnly }: { item: StudioItem; onText: () => void; readOnly: boolean }) {
  const remove = useDeleteStudioItem();
  const done = item.status === 'done';
  const doDelete = async () => {
    const ok = await confirmAction({
      title: 'Borrar',
      message: 'Se borran el audio y el texto. Los minutos ya usados no vuelven al plan.',
      confirmLabel: 'Borrar',
      danger: true,
    });
    if (ok) remove.mutate(item.id, { onError: (e) => notifyError(e, 'No se pudo borrar') });
  };
  return (
    <Group gap={4} justify="flex-end" wrap="nowrap">
      {done && (
        <Tooltip label="Ver el texto" withArrow>
          <ActionIcon variant="subtle" color="gray" aria-label="Ver el texto" onClick={onText}>
            <IconFileText size={16} />
          </ActionIcon>
        </Tooltip>
      )}
      {done && item.kind === 'tts' && (
        <Menu position="bottom-end" withinPortal>
          <Menu.Target>
            <ActionIcon variant="subtle" color="gray" aria-label="Descargar el audio">
              <IconDownload size={16} />
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown>
            {AUDIO_FORMATS.map((f) => (
              <Menu.Item key={f.value} component="a" href={audioUrl(item.id, f.value, true)}>
                {f.label}
              </Menu.Item>
            ))}
          </Menu.Dropdown>
        </Menu>
      )}
      {!isActive(item) && !readOnly && (
        <Tooltip label="Borrar" withArrow>
          <ActionIcon variant="subtle" color="gray" aria-label="Borrar" onClick={() => void doDelete()}>
            <IconTrash size={16} />
          </ActionIcon>
        </Tooltip>
      )}
    </Group>
  );
}

/** Todo lo que el cliente generó de este tipo, guardado: escuchar, ver el texto, descargar y borrar. */
export function History({ kind, readOnly }: { kind: StudioKind; readOnly: boolean }) {
  const items = useStudioItems(kind);
  const [textOf, setTextOf] = useState<string | null>(null);
  return (
    <>
      <QueryState query={items}>
        {({ items: list }) =>
          list.length === 0 ? (
            <EmptyState>
              {kind === 'tts'
                ? 'Todavía no sintetizaste nada. Lo que generes va a quedar guardado acá.'
                : 'Todavía no transcribiste nada. Lo que subas va a quedar guardado acá.'}
            </EmptyState>
          ) : (
            <Table.ScrollContainer minWidth={560}>
              <Table verticalSpacing="xs">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>{kind === 'tts' ? 'Texto' : 'Archivo'}</Table.Th>
                    <Table.Th>Audio</Table.Th>
                    <Table.Th ta="right">Duración</Table.Th>
                    <Table.Th>Fecha</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {list.map((item) => (
                    <Table.Tr key={item.id}>
                      <Table.Td maw={320}>
                        <Text size="sm" fw={600} lineClamp={1}>
                          {item.title}
                        </Text>
                        <Group gap={6} wrap="nowrap">
                          {item.voice && (
                            <Text size="xs" c="dimmed">
                              {voiceName(item.voice)}
                            </Text>
                          )}
                          {item.origin === 'voice_test' && <Badge color="gray">Prueba de voz</Badge>}
                          {kind === 'stt' && item.excerpt && (
                            <Text size="xs" c="dimmed" lineClamp={1}>
                              {item.excerpt}
                            </Text>
                          )}
                        </Group>
                      </Table.Td>
                      <Table.Td miw={200}>
                        <Status item={item} />
                        {item.status === 'done' && (
                          <audio
                            controls
                            preload="none"
                            style={{ height: 32, width: '100%' }}
                            src={audioUrl(item.id)}
                          />
                        )}
                      </Table.Td>
                      <Table.Td ta="right" className="mono">
                        {item.audio_seconds != null ? formatDuration(item.audio_seconds) : '—'}
                      </Table.Td>
                      <Table.Td className="mono">{formatDateTime(item.created_at)}</Table.Td>
                      <Table.Td>
                        <Actions item={item} onText={() => setTextOf(item.id)} readOnly={readOnly} />
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )
        }
      </QueryState>
      <TextModal id={textOf} onClose={() => setTextOf(null)} />
    </>
  );
}

/** Aviso para un admin que entró como el cliente. */
export function SupportNotice() {
  return (
    <Text size="xs" c="dimmed">
      Entrando como el cliente solo se ve el historial: generar gastaría sus minutos.
    </Text>
  );
}
