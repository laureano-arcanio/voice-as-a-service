import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
  UnstyledButton,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconPhone, IconSearch } from '@tabler/icons-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import type { CallSummary, Contact, PhoneNumber } from '@/api/types';
import { CallStatusBadge, Dash } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { PlanGate } from '@/components/PlanGate';
import { EmptyState, ErrorAlert } from '@/components/QueryState';
import { useCurrentUser } from '@/features/auth/api';
import { useBlockedNumbers, useContacts, useOptouts } from '@/features/contacts/api';
import { usePhoneNumbers } from '@/features/numbers/api';
import { E164_RE, formatDate, formatDateTime, formatDuration, formatValue } from '@/lib/format';
import { useContactCalls, useMyCalls } from './api';
import { type CallTarget, useDirectCall } from './context';
import { PresenceSwitch } from './PresenceSwitch';
import { storedFrom } from './storage';

const CONTACT_HISTORY = 5;

function numberLabel(n: PhoneNumber): string {
  return n.label ? `${n.e164} · ${n.label}` : n.e164;
}

/** "Saliente" (la hizo el usuario) o "Entrante" (atendió una del equipo); con agente, el agente. */
function callKind(c: CallSummary): string {
  if (c.mode === 'directa') return c.user_name ? `Saliente · ${c.user_name}` : 'Saliente';
  if (c.answered_by === 'team') return c.user_name ? `Entrante · ${c.user_name}` : 'Entrante';
  return c.agent_name ? `Agente · ${c.agent_name}` : c.mode === 'entrante' ? 'Entrante' : 'Saliente';
}

/** Llamar, con el motivo del botón apagado en un tooltip. */
function CallButton({
  target,
  fromId,
  blocked,
  variant = 'subtle',
  label = 'Llamar',
}: {
  target: CallTarget;
  fromId: string | null;
  blocked?: boolean;
  variant?: 'subtle' | 'filled';
  label?: string;
}) {
  const c = useDirectCall();
  const reason = c.disabledReason
    ? c.disabledReason
    : blocked
      ? 'El número está bloqueado: desbloquealo en Contactos, Números bloqueados.'
      : c.busy
        ? 'Ya estás en una llamada.'
        : !fromId
          ? 'Hace falta un número asignado a tu cuenta para llamar.'
          : null;
  const who = target.name || target.phone || '';
  return (
    <Tooltip label={reason} withArrow disabled={!reason} multiline w={240}>
      <Button
        variant={variant}
        size={variant === 'filled' ? 'sm' : 'compact-sm'}
        leftSection={<IconPhone size={variant === 'filled' ? 18 : 16} />}
        data-disabled={!!reason || undefined}
        aria-label={`${label} a ${who}`}
        onClick={(e) => {
          e.stopPropagation();
          if (reason) return e.preventDefault();
          void c.call(target, fromId);
        }}
      >
        {label}
      </Button>
    </Tooltip>
  );
}

function CallsTable({ items, showContact = true }: { items: CallSummary[]; showContact?: boolean }) {
  return (
    <Table.ScrollContainer minWidth={showContact ? 640 : 460}>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Fecha</Table.Th>
            {showContact && <Table.Th>Contacto</Table.Th>}
            <Table.Th>Tipo</Table.Th>
            <Table.Th>Estado</Table.Th>
            <Table.Th ta="right">Duración</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {items.map((c) => (
            <Table.Tr key={c.id}>
              <Table.Td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(c.created_at)}</Table.Td>
              {showContact && (
                <Table.Td>
                  {c.contact_name ? (
                    <>
                      {formatValue(c.contact_name)}
                      {c.phone && (
                        <Text size="xs" c="dimmed" className="mono">
                          {c.phone}
                        </Text>
                      )}
                    </>
                  ) : c.phone ? (
                    <Text span inherit className="mono">
                      {c.phone}
                    </Text>
                  ) : (
                    <Dash />
                  )}
                </Table.Td>
              )}
              <Table.Td>
                <Badge color="gray">{callKind(c)}</Badge>
              </Table.Td>
              <Table.Td>
                <CallStatusBadge status={c.status} endedReason={c.ended_reason} />
              </Table.Td>
              <Table.Td ta="right" className="mono">
                {formatDuration(c.duration_seconds)}
              </Table.Td>
              <Table.Td ta="right">
                <Button
                  component={Link}
                  to={`/calls/${c.id}`}
                  variant="subtle"
                  size="compact-sm"
                  aria-label={`Ver detalle de la llamada del ${formatDateTime(c.created_at)}`}
                >
                  {showContact ? 'Ver detalle' : 'Ver'}
                </Button>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

function ContactPanel({
  contact,
  optedOutSince,
  blocked,
  fromId,
  fromLabel,
}: {
  contact: Contact | null;
  optedOutSince: string | null;
  blocked: boolean;
  fromId: string | null;
  fromLabel: string | null;
}) {
  const recent = useContactCalls(contact?.id, CONTACT_HISTORY);
  if (!contact)
    return (
      <Card h="100%">
        <EmptyState>Elegí un contacto de la lista para ver sus últimas llamadas y llamarlo.</EmptyState>
      </Card>
    );
  const history = recent.data ?? [];
  return (
    <Card h="100%">
      <Stack gap="sm">
        <Group justify="space-between" align="flex-start" gap="sm">
          <Stack gap={2} miw={0}>
            <Title order={4}>{contact.name || contact.phone}</Title>
            <Text size="sm" className="mono" c="dimmed">
              {contact.phone}
            </Text>
          </Stack>
          <CallButton
            target={{ contactId: contact.id, phone: contact.phone, name: contact.name, fromLabel }}
            fromId={fromId}
            blocked={blocked}
            variant="filled"
          />
        </Group>
        {contact.notes && (
          <Text size="sm" c="dimmed" style={{ whiteSpace: 'pre-wrap' }}>
            {contact.notes}
          </Text>
        )}
        {optedOutSince && (
          <Alert color="yellow" p="xs">
            <Text size="sm">
              Pidió no recibir llamadas ({formatDate(optedOutSince)}). Se puede llamar igual, con
              confirmación.
            </Text>
          </Alert>
        )}
        {blocked && (
          <Alert color="red" p="xs">
            <Text size="sm">
              Número bloqueado: no se puede llamar. Se desbloquea en Contactos, Números bloqueados.
            </Text>
          </Alert>
        )}
        <Group justify="space-between">
          <Text className="label">Últimas llamadas</Text>
          <Anchor component={Link} to={`/contacts/${contact.id}`} size="sm">
            Ver la ficha
          </Anchor>
        </Group>
        {recent.isError ? (
          <ErrorAlert error={recent.error} onRetry={() => void recent.refetch()} />
        ) : history.length ? (
          <CallsTable items={history} showContact={false} />
        ) : (
          <EmptyState>
            {recent.isPending ? 'Cargando…' : 'Sin llamadas recientes con este contacto.'}
          </EmptyState>
        )}
      </Stack>
    </Card>
  );
}

function MyCalls({ userId }: { userId: string }) {
  const calls = useMyCalls(userId);
  const items = calls.data?.items ?? [];
  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Title order={4}>Mis últimas llamadas</Title>
        <Anchor component={Link} to="/calls" size="sm">
          Ver todas las conversaciones
        </Anchor>
      </Group>
      {calls.isError ? (
        <ErrorAlert error={calls.error} onRetry={() => void calls.refetch()} />
      ) : items.length ? (
        <CallsTable items={items} />
      ) : (
        <EmptyState>
          {calls.isPending
            ? 'Cargando…'
            : 'Todavía no hiciste ni atendiste llamadas. Elegí un contacto y tocá Llamar.'}
        </EmptyState>
      )}
    </Card>
  );
}

/**
 * Teléfono (docs/LLAMADAS_DIRECTAS_PLAN.md, sección 8): el usuario llama a un contacto, o a un número
 * suelto, desde el navegador y desde un número de su cuenta. Habla él, sin agente; la llamada sigue en
 * la barra de abajo mientras navega por el panel.
 */
export function TelefonoPage() {
  const me = useCurrentUser();
  const c = useDirectCall();
  const numbers = usePhoneNumbers();
  const [chosenFrom, setChosenFrom] = useState<string | null>(() => storedFrom.get(me.id));
  const [search, setSearch] = useState('');
  const [q] = useDebouncedValue(search, 250);
  const [selected, setSelected] = useState<Contact | null>(null);
  const [dial, setDial] = useState('');
  const [dialError, setDialError] = useState<string | null>(null);

  const contacts = useContacts({ q, archived: 'false', offset: 0 });
  const optouts = useOptouts();
  const blockedNumbers = useBlockedNumbers();

  const own = (numbers.data ?? []).filter((n) => n.client_id === me.client_id);
  const from = own.find((n) => n.id === chosenFrom) ?? own[0] ?? null;
  const fromId = from?.id ?? null;
  const fromLabel = from ? numberLabel(from) : null;

  // Bajas de llamadas (voz o todos los canales) y bloqueados, por teléfono.
  const optedOut = useMemo(() => {
    const m = new Map<string, string>();
    for (const o of optouts.data ?? []) if (o.channel !== 'whatsapp') m.set(o.phone, o.created_at);
    return m;
  }, [optouts.data]);
  const blocked = useMemo(
    () => new Set((blockedNumbers.data ?? []).map((b) => b.phone)),
    [blockedNumbers.data],
  );

  const pickFrom = (id: string | null) => {
    setChosenFrom(id);
    storedFrom.set(me.id, id);
  };

  const callNumber = () => {
    const phone = dial.trim().replace(/[\s()-]/g, '');
    if (!E164_RE.test(phone))
      return setDialError('Formato internacional: + y entre 8 y 15 dígitos (ej. +5493515551234).');
    setDialError(null);
    void c.call({ phone, fromLabel }, fromId);
  };

  const items = contacts.data?.items ?? [];
  const total = contacts.data?.total ?? 0;

  return (
    <Stack gap="md">
      <PageHeader
        title="Teléfono"
        description="Llamá a tus contactos desde el navegador: hablás vos, sin agente. La llamada sigue abajo mientras usás el panel."
        actions={c.enabled ? <PresenceSwitch /> : undefined}
      />
      <PlanGate
        feature="direct_calls"
        what="llamadas directas"
        hint="Las llamadas con un agente siguen en Canales, Llamadas."
      >
        <Stack gap="md">
          {c.disabledReason && (
            <Alert color="yellow" p="xs">
              <Text size="sm">{c.disabledReason}</Text>
            </Alert>
          )}
          {numbers.isError ? (
            <ErrorAlert error={numbers.error} onRetry={() => void numbers.refetch()} />
          ) : (
            numbers.data &&
            own.length === 0 && (
              <Alert color="yellow" p="xs">
                <Text size="sm">Todavía no tenés un número asignado: hace falta uno para llamar.</Text>
              </Alert>
            )
          )}
          {own.length > 1 && (
            <Select
              label="Sale desde"
              description="El número que ve el contacto. Se recuerda en este navegador."
              data={own.map((n) => ({ value: n.id, label: numberLabel(n) }))}
              value={fromId}
              onChange={pickFrom}
              allowDeselect={false}
              maw={360}
            />
          )}
          <Grid gutter="md">
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Card h="100%">
                <Stack gap="sm">
                  <TextInput
                    aria-label="Buscar contacto"
                    placeholder="Buscar contacto…"
                    leftSection={<IconSearch size={16} />}
                    value={search}
                    onChange={(e) => setSearch(e.currentTarget.value)}
                  />
                  {contacts.isError ? (
                    <ErrorAlert error={contacts.error} onRetry={() => void contacts.refetch()} />
                  ) : !items.length ? (
                    <EmptyState>
                      {contacts.isPending ? (
                        'Cargando…'
                      ) : q ? (
                        'Ningún contacto coincide con la búsqueda.'
                      ) : (
                        <>
                          Tu agenda está vacía: cargá contactos en{' '}
                          <Anchor component={Link} to="/contacts" inherit>
                            Contactos
                          </Anchor>{' '}
                          o marcá un número abajo.
                        </>
                      )}
                    </EmptyState>
                  ) : (
                    <Stack gap={0} role="list" aria-label="Contactos">
                      {items.map((k) => {
                        const isBlocked = blocked.has(k.phone);
                        const out = optedOut.has(k.phone);
                        return (
                          <Group
                            key={k.id}
                            role="listitem"
                            justify="space-between"
                            wrap="nowrap"
                            gap="sm"
                            py={6}
                            px="xs"
                            className="phone-contact"
                            data-active={selected?.id === k.id || undefined}
                          >
                            <UnstyledButton
                              onClick={() => setSelected(k)}
                              style={{ flex: 1, minWidth: 0 }}
                              aria-label={`Ver ${k.name || k.phone}`}
                            >
                              <Text size="sm" fw={600} truncate>
                                {k.name || k.phone}
                              </Text>
                              <Group gap={6} wrap="wrap">
                                {k.name && (
                                  <Text size="xs" c="dimmed" className="mono">
                                    {k.phone}
                                  </Text>
                                )}
                                {out && <Badge color="yellow">No quiere llamadas</Badge>}
                                {isBlocked && <Badge color="red">Bloqueado</Badge>}
                              </Group>
                            </UnstyledButton>
                            <CallButton
                              target={{ contactId: k.id, phone: k.phone, name: k.name, fromLabel }}
                              fromId={fromId}
                              blocked={isBlocked}
                            />
                          </Group>
                        );
                      })}
                    </Stack>
                  )}
                  {total > items.length && (
                    <Text size="xs" c="dimmed">
                      Se muestran {items.length} de {total}: buscá para encontrar el resto.
                    </Text>
                  )}
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      callNumber();
                    }}
                  >
                    <Group gap="xs" align="flex-start" wrap="nowrap">
                      <TextInput
                        label="O marcá un número"
                        placeholder="+5493515551234"
                        classNames={{ input: 'mono' }}
                        value={dial}
                        onChange={(e) => setDial(e.currentTarget.value)}
                        error={dialError}
                        style={{ flex: 1 }}
                      />
                      <Button
                        type="submit"
                        mt={25}
                        leftSection={<IconPhone size={18} />}
                        disabled={!!c.disabledReason || c.busy || !fromId}
                      >
                        Llamar
                      </Button>
                    </Group>
                  </form>
                </Stack>
              </Card>
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 6 }}>
              <ContactPanel
                contact={selected}
                optedOutSince={selected ? (optedOut.get(selected.phone) ?? null) : null}
                blocked={!!selected && blocked.has(selected.phone)}
                fromId={fromId}
                fromLabel={fromLabel}
              />
            </Grid.Col>
          </Grid>
          <MyCalls userId={me.id} />
        </Stack>
      </PlanGate>
    </Stack>
  );
}
