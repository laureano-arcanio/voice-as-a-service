import { Button, Group, Modal, Stack, Text, TextInput, Textarea } from '@mantine/core';
import { useState } from 'react';
import { Link } from 'react-router';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useApprove, useCancelMessage, useEditDraft } from '../api';
import { MESSAGE_KIND, fmtDateTime } from '../format';
import type { Message } from '../types';
import { MessageStatusBadge } from './Badges';

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Group gap="xs" wrap="nowrap" align="baseline">
      <Text size="xs" c="dimmed" w={70}>
        {label}
      </Text>
      <Text size="sm" style={{ minWidth: 0, overflowWrap: 'anywhere' }}>
        {children}
      </Text>
    </Group>
  );
}

/** Ver un mensaje; si es borrador, editarlo, aprobarlo o descartarlo. */
export function MessageModal({ message, onClose }: { message: Message | null; onClose: () => void }) {
  return (
    <Modal opened={!!message} onClose={onClose} title={message ? MESSAGE_KIND[message.kind] : ''} size="lg">
      {message && <MessageBody key={message.id} m={message} onClose={onClose} />}
    </Modal>
  );
}

function MessageBody({ m, onClose }: { m: Message; onClose: () => void }) {
  const [subject, setSubject] = useState(m.subject);
  const [text, setText] = useState(m.text);
  const edit = useEditDraft();
  const approve = useApprove();
  const cancel = useCancelMessage();
  const isDraft = m.status === 'draft';
  const dirty = subject !== m.subject || text !== m.text;

  const save = async () => {
    if (!dirty) return true;
    try {
      await edit.mutateAsync({ id: m.id, lead_id: m.lead_id, kind: m.kind, subject, text });
      return true;
    } catch (e) {
      notifyError(e, 'No se pudo guardar');
      return false;
    }
  };

  return (
    <Stack gap="sm">
      <Group gap="xs">
        <MessageStatusBadge status={m.status} error={m.error} />
        {m.campaign_slug && (
          <Text size="xs" c="dimmed" className="mono">
            {m.campaign_slug}
          </Text>
        )}
      </Group>
      <Stack gap={2}>
        <Meta label="Lead">
          <Link to={`/leads/${m.lead_id}`} onClick={onClose}>
            {m.lead_name ?? `#${m.lead_id}`}
          </Link>
        </Meta>
        <Meta label={m.direction === 'in' ? 'De' : 'Para'}>
          <span className="mono">{m.direction === 'in' ? m.from_addr : m.to_addr}</span>
        </Meta>
        {m.direction === 'out' && (
          <Meta label="Desde">
            <span className="mono">{m.from_addr}</span>
          </Meta>
        )}
        <Meta label="Fecha">{fmtDateTime(m.sent_at ?? m.queued_at ?? m.created_at)}</Meta>
        {m.in_reply_to && <Meta label="Hilo">responde al mail anterior</Meta>}
      </Stack>
      {isDraft ? (
        <>
          <TextInput label="Asunto" value={subject} onChange={(e) => setSubject(e.currentTarget.value)} />
          <Textarea
            label="Texto"
            value={text}
            onChange={(e) => setText(e.currentTarget.value)}
            autosize
            minRows={6}
            maxRows={18}
          />
          <Group justify="space-between">
            <Button
              variant="subtle"
              color="red"
              loading={cancel.isPending}
              onClick={() =>
                cancel.mutate(m.id, {
                  onSuccess: () => {
                    notifySuccess('Borrador descartado.');
                    onClose();
                  },
                  onError: (e) => notifyError(e),
                })
              }
            >
              Descartar
            </Button>
            <Group gap="xs">
              <Button
                variant="default"
                disabled={!dirty}
                loading={edit.isPending}
                onClick={() => void save().then((ok) => ok && notifySuccess('Borrador guardado.'))}
              >
                Guardar
              </Button>
              <Button
                loading={approve.isPending}
                onClick={async () => {
                  if (!(await save())) return;
                  approve.mutate([m.id], {
                    onSuccess: () => {
                      notifySuccess('Aprobado: sale por la cola.');
                      onClose();
                    },
                    onError: (e) => notifyError(e, 'No se pudo aprobar'),
                  });
                }}
              >
                Aprobar
              </Button>
            </Group>
          </Group>
        </>
      ) : (
        <>
          <Text fw={600} size="sm">
            {m.subject}
          </Text>
          <Text size="sm" style={{ whiteSpace: 'pre-wrap' }} className="crm-mail">
            {m.text || '–'}
          </Text>
          {m.status === 'queued' && (
            <Group justify="flex-end">
              <Button
                variant="subtle"
                color="red"
                loading={cancel.isPending}
                onClick={() =>
                  cancel.mutate(m.id, {
                    onSuccess: () => {
                      notifySuccess('Sacado de la cola.');
                      onClose();
                    },
                    onError: (e) => notifyError(e),
                  })
                }
              >
                Sacar de la cola
              </Button>
            </Group>
          )}
        </>
      )}
    </Stack>
  );
}
