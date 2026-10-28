import {
  Anchor,
  Button,
  Card,
  Grid,
  Group,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconPhoneCall } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router';
import { errorMessage } from '@/api/errors';
import type { Contact } from '@/api/types';
import { CallStatusBadge, Dash, OutcomeBadge } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { PlanGate } from '@/components/PlanGate';
import { EmptyState, ErrorAlert } from '@/components/QueryState';
import { agentOptions } from '@/features/agents/options';
import { useAgents } from '@/features/agents/api';
import { useCalls, useStartCall } from '@/features/calls/api';
import { CallError, CallStartedAlert } from '@/features/calls/NewCallForm';
import { useContacts } from '@/features/contacts/api';
import { usePhoneNumbers } from '@/features/numbers/api';
import { E164_RE, formatDateTime, formatDuration, formatValue } from '@/lib/format';

// El tope de la API (CallIn.context).
const MAX_CONTEXT = 2000;
const RECENT = 10;

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
      description="De la agenda (Contactos). Sus datos también le llegan al agente."
      placeholder="Buscá por nombre o teléfono"
      data={list.map((c) => ({ value: c.id, label: contactLabel(c) }))}
      value={value?.id ?? null}
      onChange={(id) => onChange(list.find((c) => c.id === id) ?? null)}
      searchable
      searchValue={search}
      onSearchChange={setSearch}
      // La búsqueda la hace la API: no filtrar de nuevo acá.
      filter={({ options }) => options}
      nothingFoundMessage={contacts.isPending ? 'Buscando…' : 'Sin contactos: cargalos en Contactos'}
      clearable
      error={error ?? (contacts.isError ? errorMessage(contacts.error) : undefined)}
    />
  );
}

function RecentCalls() {
  const calls = useCalls({ mode: 'saliente', limit: RECENT, offset: 0 });
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
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Fecha</Table.Th>
                <Table.Th>Contacto</Table.Th>
                <Table.Th>Agente</Table.Th>
                <Table.Th>Estado</Table.Th>
                <Table.Th ta="right">Duración</Table.Th>
                <Table.Th>Resultado</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((c) => (
                <Table.Tr key={c.id}>
                  <Table.Td>{formatDateTime(c.created_at)}</Table.Td>
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
                    <CallStatusBadge status={c.status} />
                  </Table.Td>
                  <Table.Td ta="right" className="mono">
                    {formatDuration(c.duration_seconds)}
                  </Table.Td>
                  <Table.Td>
                    <OutcomeBadge label={c.outcome} goal={c.goal} />
                  </Table.Td>
                  <Table.Td ta="right">
                    <Button component={Link} to={`/calls/${c.id}`} variant="subtle" size="compact-sm">
                      Ver detalle
                    </Button>
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
 * Llamada saliente suelta con motivo: el agente llama a un contacto (de la agenda o un número)
 * con el texto que se escribe acá, por ejemplo la consulta que dejó en la web.
 */
export function OutboundCallsPage() {
  const agents = useAgents();
  const [agentId, setAgentId] = useState<string | null>(null);
  const [target, setTarget] = useState<Target>('contact');
  const [contact, setContact] = useState<Contact | null>(null);
  const [phone, setPhone] = useState('');
  const [context, setContext] = useState('');
  const [fromNumber, setFromNumber] = useState<string | null>(null);
  const [testMode, setTestMode] = useState(false);
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

  const submit = () => {
    if (!agent) return setAgentError('Elegí el agente que va a llamar.');
    const p = phone.trim().replace(/[\s-]/g, '');
    if (!testMode) {
      if (target === 'contact' && !contact)
        return setTargetError('Elegí un contacto o activá el modo prueba.');
      if (target === 'phone' && !E164_RE.test(p))
        return setTargetError('Formato internacional: + y entre 8 y 15 dígitos (ej. +5493515551234).');
    }
    setTargetError(null);
    start.mutate(
      {
        agent_id: agent.id,
        // Con contacto, la API marca su teléfono: en modo prueba (sin marcar) va solo el motivo.
        contact_id: !testMode && target === 'contact' ? (contact?.id ?? null) : null,
        phone: !testMode && target === 'phone' ? p : null,
        from_number_id: testMode ? null : from,
        context: context.trim() || null,
        loadtest: false,
      },
      {
        onSuccess: () => {
          setContext('');
          setPhone('');
          setContact(null);
        },
      },
    );
  };

  return (
    <Stack gap="md">
      <PageHeader
        title="Llamadas"
        description="El agente llama a un contacto con el motivo que escribís, por ejemplo la consulta que dejó en tu web, y al cortar queda el resultado para que tu equipo siga."
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
          <Grid gutter="md">
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Stack gap="sm">
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
                    { value: 'contact', label: 'Contacto de la agenda' },
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
                    disabled={testMode}
                    error={targetError}
                    autoComplete="off"
                  />
                )}
                {!testMode && (
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
                )}
              </Stack>
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Stack gap="sm">
                <Textarea
                  label="Motivo del llamado"
                  description="Lo que el contacto dejó escrito o lo que necesitás que resuelva. El agente lo usa para ir al punto, sin leerlo."
                  placeholder="Dejó una consulta en la web: quiere precio y formas de pago, y pregunta si le toman el usado."
                  autosize
                  minRows={5}
                  maxRows={12}
                  maxLength={MAX_CONTEXT}
                  value={context}
                  onChange={(e) => setContext(e.currentTarget.value)}
                />
                <Text size="xs" c="dimmed" ta="right" className="mono">
                  {context.length}/{MAX_CONTEXT}
                </Text>
                <Switch
                  label="Modo prueba"
                  description="No marca ningún teléfono: te conectás por navegador y hacés de contacto. Se usa solo el motivo."
                  checked={testMode}
                  onChange={(e) => setTestMode(e.currentTarget.checked)}
                />
              </Stack>
            </Grid.Col>
          </Grid>
          <Group gap="sm" align="center" mt="md">
            <Button
              leftSection={<IconPhoneCall size={18} />}
              onClick={submit}
              loading={start.isPending}
              disabled={!agent}
            >
              {testMode ? 'Crear llamada de prueba' : 'Llamar'}
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
