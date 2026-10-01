import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  SimpleGrid,
  Stack,
  Switch,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { IconArrowLeft } from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router';
import { ApiError } from '@/api/errors';
import type { CallDetail, FieldValue } from '@/api/types';
import { CallStatusBadge, OriginBadge, OutcomeBadge, WorkflowBadge } from '@/components/Badges';
import { PageHeader } from '@/components/PageHeader';
import { ErrorAlert, QueryState } from '@/components/QueryState';
import { formatDateTimeLong, formatDuration, formatValue } from '@/lib/format';
import { isCallLive, useCallDetail } from './api';
import { ChatView } from './ChatView';
import { LatencyCard } from './LatencyCard';
import { useFreshFields } from './useFreshFields';
import { asLatency } from './types';

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Stack gap={2}>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text component="div" size="sm" fw={600}>
        {children}
      </Text>
    </Stack>
  );
}

function fieldValue(c: CallDetail, name: string): string {
  return formatValue(c.fields.find((f) => f.name === name)?.value);
}

function FieldBadge({ f }: { f: FieldValue }) {
  if (f.value != null) return <Badge color="green">Obtenido</Badge>;
  return f.required ? (
    <Badge color="yellow">Pendiente</Badge>
  ) : (
    <Text span size="xs" c="dimmed">
      No
    </Text>
  );
}

function FieldsCard({ c }: { c: CallDetail }) {
  const fresh = useFreshFields(c.fields);
  return (
    <Card>
      <Title order={4} mb="sm">
        Estado
      </Title>
      <Table.ScrollContainer minWidth={360}>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Dato</Table.Th>
              <Table.Th>Valor</Table.Th>
              <Table.Th w={110} />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {c.fields.map((f) => (
              <Table.Tr key={f.name} className={fresh.has(f.name) ? 'just-set' : undefined}>
                <Table.Td>
                  <Text size="sm" fw={600}>
                    {f.name}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {f.description}
                  </Text>
                </Table.Td>
                <Table.Td>
                  {f.value != null ? (
                    <Text size="sm">{formatValue(f.value)}</Text>
                  ) : (
                    <Text size="sm" c="dimmed" fs="italic" style={{ whiteSpace: 'nowrap' }}>
                      sin dato
                    </Text>
                  )}
                  {f.rejected != null && (
                    <Text size="xs" c="red">
                      rechazado: {formatValue(f.rejected)}
                    </Text>
                  )}
                </Table.Td>
                <Table.Td ta="center" style={{ whiteSpace: 'nowrap' }}>
                  <FieldBadge f={f} />
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Card>
  );
}

/** Error de Meta de un envio fallido ({code, subcode, message}). */
function waErrorText(err: Record<string, unknown> | null | undefined): string {
  if (!err) return '';
  const code = err.code != null ? String(err.code) : '';
  const hint = code === '131047' ? ' (pasaron más de 24 h desde el último mensaje del contacto)' : '';
  return `${code ? `${code}: ` : ''}${typeof err.message === 'string' ? err.message : ''}${hint}`;
}

function CallHeader({ c }: { c: CallDetail }) {
  const call = c.call;
  const wa = c.whatsapp;
  const required = c.fields.filter((f) => f.required);
  const captured = required.filter((f) => f.value != null).length;
  return (
    <Card>
      <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }} spacing="md" verticalSpacing="md">
        <Item label="Contacto">{fieldValue(c, 'contact_name') || wa?.contact_name || '–'}</Item>
        <Item label="Empresa">
          {fieldValue(c, 'company_name') || fieldValue(c, 'company_context') || '–'}
        </Item>
        <Item label="Origen">
          {wa ? (
            <OriginBadge mode="whatsapp" phone={wa.wa_id} />
          ) : (
            <OriginBadge mode={call ? call.mode : 'api'} phone={call?.phone} />
          )}
        </Item>
        <Item label="Número del cliente">{(wa ? wa.business_number : call?.client_number) || '–'}</Item>
        <Item label="Fecha">{formatDateTimeLong(c.created_at)}</Item>
        {wa ? (
          <>
            <Item label="Último mensaje">{formatDateTimeLong(wa.last_user_at)}</Item>
            <Item label="Envíos fallidos">
              {wa.failed_messages ? (
                <Text span inherit c="red">
                  {wa.failed_messages}
                </Text>
              ) : (
                0
              )}
            </Item>
          </>
        ) : (
          <>
            <Item label="Estado">
              <CallStatusBadge status={call?.status} />
            </Item>
            <Item label="Duración">{formatDuration(call?.duration_seconds)}</Item>
            <Item label="Fin de llamada">{call?.ended_reason || '–'}</Item>
          </>
        )}
        <Item label="Datos obtenidos">
          {captured} de {required.length}
        </Item>
        <Item label="Resultado">
          {c.outcome ? <OutcomeBadge label={c.outcome.label} goal={c.outcome.goal} /> : '–'}
        </Item>
        <Item label="Agente">
          {c.agent_id ? (
            <Anchor component={Link} to={`/agents/${c.agent_id}`} size="sm" fw={600}>
              {c.agent_name ?? 'Agente'}
            </Anchor>
          ) : (
            (c.agent_name ?? '–')
          )}
          {c.agent_version != null && (
            <Text span size="xs" c="dimmed">
              {' '}
              v{c.agent_version}
            </Text>
          )}
        </Item>
        {c.client_name && <Item label="Cliente">{c.client_name}</Item>}
      </SimpleGrid>
      {call?.error && (
        <Alert color="red" mt="md" title="Error">
          {call.error}
        </Alert>
      )}
      {wa?.last_error && (
        <Alert color="red" mt="md" title="Último envío fallido">
          {waErrorText(wa.last_error)}
        </Alert>
      )}
    </Card>
  );
}

function ChatCard({ c, live }: { c: CallDetail; live: boolean }) {
  const [showLlm, setShowLlm] = useState(false);
  return (
    <Card>
      <Group justify="space-between" mb="sm">
        <Group gap="xs">
          <Title order={4}>Conversación</Title>
          {live && (
            <Badge color="blue" variant="dot">
              {c.whatsapp ? 'Activa' : 'En vivo'}
            </Badge>
          )}
        </Group>
        <Switch
          size="sm"
          label="Salida del LLM"
          checked={showLlm}
          onChange={(e) => setShowLlm(e.currentTarget.checked)}
        />
      </Group>
      <ChatView messages={c.messages} showLlm={showLlm} />
    </Card>
  );
}

export function CallDetailPage() {
  const { id } = useParams();
  const query = useCallDetail(id);
  const live = isCallLive(query.data);

  const back = (
    <Button
      component={Link}
      to="/"
      variant="subtle"
      size="compact-sm"
      leftSection={<IconArrowLeft size={16} />}
      w="fit-content"
    >
      Volver al inicio
    </Button>
  );

  if (query.isError && query.error instanceof ApiError && query.error.status === 404) {
    return (
      <>
        <PageHeader title="Conversación" above={back} />
        <ErrorAlert error={query.error} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        above={back}
        docTitle="Conversación"
        title={
          <Group gap="sm" component="span">
            Conversación
            {query.data && <WorkflowBadge status={query.data.workflow_status} />}
          </Group>
        }
      />
      <QueryState query={query}>
        {(c) => (
          <Stack gap="md">
            <CallHeader c={c} />
            <Grid gutter="md">
              <Grid.Col span={{ base: 12, lg: 5 }}>
                <FieldsCard c={c} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, lg: 7 }}>
                <ChatCard c={c} live={live} />
              </Grid.Col>
            </Grid>
            <LatencyCard latency={asLatency(c.call?.latency)} />
          </Stack>
        )}
      </QueryState>
    </>
  );
}
