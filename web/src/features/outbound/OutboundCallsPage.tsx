import {
  Anchor,
  Button,
  Card,
  Group,
  SegmentedControl,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconPhoneCall } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router';
import { RowLink } from '@/components/RowLink';
import { useRowLink } from '@/components/useRowLink';
import { errorMessage } from '@/api/errors';
import type { Contact } from '@/api/types';
import { CallStatusBadge, Dash, OutcomeBadge } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { PlanGate } from '@/components/PlanGate';
import { EmptyState, ErrorAlert } from '@/components/QueryState';
import { agentOptions } from '@/features/agents/options';
import { useAgent, useAgents } from '@/features/agents/api';
import { TestVariables } from '@/features/agents/TestVariables';
import { useTestVariables } from '@/features/agents/testVariables';
import { useCalls, useStartCall } from '@/features/calls/api';
import { CallError, CallStartedAlert } from '@/features/calls/CallAlerts';
import { useContacts } from '@/features/contacts/api';
import { usePhoneNumbers } from '@/features/numbers/api';
import { E164_RE, formatDateTime, formatDuration, formatValue } from '@/lib/format';

const RECENT = 10;

/** El motivo es siempre una variable de la llamada, la use el prompt del agente o no. */
const MOTIVO = [{ name: 'motivo', description: 'Por qué se llama' }];

type Target = 'contact' | 'phone';

function contactLabel(c: Contact): string {
  return c.name ? `${c.name} · ${c.phone}` : c.phone;
}

/** Contacto activo de la agenda del cliente, buscado en la API mientras se escribe. */
function ContactPicker({
  clientId,
  value,
  onChange,
  error,
}: {
  clientId?: string;
  value: Contact | null;
  onChange: (c: Contact | null) => void;
  error?: string | null;
}) {
  const [search, setSearch] = useState('');
  const [q] = useDebouncedValue(search, 250);
  const contacts = useContacts({
    clientId,
    q: value && search === contactLabel(value) ? '' : q,
    archived: 'false',
    offset: 0,
  });
  const items = contacts.data?.items ?? [];
  const list = value && !items.some((c) => c.id === value.id) ? [value, ...items] : items;
  return (
    <Select
      label="Contacto"
      description="De tus clientes. Sus datos también le llegan al agente."
      placeholder="Buscá por nombre o teléfono"
      data={list.map((c) => ({ value: c.id, label: contactLabel(c) }))}
      value={value?.id ?? null}
      onChange={(id) => onChange(list.find((c) => c.id === id) ?? null)}
      searchable
      searchValue={search}
      onSearchChange={setSearch}
      // La búsqueda la hace la API: no filtrar de nuevo acá.
      filter={({ options }) => options}
      nothingFoundMessage={contacts.isPending ? 'Buscando…' : 'Sin contactos: cargalos en Tus clientes'}
      clearable
      error={error ?? (contacts.isError ? errorMessage(contacts.error) : undefined)}
    />
  );
}

function RecentCalls() {
  const rowLink = useRowLink();
  const calls = useCalls({ mode: ['saliente'], limit: RECENT, offset: 0 });
  const items = calls.data?.items ?? [];
  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Title order={4}>Últimas llamadas</Title>
        <Anchor component={Link} to="/calls" size="sm">
          Ver todas las conversaciones
        </Anchor>
      </Group>
      {calls.isError ? (
        <ErrorAlert error={calls.error} onRetry={() => void calls.refetch()} />
      ) : !items.length ? (
        <EmptyState>
          {calls.isPending
            ? 'Cargando…'
            : 'Todavía no hay llamadas salientes. La primera aparece acá al llamar.'}
        </EmptyState>
      ) : (
        <Table.ScrollContainer minWidth={640}>
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Fecha</Table.Th>
                <Table.Th>Contacto</Table.Th>
                <Table.Th>Agente</Table.Th>
                <Table.Th>Estado</Table.Th>
                <Table.Th ta="right">Duración</Table.Th>
                <Table.Th>Resultado</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((c) => (
                <Table.Tr key={c.id} {...rowLink(`/calls/${c.id}`)}>
                  <Table.Td>
                    <RowLink to={`/calls/${c.id}`} label={`Ver conversación del ${formatDateTime(c.created_at)}`}>
                      {formatDateTime(c.created_at)}
                    </RowLink>
                  </Table.Td>
                  <Table.Td>
                    {formatValue(c.contact_name) || <Dash />}
                    {c.phone && (
                      <Text size="xs" c="dimmed" className="mono">
                        {c.phone}
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>{c.agent_name ?? <Dash />}</Table.Td>
                  <Table.Td>
                    <CallStatusBadge status={c.status} endedReason={c.ended_reason} />
                  </Table.Td>
                  <Table.Td ta="right" className="mono">
                    {formatDuration(c.duration_seconds)}
                  </Table.Td>
                  <Table.Td>
                    <OutcomeBadge label={c.outcome} goal={c.goal} />
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Card>
  );
}

/**
 * Llamada saliente suelta: el agente llama a un contacto (de la agenda o un número). Las que nadie
 * atiende quedan en la lista de abajo con la marca "No atendida".
 */
export function OutboundCallsPage() {
  const agents = useAgents();
  const [agentId, setAgentId] = useState<string | null>(null);
  const [target, setTarget] = useState<Target>('contact');
  const [contact, setContact] = useState<Contact | null>(null);
  const [phone, setPhone] = useState('');
  const [fromNumber, setFromNumber] = useState<string | null>(null);
  const [targetError, setTargetError] = useState<string | null>(null);
  const [agentError, setAgentError] = useState<string | null>(null);
  const start = useStartCall();

  const list = agents.data ?? [];
  // Sin agente por defecto: llamar con uno que no se eligió es peor que pedir que se elija.
  const agent = list.find((a) => a.id === agentId);
  const numbers = usePhoneNumbers({}, !!agent);
  const clientNumbers = (numbers.data ?? []).filter((n) => n.client_id === agent?.client_id);
  const fromOptions = clientNumbers.map((n) => ({
    value: n.id,
    label: n.label ? `${n.e164} · ${n.label}` : n.e164,
  }));
  // Caller ID: el elegido, o el número que atiende ese agente (así devuelve el llamado desde "su" línea).
  const from = fromNumber ?? clientNumbers.find((n) => n.agent_id === agent?.id)?.id ?? null;
  // Las variables del agente (declaradas y usadas) con sus defaults, y el motivo siempre presente.
  const detail = useAgent(agent?.id);
  const test = useTestVariables(agent?.id ?? '', detail.data?.definition ?? {}, MOTIVO);
  // Una fila vacía no viaja: así el dato del contacto o el default del agente no se pisan con "".
  const testValues = Object.fromEntries(Object.entries(test.variables).filter(([, v]) => v.trim()));

  const submit = () => {
    if (!agent) return setAgentError('Elegí el agente que va a llamar.');
    const p = phone.trim().replace(/[\s-]/g, '');
    if (target === 'contact' && !contact) return setTargetError('Elegí un contacto.');
    if (target === 'phone' && !E164_RE.test(p))
      return setTargetError('Formato internacional: + y entre 8 y 15 dígitos (ej. +5493515551234).');
    setTargetError(null);
    start.mutate(
      {
        agent_id: agent.id,
        // Con contacto, la API marca su teléfono.
        contact_id: target === 'contact' ? (contact?.id ?? null) : null,
        phone: target === 'phone' ? p : null,
        from_number_id: from,
        loadtest: false,
        variables: testValues,
      },
      {
        onSuccess: () => {
          setPhone('');
          setContact(null);
        },
      },
    );
  };

  return (
    <Stack gap="md">
      <PageHeader
        title="Llamadas del agente"
        description="El agente llama a un contacto y, al cortar, queda el resultado para que tu equipo siga. Si no atienden, la llamada queda igual en la lista, marcada como no atendida."
      />
      <PlanGate
        feature="outbound_calls"
        what="llamadas salientes"
        hint="Para hablar con tu agente desde el navegador, usá la pestaña Probar del agente o su link para llamar."
      >
        <Card>
          <Title order={4} mb="sm">
            Nueva llamada
          </Title>
          <Stack gap="sm" maw={520}>
            <Select
              label="Agente"
              placeholder={agents.isPending ? 'Cargando…' : 'Elegí un agente'}
              data={agentOptions(list)}
              value={agent?.id ?? null}
              onChange={(v) => {
                setAgentId(v);
                setAgentError(null);
                setContact(null);
                setFromNumber(null);
              }}
              searchable
              allowDeselect={false}
              nothingFoundMessage="Sin agentes"
              error={agentError ?? (agents.isError ? errorMessage(agents.error) : undefined)}
            />
            <SegmentedControl
              value={target}
              onChange={(v) => {
                setTarget(v as Target);
                setTargetError(null);
              }}
              data={[
                { value: 'contact', label: 'Uno de tus clientes' },
                { value: 'phone', label: 'Otro número' },
              ]}
            />
            {target === 'contact' ? (
              <ContactPicker
                clientId={agent?.client_id}
                value={contact}
                onChange={(c) => {
                  setContact(c);
                  setTargetError(null);
                }}
                error={targetError}
              />
            ) : (
              <TextInput
                label="Teléfono"
                type="tel"
                placeholder="+5493515551234"
                value={phone}
                onChange={(e) => setPhone(e.currentTarget.value)}
                error={targetError}
                autoComplete="off"
              />
            )}
            <Select
              label="Número de origen"
              description="Por defecto, el número que atiende el agente."
              placeholder={
                !agent
                  ? 'Elegí primero el agente'
                  : fromOptions.length
                    ? 'El primero del cliente'
                    : 'El cliente no tiene números'
              }
              data={fromOptions}
              value={from}
              onChange={setFromNumber}
              allowDeselect={false}
              disabled={!fromOptions.length}
            />
            {agent && (
              <TestVariables
                rows={test.rows}
                onChange={test.setRows}
                fixedNames={[...test.names.map((n) => n.name), ...MOTIVO.map((m) => m.name)]}
                description="Lo que el agente ve en esta llamada: las variables que declara o usa en su prompt y el motivo. El motivo lo lee si su prompt dice {{motivo}}. Se recuerdan en esta pestaña."
              />
            )}
          </Stack>
          <Group gap="sm" align="center" mt="md">
            <Button
              leftSection={<IconPhoneCall size={18} />}
              onClick={submit}
              loading={start.isPending}
              disabled={!agent}
            >
              Llamar
            </Button>
            <Text size="xs" c="dimmed" style={{ flex: 1, minWidth: 200 }}>
              Al cortar, el resultado (por ejemplo, a qué área pasa y con qué urgencia) queda en
              Conversaciones y, si el agente tiene el resumen por email prendido, le llega a tu equipo.
            </Text>
          </Group>
          <Stack gap="sm" mt="md">
            {start.isError && <CallError error={start.error} />}
            {start.isSuccess && <CallStartedAlert started={start.data} />}
          </Stack>
        </Card>
      </PlanGate>
      <RecentCalls />
    </Stack>
  );
}
