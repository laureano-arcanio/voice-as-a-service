import {
  Alert,
  Anchor,
  Avatar,
  Button,
  Card,
  Center,
  Grid,
  Group,
  List,
  Loader,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { IconMicrophone, IconMicrophoneOff, IconPhoneOff, IconVolume } from '@tabler/icons-react';
import {
  createLocalAudioTrack,
  type LocalAudioTrack,
  type Participant,
  Room,
  RoomEvent,
  Track,
} from 'livekit-client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router';
import { api } from '@/api/client';
import { errorMessage } from '@/api/errors';
import { unwrap } from '@/api/request';
import { PageHeader } from '@/components/PageHeader';
import { EmptyState } from '@/components/QueryState';
import { initials } from '@/lib/initials';
import { isLiveStatus } from '@/lib/labels';
import { useCallDetail, useHangUp } from './api';
import { ChatView } from './ChatView';

type Phase =
  | 'checking' // leyendo el permiso del micrófono
  | 'ask' // falta el permiso: aviso grande antes de pedírselo al navegador
  | 'denied' // bloqueado: pasos para habilitarlo
  | 'no-mic'
  | 'connecting'
  | 'live'
  | 'ended'
  | 'error';

/** El permiso del micrófono sin pedirlo. Sin la Permissions API (o sin "microphone", Firefox viejo): "prompt". */
async function micPermission(): Promise<PermissionState> {
  try {
    return (await navigator.permissions.query({ name: 'microphone' as PermissionName })).state;
  } catch {
    return 'prompt';
  }
}

function micSteps(): string[] {
  return /iPhone|iPad|iPod/.test(navigator.userAgent)
    ? ['Tocá "aA" en la barra de direcciones.', 'Configuración del sitio → Micrófono → Permitir.']
    : [
        'Hacé clic en el candado (o el ícono de ajustes) de la barra de direcciones.',
        'Micrófono → Permitir.',
      ];
}

function Tile({
  name,
  label,
  speaking,
  muted,
}: {
  name: string;
  label: string;
  speaking: boolean;
  muted?: boolean;
}) {
  return (
    <Stack align="center" gap={6}>
      <Avatar
        size={88}
        radius="xl"
        color={speaking ? 'blue' : 'gray'}
        variant={speaking ? 'filled' : 'light'}
      >
        {initials(name)}
      </Avatar>
      <Text fw={600}>{name}</Text>
      <Group gap={4} c="dimmed">
        {muted && <IconMicrophoneOff size={14} aria-label="Micrófono silenciado" />}
        <Text size="xs" c="dimmed">
          {speaking ? 'Hablando…' : label}
        </Text>
      </Group>
    </Stack>
  );
}

/**
 * Llamada de prueba desde el navegador (reemplaza a LiveKit Meet): revisa el permiso del micrófono
 * antes de conectar, lo pide con un clic, y entra con el micrófono y el audio prendidos.
 */
export function TestCallPage() {
  const { id = '' } = useParams();
  const detail = useCallDetail(id);
  const hangUp = useHangUp(id);
  const [phase, setPhase] = useState<Phase>('checking');
  const [error, setError] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const [audioBlocked, setAudioBlocked] = useState(false);
  const [agentSpeaks, setAgentSpeaks] = useState(false);
  const [userSpeaks, setUserSpeaks] = useState(false);
  const room = useRef<Room | null>(null);
  const mic = useRef<LocalAudioTrack | null>(null);
  const started = useRef(false);

  const c = detail.data;
  const callLive = c ? isLiveStatus(c.call?.status) : true;
  const agentName = c?.agent_name ?? 'Agente';

  const release = useCallback(() => {
    room.current?.removeAllListeners();
    void room.current?.disconnect();
    room.current = null;
    mic.current?.stop();
    mic.current = null;
    document.querySelectorAll('audio[data-test-call]').forEach((el) => el.remove());
  }, []);

  /** Micrófono (con el permiso ya dado o pidiéndolo ahora) y la room. */
  const connect = useCallback(async () => {
    if (started.current) return;
    started.current = true;
    setError(null);
    setPhase('connecting');
    try {
      mic.current = await createLocalAudioTrack({
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      });
    } catch (e) {
      started.current = false;
      const name = e instanceof DOMException ? e.name : '';
      setPhase(name === 'NotFoundError' || name === 'OverconstrainedError' ? 'no-mic' : 'denied');
      return;
    }
    try {
      const join = await unwrap(
        api.POST('/api/v1/calls/{conversation_id}/join', { params: { path: { conversation_id: id } } }),
      );
      const r = new Room({ adaptiveStream: false, dynacast: false });
      room.current = r;
      r.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind !== Track.Kind.Audio) return;
        const el = track.attach();
        el.dataset.testCall = '';
        el.hidden = true;
        document.body.appendChild(el);
      });
      r.on(RoomEvent.TrackUnsubscribed, (track) => track.detach().forEach((el) => el.remove()));
      r.on(RoomEvent.AudioPlaybackStatusChanged, () => setAudioBlocked(!r.canPlaybackAudio));
      r.on(RoomEvent.ActiveSpeakersChanged, (speakers: Participant[]) => {
        const local = r.localParticipant.identity;
        setAgentSpeaks(speakers.some((p) => p.identity !== local));
        setUserSpeaks(speakers.some((p) => p.identity === local));
      });
      r.on(RoomEvent.Disconnected, () => {
        setPhase('ended');
        release();
      });
      await r.connect(join.livekit_url, join.token);
      await r.localParticipant.publishTrack(mic.current);
      await r.startAudio().catch(() => undefined);
      setAudioBlocked(!r.canPlaybackAudio);
      setPhase('live');
    } catch (e) {
      release();
      started.current = false;
      setError(errorMessage(e));
      setPhase('error');
    }
  }, [id, release]);

  // Al entrar: con el permiso dado, conecta solo; si falta, primero el aviso.
  useEffect(() => {
    if (!c || started.current || phase !== 'checking') return;
    void micPermission().then((state) => {
      if (!callLive) setPhase('ended');
      else if (state === 'granted') void connect();
      else setPhase(state === 'denied' ? 'denied' : 'ask');
    });
  }, [c, callLive, phase, connect]);

  useEffect(() => release, [release]);

  const toggleMute = async () => {
    if (!mic.current) return;
    await (muted ? mic.current.unmute() : mic.current.mute());
    setMuted(!muted);
  };

  const end = () => {
    hangUp.mutate();
    release();
    setPhase('ended');
  };

  const header = (
    <PageHeader
      title="Llamada de prueba"
      description={`Hablás con ${agentName} desde el navegador, como si fueras quien llama.`}
    />
  );

  if (detail.isError) {
    return (
      <Stack gap="md">
        {header}
        <Alert color="red">{errorMessage(detail.error)}</Alert>
      </Stack>
    );
  }

  const permissionCard = (phase === 'ask' || phase === 'denied' || phase === 'no-mic') && (
    <Card p="xl">
      <Stack align="center" gap="md" maw={520} mx="auto" ta="center">
        <Avatar size={72} radius="xl" color={phase === 'ask' ? 'blue' : 'yellow'} variant="light">
          {phase === 'ask' ? <IconMicrophone size={36} /> : <IconMicrophoneOff size={36} />}
        </Avatar>
        {phase === 'ask' && (
          <>
            <Title order={3}>Necesitamos tu micrófono</Title>
            <Text c="dimmed">
              Para hablar con {agentName}, el navegador te va a pedir permiso para usar el micrófono. Elegí
              “Permitir”.
            </Text>
            <Button size="lg" leftSection={<IconMicrophone size={20} />} onClick={() => void connect()}>
              Permitir micrófono y llamar
            </Button>
          </>
        )}
        {phase === 'denied' && (
          <>
            <Title order={3}>El micrófono está bloqueado</Title>
            <Text c="dimmed">El navegador no deja usarlo en esta página. Para habilitarlo:</Text>
            <List type="ordered" ta="left" spacing={4}>
              {micSteps().map((s) => (
                <List.Item key={s}>{s}</List.Item>
              ))}
              <List.Item>Volvé a intentar.</List.Item>
            </List>
            <Button size="lg" onClick={() => void connect()}>
              Volver a intentar
            </Button>
          </>
        )}
        {phase === 'no-mic' && (
          <>
            <Title order={3}>No encontramos un micrófono</Title>
            <Text c="dimmed">Conectá uno y volvé a intentar.</Text>
            <Button size="lg" onClick={() => void connect()}>
              Volver a intentar
            </Button>
          </>
        )}
      </Stack>
    </Card>
  );

  return (
    <Stack gap="md">
      {header}
      {phase === 'checking' || (phase === 'connecting' && !permissionCard) ? (
        <Card>
          <Center py="xl">
            <Group gap="sm">
              <Loader size="sm" />
              <Text c="dimmed">{phase === 'checking' ? 'Preparando la llamada…' : 'Conectando…'}</Text>
            </Group>
          </Center>
        </Card>
      ) : null}
      {permissionCard}
      {phase === 'error' && (
        <Alert color="red" title="No pudimos conectar la llamada">
          <Stack gap="xs" align="flex-start">
            <Text size="sm">{error}</Text>
            <Button size="xs" variant="white" color="red" onClick={() => void connect()}>
              Volver a intentar
            </Button>
          </Stack>
        </Alert>
      )}
      {phase === 'ended' && (
        <Alert color="gray" title="La llamada terminó">
          <Text size="sm">
            La conversación queda en el{' '}
            <Anchor component={Link} to={`/calls/${id}`} inherit>
              detalle de la llamada
            </Anchor>
            . Para otra prueba, creala de nuevo desde Llamadas o la pestaña Probar del agente.
          </Text>
        </Alert>
      )}
      {(phase === 'live' || phase === 'ended') && (
        <Grid gutter="md">
          <Grid.Col span={{ base: 12, md: 5 }}>
            <Card h="100%">
              <Stack gap="lg">
                {audioBlocked && phase === 'live' && (
                  <Button
                    size="lg"
                    color="yellow"
                    leftSection={<IconVolume size={20} />}
                    onClick={() =>
                      void room.current
                        ?.startAudio()
                        .then(() => setAudioBlocked(!room.current?.canPlaybackAudio))
                    }
                  >
                    Activar el audio para escuchar al agente
                  </Button>
                )}
                <Group justify="space-evenly" align="flex-start" py="md">
                  <Tile name={agentName} label="Agente" speaking={phase === 'live' && agentSpeaks} />
                  <Tile
                    name="Vos"
                    label="Micrófono prendido"
                    speaking={phase === 'live' && userSpeaks}
                    muted={muted}
                  />
                </Group>
                {phase === 'live' && (
                  <Group justify="center" gap="sm">
                    <Button
                      variant="default"
                      leftSection={muted ? <IconMicrophoneOff size={18} /> : <IconMicrophone size={18} />}
                      onClick={() => void toggleMute()}
                    >
                      {muted ? 'Activar micrófono' : 'Silenciar'}
                    </Button>
                    <Button
                      color="red"
                      leftSection={<IconPhoneOff size={18} />}
                      onClick={end}
                      loading={hangUp.isPending}
                    >
                      Cortar
                    </Button>
                  </Group>
                )}
              </Stack>
            </Card>
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 7 }}>
            <Card h="100%">
              <Title order={4} mb="sm">
                Conversación
              </Title>
              {c && c.messages.length ? (
                <ChatView messages={c.messages} userLabel="Vos" maxHeight={520} conversationId={c.id} />
              ) : (
                <EmptyState>El agente atiende en unos segundos.</EmptyState>
              )}
            </Card>
          </Grid.Col>
        </Grid>
      )}
    </Stack>
  );
}
