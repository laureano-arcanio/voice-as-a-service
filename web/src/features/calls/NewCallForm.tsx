import { Alert, Anchor, Button, Grid, Group, Select, Stack, Switch, Text, TextInput } from '@mantine/core';
import { IconAlertTriangle, IconCircleCheck, IconPhoneCall } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router';
import { ApiError, errorMessage } from '@/api/errors';
import type { Agent, CallStarted } from '@/api/types';
import { agentOptions } from '@/features/agents/options';
import { useIsAdmin } from '@/features/auth/api';
import { useAgents } from '@/features/agents/api';
import { useClients } from '@/features/clients/api';
import { usePhoneNumbers } from '@/features/numbers/api';
import { VoicePicker } from '@/features/voices/VoicePicker';
import { VoicePreview } from '@/features/voices/VoicePreview';
import { E164_RE } from '@/lib/format';
import { QUOTA_TITLES } from '@/lib/labels';
import { useStartCall } from './api';

const HINT_PHONE =
  'Llamada saliente: el agente marca el número (formato E.164, ej. +5491155551234). Las entrantes las atiende solo; todas quedan en Conversaciones.';
const HINT_TEST =
  'Se crea la llamada sin marcar ningún teléfono. Te aparece un link para conectarte por navegador (LiveKit Meet) y hablar con el agente.';

function CallError({ error }: { error: unknown }) {
  const quota = error instanceof ApiError && error.status === 429;
  const title = quota
    ? (QUOTA_TITLES[error.code ?? ''] ?? 'Límite del plan')
    : error instanceof ApiError && error.status === 502
      ? 'No se pudo iniciar la llamada'
      : 'Error';
  return (
    <Alert color={quota ? 'yellow' : 'red'} icon={<IconAlertTriangle size={18} />} title={title}>
      <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
        {errorMessage(error)}
      </Text>
    </Alert>
  );
}

function CallStartedAlert({ started }: { started: CallStarted }) {
  return (
    <Alert
      color="green"
      icon={<IconCircleCheck size={18} />}
      title={started.join_url ? 'Llamada de prueba creada' : 'Llamada iniciada'}
    >
      <Stack gap={4}>
        {started.join_url ? (
          <>
            <Anchor href={started.join_url} target="_blank" rel="noopener noreferrer" fw={600}>
              Conectate acá para hablar con el agente
            </Anchor>
            <Text size="xs" c="dimmed">
              Abrilo ahora: el link no se vuelve a mostrar.
            </Text>
          </>
        ) : (
          <Text size="sm">El estado se actualiza solo.</Text>
        )}
        <Anchor component={Link} to={`/calls/${started.conversation_id}`} size="sm">
          Ver en vivo
        </Anchor>
      </Stack>
    </Alert>
  );
}

/**
 * Lanza una llamada saliente o de prueba. Con `fixedAgent`, sin selector de agente
 * (pestaña Probar del agente).
 */
export function NewCallForm({ fixedAgent }: { fixedAgent?: Agent }) {
  const isAdmin = useIsAdmin();
  const agents = useAgents(undefined, false);
  const clients = useClients(isAdmin && !fixedAgent);
  const [agentId, setAgentId] = useState<string | null>(fixedAgent?.id ?? null);
  const [testMode, setTestMode] = useState(false);
  const [phone, setPhone] = useState('');
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [fromNumber, setFromNumber] = useState<string | null>(null);
  const [voice, setVoice] = useState('');
  const start = useStartCall();

  const list = agents.data ?? [];
  const agent = fixedAgent ?? list.find((a) => a.id === agentId) ?? list[0];
  const numbers = usePhoneNumbers({ clientId: agent?.client_id }, !!agent);
  const fromOptions = (numbers.data ?? [])
    .filter((n) => n.client_id === agent?.client_id)
    .map((n) => ({ value: n.id, label: n.label ? `${n.e164} · ${n.label}` : n.e164 }));

  const submit = () => {
    if (!agent) return;
    const p = phone.trim().replace(/[\s-]/g, '');
    if (!testMode) {
      if (!p) return setPhoneError('Ingresá un número de teléfono o activá el modo prueba.');
      if (!E164_RE.test(p))
        return setPhoneError('Formato E.164: + y entre 8 y 15 dígitos (ej. +5491155551234).');
    }
    setPhoneError(null);
    start.mutate(
      {
        agent_id: agent.id,
        phone: testMode ? null : p,
        from_number_id: testMode ? null : fromNumber,
        voice: voice || null,
        loadtest: false,
      },
      { onSuccess: () => setPhone('') },
    );
  };

  return (
    <Stack gap="md">
      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Stack gap="sm">
            {!fixedAgent && (
              <Select
                label="Agente"
                placeholder={agents.isPending ? 'Cargando…' : 'Elegí un agente'}
                data={agentOptions(list, clients.data, isAdmin)}
                value={agent?.id ?? null}
                onChange={(v) => {
                  setAgentId(v);
                  setFromNumber(null);
                }}
                searchable
                allowDeselect={false}
                nothingFoundMessage="Sin agentes"
                error={agents.isError ? errorMessage(agents.error) : undefined}
              />
            )}
            <Switch
              label="Modo prueba"
              description="Sin teléfono real: te conectás por navegador y hacés de interesado."
              checked={testMode}
              onChange={(e) => setTestMode(e.currentTarget.checked)}
            />
            <TextInput
              label="Teléfono"
              type="tel"
              placeholder={testMode ? '(no hace falta en modo prueba)' : '+5491155551234'}
              value={phone}
              onChange={(e) => setPhone(e.currentTarget.value)}
              disabled={testMode}
              error={phoneError}
              autoComplete="off"
            />
            {!testMode && (
              <Select
                label="Número de origen"
                placeholder={fromOptions.length ? 'El predeterminado' : 'El cliente no tiene números'}
                data={fromOptions}
                value={fromNumber}
                onChange={setFromNumber}
                clearable
                disabled={!fromOptions.length}
              />
            )}
            <VoicePicker value={voice} onChange={setVoice} agentVoice={agent?.voice} />
          </Stack>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <VoicePreview voice={voice || agent?.voice} />
        </Grid.Col>
      </Grid>
      <Group gap="sm" align="center">
        <Button
          leftSection={<IconPhoneCall size={18} />}
          onClick={submit}
          loading={start.isPending}
          disabled={!agent}
        >
          {testMode ? 'Crear llamada de prueba' : 'Llamar'}
        </Button>
        <Text size="xs" c="dimmed" style={{ flex: 1, minWidth: 200 }}>
          {testMode ? HINT_TEST : HINT_PHONE}
        </Text>
      </Group>
      {start.isError && <CallError error={start.error} />}
      {start.isSuccess && <CallStartedAlert started={start.data} />}
    </Stack>
  );
}
