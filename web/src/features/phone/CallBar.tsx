import {
  ActionIcon,
  Anchor,
  Badge,
  Box,
  Button,
  CloseButton,
  Group,
  Modal,
  Popover,
  ScrollArea,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core';
import {
  IconAlertCircle,
  IconDialpad,
  IconMessage2,
  IconMicrophone,
  IconMicrophoneOff,
  IconPhone,
  IconPhoneIncoming,
  IconPhoneOff,
  IconVolume,
} from '@tabler/icons-react';
import { type ReactNode, useEffect, useState } from 'react';
import { Link } from 'react-router';
import { LiveBadge } from '@/components/Badges';
import { useUpsertContact } from '@/features/contacts/api';
import { formatDuration } from '@/lib/format';
import { notifyError, notifySuccess } from '@/lib/notify';
import { type CallPhase, type CallResult, DTMF_KEYS, useDirectCall, usePresence } from './context';
import { PresenceSwitch } from './PresenceSwitch';
import type { Ringing } from './types';

const PHASE_LABEL: Record<CallPhase, string> = {
  idle: '',
  mic: 'Conectando micrófono',
  connecting: 'Conectando',
  dialing: 'Llamando',
  ringing: 'Sonando',
  active: 'En curso',
  ended: 'Terminada',
  error: 'Error',
};

const RESULT_LABEL: Record<CallResult, { label: string; color: string }> = {
  completed: { label: 'Terminada', color: 'green' },
  no_answer: { label: 'Terminada · no atendió', color: 'yellow' },
  busy: { label: 'Terminada · ocupado', color: 'yellow' },
  failed: { label: 'Terminada · falló', color: 'red' },
  hangup: { label: 'Terminada · cortada', color: 'gray' },
};

// Lado izquierdo de la barra (estado y con quién): ocupa lo que sobra y, en el celular, baja los botones a otra
// línea antes de quedar sin lugar para el nombre.
const FILL = { flex: '1 1 240px' } as const;

/** m:ss desde `since`, al segundo. */
function Timer({ since }: { since: number }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);
  return (
    <Text size="sm" className="mono" aria-label="Duración">
      {formatDuration(Math.max(1, (now - since) / 1000))}
    </Text>
  );
}

/** Quién y desde qué línea: el nombre del contacto (o el teléfono) y debajo el teléfono y la línea. */
function Who() {
  const { target, direction } = useDirectCall();
  const name = target?.name || target?.phone || (direction === 'inbound' ? 'Llamada entrante' : 'Llamada');
  const line = target?.fromLabel
    ? direction === 'inbound'
      ? `a ${target.fromLabel}`
      : `desde ${target.fromLabel}`
    : null;
  return (
    <Stack gap={0} miw={0}>
      <Text size="sm" fw={600} truncate>
        {name}
      </Text>
      {(target?.name || line) && (
        <Text size="xs" c="dimmed" truncate>
          {target?.name && target.phone && (
            <Text span inherit className="mono">
              {target.phone}
            </Text>
          )}
          {target?.name && target.phone && line ? ' · ' : ''}
          {line}
        </Text>
      )}
    </Stack>
  );
}

function Keypad({ disabled }: { disabled: boolean }) {
  const { dtmf } = useDirectCall();
  const [typed, setTyped] = useState('');
  return (
    <Popover position="top" withArrow shadow="md">
      <Popover.Target>
        <Tooltip label={disabled ? 'El teclado se usa con la llamada en curso' : 'Teclado'} withArrow>
          <ActionIcon variant="default" size="lg" aria-label="Teclado" disabled={disabled}>
            <IconDialpad size={18} />
          </ActionIcon>
        </Tooltip>
      </Popover.Target>
      <Popover.Dropdown>
        <Stack gap="xs" w={168}>
          <Text className="mono" ta="center" size="sm" mih={20} aria-live="polite">
            {typed}
          </Text>
          <SimpleGrid cols={3} spacing={6}>
            {DTMF_KEYS.map((d) => (
              <Button
                key={d}
                variant="default"
                className="mono"
                style={d === '0' ? { gridColumn: 2 } : undefined}
                onClick={() => {
                  dtmf(d);
                  setTyped((s) => (s + d).slice(-16));
                }}
              >
                {d}
              </Button>
            ))}
          </SimpleGrid>
        </Stack>
      </Popover.Dropdown>
    </Popover>
  );
}

function TranscriptButton() {
  const { transcript } = useDirectCall();
  return (
    <Popover position="top-end" withArrow shadow="md" width={360}>
      <Popover.Target>
        <Tooltip label="Transcripción" withArrow>
          <ActionIcon variant="default" size="lg" aria-label="Transcripción">
            <IconMessage2 size={18} />
          </ActionIcon>
        </Tooltip>
      </Popover.Target>
      <Popover.Dropdown>
        <Text className="label" mb={6}>
          Transcripción en vivo
        </Text>
        <ScrollArea.Autosize mah={300}>
          {transcript.length ? (
            <Stack gap={6}>
              {transcript.map((l) => (
                <Text key={l.id} size="sm">
                  <Text span inherit fw={600} c={l.mine ? 'blue' : undefined}>
                    {l.who}:
                  </Text>{' '}
                  {l.text}
                </Text>
              ))}
            </Stack>
          ) : (
            <Text size="sm" c="dimmed">
              Las frases aparecen acá mientras hablan.
            </Text>
          )}
        </ScrollArea.Autosize>
      </Popover.Dropdown>
    </Popover>
  );
}

function Bar({ children }: { children: ReactNode }) {
  return (
    <Group h="100%" px="md" py={6} gap="sm" justify="space-between" wrap="wrap" align="center">
      {children}
    </Group>
  );
}

function LiveBar() {
  const c = useDirectCall();
  const last = c.transcript.at(-1);
  const status = PHASE_LABEL[c.phase];
  return (
    <Bar>
      <Group gap="sm" wrap="nowrap" miw={0} style={FILL}>
        {c.phase === 'active' || c.phase === 'ringing' || c.phase === 'dialing' ? (
          <LiveBadge>{status}</LiveBadge>
        ) : (
          <Badge color="gray">{status}</Badge>
        )}
        {c.phase === 'active' && c.startedAt && <Timer since={c.startedAt} />}
        <Who />
        <Stack gap={0} miw={0} visibleFrom="md" style={{ flex: 1 }}>
          {last && (
            <Text size="xs" truncate>
              <Text span inherit fw={600}>
                {last.who}:
              </Text>{' '}
              “{last.text}”
            </Text>
          )}
          <Text size="xs" c="dimmed" truncate>
            Usá auriculares: así no vuelve tu voz como eco.
          </Text>
        </Stack>
      </Group>
      <Group gap="xs" wrap="nowrap">
        {c.audioBlocked && (
          <Button
            size="compact-sm"
            color="yellow"
            leftSection={<IconVolume size={16} />}
            onClick={c.startAudio}
          >
            Activar el audio
          </Button>
        )}
        <Tooltip label={c.muted ? 'Activar micrófono' : 'Silenciar'} withArrow>
          <ActionIcon
            variant={c.muted ? 'light' : 'default'}
            color={c.muted ? 'yellow' : undefined}
            size="lg"
            aria-label={c.muted ? 'Activar micrófono' : 'Silenciar'}
            aria-pressed={c.muted}
            disabled={c.phase === 'mic'}
            onClick={c.toggleMute}
          >
            {c.muted ? <IconMicrophoneOff size={18} /> : <IconMicrophone size={18} />}
          </ActionIcon>
        </Tooltip>
        <Keypad disabled={c.phase !== 'active'} />
        <TranscriptButton />
        <Button color="red" size="sm" leftSection={<IconPhoneOff size={18} />} onClick={c.hangup}>
          Cortar
        </Button>
      </Group>
    </Bar>
  );
}

function SaveContactModal({ phone, onClose }: { phone: string; onClose: () => void }) {
  const save = useUpsertContact();
  const [name, setName] = useState('');
  const submit = () =>
    save.mutate(
      { phone, name: name.trim() || null },
      {
        onSuccess: (r) => {
          notifySuccess(r.created ? 'Contacto guardado.' : 'Ese teléfono ya estaba en la agenda.');
          onClose();
        },
        onError: (e) => notifyError(e, 'No se pudo guardar'),
      },
    );
  return (
    <Modal opened onClose={onClose} title="Guardar como contacto">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <Stack>
          <TextInput label="Teléfono" value={phone} disabled classNames={{ input: 'mono' }} />
          <TextInput
            label="Nombre"
            placeholder="Ana Pérez"
            value={name}
            onChange={(e) => setName(e.currentTarget.value)}
            data-autofocus
          />
          <Group justify="flex-end" gap="xs">
            <Button variant="default" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" loading={save.isPending}>
              Guardar contacto
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

function EndedBar() {
  const c = useDirectCall();
  const [saving, setSaving] = useState(false);
  const r = RESULT_LABEL[c.result ?? 'completed'];
  const seconds = c.startedAt && c.endedAt ? (c.endedAt - c.startedAt) / 1000 : 0;
  const phone = c.target?.phone;
  const canSave = !!phone && !c.target?.contactId && c.direction === 'outbound';
  return (
    <Bar>
      <Group gap="sm" wrap="nowrap" miw={0} style={FILL}>
        <Badge color={r.color}>{r.label}</Badge>
        {seconds > 0 && (
          <Text size="sm" className="mono" aria-label="Duración">
            {formatDuration(seconds)}
          </Text>
        )}
        <Who />
      </Group>
      <Group gap="xs" wrap="nowrap">
        {c.conversationId && (
          <Button component={Link} to={`/calls/${c.conversationId}`} variant="default" size="compact-sm">
            Ver la conversación
          </Button>
        )}
        {canSave && (
          <Button variant="subtle" size="compact-sm" onClick={() => setSaving(true)}>
            Guardar como contacto
          </Button>
        )}
        <Box visibleFrom="sm">
          <PresenceSwitch size="xs" />
        </Box>
        <CloseButton aria-label="Cerrar" onClick={c.dismiss} />
      </Group>
      {saving && phone && <SaveContactModal phone={phone} onClose={() => setSaving(false)} />}
    </Bar>
  );
}

function ErrorBar() {
  const c = useDirectCall();
  return (
    <Bar>
      <Group gap="sm" wrap="nowrap" miw={0} style={FILL} role="alert">
        <IconAlertCircle size={20} color="var(--mantine-color-red-6)" style={{ flex: 'none' }} />
        <Stack gap={0} miw={0}>
          <Text size="sm" fw={600}>
            {c.error?.title}
          </Text>
          <Text size="xs" c="dimmed" lineClamp={2}>
            {c.error?.message}
          </Text>
        </Stack>
      </Group>
      <Group gap="xs" wrap="nowrap">
        <Box visibleFrom="sm">
          <PresenceSwitch size="xs" />
        </Box>
        <CloseButton aria-label="Cerrar" onClick={c.dismiss} />
      </Group>
    </Bar>
  );
}

function RingBar({ ring, more }: { ring: Ringing; more: number }) {
  const c = useDirectCall();
  const { decline } = usePresence();
  const [answering, setAnswering] = useState(false);
  const line = ring.number_label || ring.number_e164;
  const failed = c.phase === 'error' && c.failedRingId === ring.conversation_id && !!c.error;
  return (
    <Bar>
      <Group gap="sm" wrap="nowrap" miw={0} style={FILL}>
        <IconPhoneIncoming size={20} color="var(--mantine-color-blue-6)" style={{ flex: 'none' }} />
        <LiveBadge>Llamada entrante</LiveBadge>
        <Stack gap={0} miw={0}>
          <Text size="sm" fw={600} truncate>
            {ring.contact_name || ring.phone || 'Número privado'}
          </Text>
          <Text size="xs" c="dimmed" truncate>
            {ring.contact_name && ring.phone && (
              <Text span inherit className="mono">
                {ring.phone}
              </Text>
            )}
            {ring.contact_name && ring.phone && line ? ' · ' : ''}
            {line && `a ${line}`}
            {more > 0 && ` · ${more} más sonando`}
          </Text>
          {/* No pudo atender (el micrófono): el timbre sigue, con el motivo, para arreglarlo y volver a probar. */}
          {failed && (
            <Text size="xs" c="red.7" fw={600} role="alert" truncate>
              {c.error?.title}
            </Text>
          )}
        </Stack>
      </Group>
      <Group gap="xs" wrap="nowrap">
        <Button
          size="sm"
          leftSection={<IconPhone size={18} />}
          loading={answering}
          disabled={!!c.disabledReason}
          onClick={() => {
            setAnswering(true);
            void c.answer(ring).finally(() => setAnswering(false));
          }}
        >
          Atender
        </Button>
        <Button size="sm" variant="subtle" color="red" onClick={() => decline(ring)} disabled={answering}>
          Rechazar
        </Button>
      </Group>
    </Bar>
  );
}

function RejoinBar({ id }: { id: string }) {
  const c = useDirectCall();
  const [joining, setJoining] = useState(false);
  return (
    <Bar>
      <Group gap="sm" wrap="nowrap" miw={0} style={FILL}>
        <IconPhone size={20} color="var(--mantine-color-blue-6)" style={{ flex: 'none' }} />
        <Text size="sm" fw={600}>
          Tenés una llamada en curso
        </Text>
      </Group>
      <Group gap="xs" wrap="nowrap">
        <Button
          size="sm"
          loading={joining}
          onClick={() => {
            setJoining(true);
            void c.join(id).finally(() => setJoining(false));
          }}
        >
          Volver a entrar
        </Button>
        <CloseButton aria-label="Descartar" onClick={c.dismissRejoin} />
      </Group>
    </Bar>
  );
}

function IdleBar() {
  return (
    <Group h="100%" px="md" justify="space-between" wrap="nowrap">
      <Anchor component={Link} to="/telefono" size="sm" c="dimmed">
        <Group gap={6} wrap="nowrap">
          <IconPhone size={16} />
          Teléfono del equipo
        </Group>
      </Anchor>
      <PresenceSwitch size="xs" />
    </Group>
  );
}

/**
 * Barra de llamada, fija abajo en todo el panel del cliente (el footer del AppShell): la llamada en curso,
 * el timbre de una entrante, "Volver a entrar" después de recargar y Disponible.
 */
export function CallBar() {
  const c = useDirectCall();
  const { rings } = usePresence();
  if (c.busy) return <LiveBar />;
  if (rings.length) return <RingBar ring={rings[0]} more={rings.length - 1} />;
  if (c.phase === 'error') return <ErrorBar />;
  if (c.phase === 'ended') return <EndedBar />;
  if (c.rejoinId) return <RejoinBar id={c.rejoinId} />;
  return <IdleBar />;
}
