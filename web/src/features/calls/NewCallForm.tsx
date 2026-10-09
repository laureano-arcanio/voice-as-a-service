import {
  Alert,
  Anchor,
  Button,
  Grid,
  Group,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { IconAlertTriangle, IconCircleCheck, IconPhoneCall } from '@tabler/icons-react';
import { useRef, useState } from 'react';
import { Link } from 'react-router';
import { errorMessage } from '@/api/errors';
import type { Agent, CallIn, CallStarted } from '@/api/types';
import { agentOptions } from '@/features/agents/options';
import { useIsAdmin } from '@/features/auth/api';
import { READ_ONLY_REASON, useReadOnly } from '@/features/auth/readOnly';
import { useAgents } from '@/features/agents/api';
import { useClients } from '@/features/clients/api';
import { usePhoneNumbers } from '@/features/numbers/api';
import { VoicePicker } from '@/features/voices/VoicePicker';
import { VoicePreview } from '@/features/voices/VoicePreview';
import { E164_RE } from '@/lib/format';
import { uuid } from '@/lib/id';
import { useStartCall } from './api';
import { callErrorInfo } from './errors';

const HINT_PHONE =
  'Llamada saliente: el agente marca el número (formato E.164, ej. +5491155551234). Las entrantes las atiende solo; todas quedan en Conversaciones.';
const HINT_TEST =
  'Se crea la llamada sin marcar ningún teléfono. Te aparece un link para conectarte por navegador (LiveKit Meet) y hablar con el agente.';

function CallError({ error, isAdmin }: { error: unknown; isAdmin: boolean }) {
  const { title, message, color } = callErrorInfo(error, isAdmin);
  return (
    <Alert color={color} icon={<IconAlertTriangle size={18} />} title={title}>
      <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
        {message}
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
  const readOnly = useReadOnly();
  const agents = useAgents(undefined, false);
  const clients = useClients(isAdmin && !fixedAgent);
  const [agentId, setAgentId] = useState<string | null>(fixedAgent?.id ?? null);
  const [testMode, setTestMode] = useState(false);
  const [phone, setPhone] = useState('');
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [fromNumber, setFromNumber] = useState<string | null>(null);
  const [voice, setVoice] = useState('');
  const start = useStartCall();
  // Idempotency-Key del ultimo intento: se reusa solo si se repite el mismo pedido despues
  // de un error de red (no se sabe si la llamada se creo); con respuesta, una clave nueva.
  const attempt = useRef<{ body: string; key: string } | null>(null);

  const list = agents.data ?? [];
  const agent = fixedAgent ?? list.find((a) => a.id === agentId) ?? list[0];
  const numbers = usePhoneNumbers({ clientId: agent?.client_id }, !!agent);
  const fromOptions = (numbers.data ?? [])
    .filter((n) => n.client_id === agent?.client_id)
    .map((n) => ({ value: n.id, label: n.label ? `${n.e164} · ${n.label}` : n.e164 }));
  // Sin numero propio el cliente no hace salientes (la API da 409 no_caller_id); el admin si.
  const noCallerId = !isAdmin && !testMode && numbers.isSuccess && fromOptions.length === 0;

  const submit = () => {
    if (!agent || noCallerId || readOnly) return;
    const p = phone.trim().replace(/[\s-]/g, '');
    if (!testMode) {
      if (!p) return setPhoneError('Ingresá un número de teléfono o activá el modo prueba.');
      if (!E164_RE.test(p))
        return setPhoneError('Formato E.164: + y entre 8 y 15 dígitos (ej. +5491155551234).');
    }
    setPhoneError(null);
    const body: CallIn = {
      agent_id: agent.id,
      phone: testMode ? null : p,
      from_number_id: testMode ? null : fromNumber,
      voice: voice || null,
      loadtest: false,
    };
    const sig = JSON.stringify(body);
    const key = attempt.current?.body === sig ? attempt.current.key : uuid();
    attempt.current = { body: sig, key };
    start.mutate(
      { body, idempotencyKey: key },
      {
        onSuccess: () => {
          attempt.current = null;
          setPhone('');
        },
        onError: (e) => {
          if (!(e instanceof TypeError)) attempt.current = null;
        },
      },
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
                placeholder={
                  fromOptions.length
                    ? 'El predeterminado'
                    : isAdmin
                      ? 'El cliente no tiene números'
                      : 'Tu cuenta no tiene números'
                }
                description={
                  noCallerId
                    ? 'Las salientes salen con un número de tu cuenta: pedinos uno. Mientras, usá el modo prueba.'
                    : undefined
                }
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
        <Tooltip
          label={readOnly ? READ_ONLY_REASON : 'Hace falta un número propio para hacer salientes.'}
          disabled={!readOnly && !noCallerId}
          withArrow
        >
          <Button
            leftSection={<IconPhoneCall size={18} />}
            onClick={submit}
            loading={start.isPending}
            // data-disabled y no disabled: un boton disabled no muestra el Tooltip.
            data-disabled={!agent || noCallerId || readOnly || undefined}
            disabled={!agent}
          >
            {testMode ? 'Crear llamada de prueba' : 'Llamar'}
          </Button>
        </Tooltip>
        <Text size="xs" c="dimmed" style={{ flex: 1, minWidth: 200 }}>
          {testMode ? HINT_TEST : HINT_PHONE}
        </Text>
      </Group>
      {start.isError && <CallError error={start.error} isAdmin={isAdmin} />}
      {start.isSuccess && <CallStartedAlert started={start.data} />}
    </Stack>
  );
}
