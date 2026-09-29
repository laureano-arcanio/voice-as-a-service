import {
  Alert,
  Badge,
  Button,
  Group,
  List,
  Modal,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useState } from 'react';
import type { PhoneNumber } from '@/api/types';
import { useAgents } from '@/features/agents/api';
import { useClients } from '@/features/clients/api';
import { useTiers } from '@/features/tiers/api';
import { formatLimit } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { useAssignNumber, useBulkLoadNumbers, useUpdateNumber } from './api';
import { numberErrorTitle } from './errors';
import { MAX_BULK, plural, previewNumbers } from './parse';

type BulkResult = { created: PhoneNumber[]; skipped: { number: string; reason: string }[] };

/** Carga masiva al inventario (quedan libres). */
export function BulkLoadModal({ onClose }: { onClose: () => void }) {
  const load = useBulkLoadNumbers();
  const [text, setText] = useState('');
  const [label, setLabel] = useState('');
  const [provider, setProvider] = useState('anura');
  const [result, setResult] = useState<BulkResult | null>(null);
  const preview = previewNumbers(text);

  const submit = () =>
    load.mutate(
      { numbers: preview.tokens, label: label.trim(), provider: provider.trim() || 'anura' },
      {
        onSuccess: (r) => {
          setResult(r);
          if (r.created.length)
            notifySuccess(`${plural(r.created.length, 'número cargado', 'números cargados')}.`);
        },
        onError: (e) => notifyError(e, 'No se pudo cargar'),
      },
    );

  return (
    <Modal opened onClose={onClose} title="Cargar números" size="lg">
      {result ? (
        <Stack>
          <Alert
            color={result.created.length ? 'green' : 'yellow'}
            title={plural(result.created.length, 'número cargado', 'números cargados')}
          >
            Quedaron libres en el inventario. Corré <code>make livekit-sip</code> en el server para que
            LiveKit los acepte.
          </Alert>
          {result.skipped.length > 0 && (
            <Stack gap={4}>
              <Text size="sm" fw={600}>
                {plural(result.skipped.length, 'salteado', 'salteados')}
              </Text>
              <List size="sm" spacing={2} style={{ maxHeight: 240, overflow: 'auto' }}>
                {result.skipped.map((s, i) => (
                  <List.Item key={i}>
                    <Text span className="mono" size="sm">
                      {s.number}
                    </Text>
                    : {s.reason}
                  </List.Item>
                ))}
              </List>
            </Stack>
          )}
          <Group justify="flex-end">
            <Button
              variant="default"
              onClick={() => {
                setResult(null);
                setText('');
              }}
            >
              Cargar más
            </Button>
            <Button onClick={onClose}>Listo</Button>
          </Group>
        </Stack>
      ) : (
        <Stack>
          <Textarea
            label="Números"
            description="Uno por línea o separados por coma, en formato internacional (+54…). Los repetidos o inválidos se saltean."
            placeholder={'+541152630861\n+541152630862'}
            autosize
            minRows={6}
            maxRows={14}
            value={text}
            onChange={(e) => setText(e.currentTarget.value)}
            data-autofocus
            classNames={{ input: 'mono' }}
          />
          <Group gap="xs">
            <Badge color="green">{plural(preview.valid, 'válido', 'válidos')}</Badge>
            {preview.invalid.length > 0 && (
              <Badge color="red">{plural(preview.invalid.length, 'inválido', 'inválidos')}</Badge>
            )}
            {preview.duplicated.length > 0 && (
              <Badge color="yellow">{plural(preview.duplicated.length, 'repetido', 'repetidos')}</Badge>
            )}
          </Group>
          {preview.tooMany && (
            <Alert color="red" icon={<IconAlertTriangle size={18} />}>
              Máximo {MAX_BULK} por carga: partilo en varias.
            </Alert>
          )}
          <Group grow>
            <TextInput
              label="Etiqueta"
              placeholder="Ej. Lote octubre"
              maxLength={64}
              value={label}
              onChange={(e) => setLabel(e.currentTarget.value)}
            />
            <TextInput
              label="Proveedor"
              value={provider}
              onChange={(e) => setProvider(e.currentTarget.value)}
            />
          </Group>
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              onClick={submit}
              loading={load.isPending}
              disabled={!preview.tokens.length || preview.tooMany}
            >
              Cargar {preview.tokens.length || ''}
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}

/** Asignar un numero libre a un cliente (y opcionalmente rutearlo a un agente). */
export function AssignNumberModal({ number, onClose }: { number: PhoneNumber; onClose: () => void }) {
  const clients = useClients();
  const tiers = useTiers();
  const assign = useAssignNumber();
  const update = useUpdateNumber();
  const [clientId, setClientId] = useState<string | null>(null);
  const [agentId, setAgentId] = useState<string | null>(null);
  const agents = useAgents(clientId ?? undefined, false, !!clientId);
  const limit = new Map((tiers.data ?? []).map((t) => [t.id, t.max_phone_numbers]));

  const clientOptions = (clients.data ?? []).map((c) => {
    const max = limit.get(c.tier.id);
    const used = c.numbers_count ?? 0;
    const full = max != null && used >= max;
    return {
      value: c.id,
      label: `${c.name} · ${used}/${formatLimit(max)}${full ? ' (sin lugar)' : ''}${c.active ? '' : ' (inactivo)'}`,
      disabled: full,
    };
  });

  const submit = () => {
    if (!clientId) return;
    assign.mutate(
      { id: number.id, clientId },
      {
        onSuccess: (n) => {
          if (!agentId) {
            notifySuccess(`${n.e164} asignado a ${n.client_name ?? 'el cliente'}.`);
            return onClose();
          }
          update.mutate(
            { id: n.id, body: { agent_id: agentId } },
            {
              onSuccess: (u) => {
                notifySuccess(
                  `${u.e164} asignado a ${u.client_name ?? 'el cliente'}; lo atiende ${u.agent_name}.`,
                );
                onClose();
              },
              onError: (e) => {
                notifyError(e, 'Se asignó, pero no se pudo elegir el agente');
                onClose();
              },
            },
          );
        },
        onError: (e) => notifyError(e, numberErrorTitle(e) ?? 'No se pudo asignar'),
      },
    );
  };

  return (
    <Modal opened onClose={onClose} title={`Asignar ${number.e164}`}>
      <Stack>
        <Select
          label="Cliente"
          description="Usados / tope de números de su tier."
          data={clientOptions}
          value={clientId}
          onChange={(v) => {
            setClientId(v);
            setAgentId(null);
          }}
          searchable
          data-autofocus
        />
        <Select
          label="Agente que atiende (opcional)"
          placeholder={clientId ? 'Ninguno' : 'Elegí primero el cliente'}
          data={(agents.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
          value={agentId}
          onChange={setAgentId}
          disabled={!clientId}
          clearable
          searchable
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={submit} disabled={!clientId} loading={assign.isPending || update.isPending}>
            Asignar
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

/** Etiqueta (y agente si esta asignado) de un numero. */
export function EditNumberModal({ number, onClose }: { number: PhoneNumber; onClose: () => void }) {
  const update = useUpdateNumber();
  const agents = useAgents(number.client_id ?? undefined, false, !!number.client_id);
  const form = useForm({
    initialValues: { label: number.label, agent_id: number.agent_id ?? '' },
    validate: { label: (v) => (v.length <= 64 ? null : 'Hasta 64 caracteres') },
  });
  const agentOptions = (agents.data ?? []).map((a) => ({ value: a.id, label: a.name }));
  if (number.agent_id && !agentOptions.some((o) => o.value === number.agent_id)) {
    agentOptions.push({ value: number.agent_id, label: `${number.agent_name ?? 'Agente'} (archivado)` });
  }
  return (
    <Modal opened onClose={onClose} title={`Editar ${number.e164}`}>
      <form
        onSubmit={form.onSubmit((v) =>
          update.mutate(
            {
              id: number.id,
              body: number.client_id
                ? { label: v.label.trim(), agent_id: v.agent_id || null }
                : { label: v.label.trim() },
            },
            {
              onSuccess: () => {
                notifySuccess('Número actualizado.');
                onClose();
              },
              onError: (e) => notifyError(e, numberErrorTitle(e)),
            },
          ),
        )}
      >
        <Stack>
          <TextInput label="Etiqueta" maxLength={64} data-autofocus {...form.getInputProps('label')} />
          {number.client_id && (
            <Select
              label="Agente que atiende las entrantes"
              placeholder="Ninguno"
              data={agentOptions}
              clearable
              searchable
              {...form.getInputProps('agent_id')}
            />
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={update.isPending}>
              Guardar
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
