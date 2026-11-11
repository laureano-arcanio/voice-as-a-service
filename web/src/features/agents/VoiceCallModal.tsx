import { Alert, Avatar, Box, Button, Group, Modal, ScrollArea, Stack, Text } from '@mantine/core';
import { IconMicrophone, IconPhoneOff } from '@tabler/icons-react';
import { useQueryClient } from '@tanstack/react-query';
import type { LocalAudioTrack, Participant, Room, TextStreamReader } from 'livekit-client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import { errorMessage } from '@/api/errors';
import type { Agent } from '@/api/types';
import { voiceName } from '@/features/voices/names';
import { HandoffProgress } from '@/components/HandoffProgress';
import { formatClock } from '@/lib/format';
import { HANDOFF_TOPIC, parseHandoffStatus, type HandoffSnapshot } from '@/lib/handoffProgress';
import { hangUpCall, startBrowserCall } from '@/features/calls/api';
import { portrait } from '@/features/onboarding/catalog';

type Phase = 'connecting' | 'live' | 'ended' | 'failed';
interface Line {
  id: string;
  user: boolean;
  text: string;
}

const livekit = () => import('livekit-client');

/** Error del micrófono, no del servidor: sin `mediaDevices` (HTTP fuera de localhost), permiso negado o sin dispositivo. */
class MicError extends Error {}

async function openMic(createLocalAudioTrack: (o: object) => Promise<LocalAudioTrack>): Promise<LocalAudioTrack> {
  if (!navigator.mediaDevices?.getUserMedia)
    throw new MicError('El navegador no permite usar el micrófono en esta dirección: hace falta HTTPS o localhost.');
  try {
    return await createLocalAudioTrack({ echoCancellation: true, noiseSuppression: true });
  } catch (e) {
    const name = e instanceof DOMException ? e.name : '';
    if (name === 'NotAllowedError')
      throw new MicError('El micrófono está bloqueado. Permitilo desde el candado de la barra de direcciones y probá de nuevo.');
    if (name === 'NotFoundError') throw new MicError('No encontramos un micrófono. Conectá uno y probá de nuevo.');
    throw new MicError('No se pudo usar el micrófono. Revisá el permiso del navegador y probá de nuevo.');
  }
}

interface Props {
  agent: Agent;
  opened: boolean;
  onClose: () => void;
  /** Número de quien llama, simulado (E.164): llega a las herramientas como {{call.phone}}; no se marca. */
  callerPhone?: string;
  /** Corre el pre-call y el post-call del agente (las pruebas del panel; Inicio no). */
  workflows?: boolean;
}

/**
 * Hablar con el agente desde el navegador, sin salir del panel: llamada de prueba (POST /calls sin teléfono,
 * modo prueba) con el micrófono y los subtítulos en vivo. Al terminar, link a la conversación.
 */
export function VoiceCallModal({ agent, opened, onClose, callerPhone, workflows }: Props) {
  const qc = useQueryClient();
  const [phase, setPhase] = useState<Phase>('connecting');
  const [error, setError] = useState<string | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [speaking, setSpeaking] = useState<'agent' | 'user' | null>(null);
  const [seconds, setSeconds] = useState(0);
  const [conversationId, setConversationId] = useState<string | null>(null);
  // Derivación a una persona: último snapshot del worker y cuándo llegó (de ahí corren los contadores).
  const [handoff, setHandoff] = useState<{ snapshot: HandoffSnapshot; at: number } | null>(null);
  const room = useRef<Room | null>(null);
  // Cada intento tiene su número: uno viejo (cerraron el modal, o React montó dos veces) no sigue.
  const gen = useRef(0);
  const viewport = useRef<HTMLDivElement>(null);
  const name = voiceName(agent.voice ?? 'sofia');
  const image = portrait(agent.voice);

  const showLine = useCallback((id: string, user: boolean, text: string) => {
    setLines((prev) => {
      const i = prev.findIndex((l) => l.id === id);
      if (i < 0) return [...prev, { id, user, text }];
      const next = prev.slice();
      next[i] = { id, user, text };
      return next;
    });
  }, []);

  const connect = useCallback(async () => {
    const g = ++gen.current;
    try {
      const { Room, RoomEvent, Track, createLocalAudioTrack } = await livekit();
      const mic = await openMic(createLocalAudioTrack);
      if (g !== gen.current) return mic.stop();
      const call = await startBrowserCall(agent.id, { callerPhone, workflows });
      if (g !== gen.current) {
        mic.stop();
        return void hangUpCall(call.conversationId).catch(() => undefined);
      }
      setConversationId(call.conversationId);
      const r = new Room({ adaptiveStream: false, dynacast: false });
      room.current = r;
      r.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind !== Track.Kind.Audio) return;
        const el = track.attach();
        el.hidden = true;
        document.body.appendChild(el);
        setPhase('live');
      });
      r.on(RoomEvent.TrackUnsubscribed, (track) => track.detach().forEach((el) => el.remove()));
      r.on(RoomEvent.ActiveSpeakersChanged, (speakers: Participant[]) => {
        const local = r.localParticipant.identity;
        setSpeaking(
          speakers.some((p) => p.identity !== local) ? 'agent' : speakers.some((p) => p.identity === local) ? 'user' : null,
        );
      });
      r.on(RoomEvent.Disconnected, () => {
        mic.stop();
        room.current = null;
        setSpeaking(null);
        setHandoff(null);
        setPhase((p) => (p === 'failed' ? p : 'ended'));
        void qc.invalidateQueries({ queryKey: ['calls'] });
        void qc.invalidateQueries({ queryKey: ['onboarding'] });
      });
      r.on(RoomEvent.DataReceived, (payload: Uint8Array, _p?: unknown, _k?: unknown, topic?: string) => {
        if (topic !== HANDOFF_TOPIC) return;
        const snapshot = parseHandoffStatus(payload);
        if (snapshot) setHandoff({ snapshot, at: Date.now() });
      });
      r.registerTextStreamHandler('lk.transcription', (reader: TextStreamReader, participant) => {
        const attributes = reader.info.attributes ?? {};
        const trackId = attributes['lk.transcribed_track_id'];
        const local = r.localParticipant;
        const user =
          participant.identity === local.identity || (trackId !== undefined && local.trackPublications.has(trackId));
        const id = attributes['lk.segment_id'] ?? reader.info.id;
        void (async () => {
          let text = '';
          for await (const chunk of reader) {
            text += chunk;
            showLine(id, user, text);
          }
        })();
      });
      await r.connect(call.livekit_url, call.token);
      await r.localParticipant.publishTrack(mic);
      await r.startAudio().catch(() => undefined);
    } catch (e) {
      if (g !== gen.current) return;
      setError(errorMessage(e));
      setPhase('failed');
      void room.current?.disconnect();
    }
  }, [agent.id, callerPhone, workflows, qc, showLine]);

  const retry = () => {
    setPhase('connecting');
    setError(null);
    setLines([]);
    setSeconds(0);
    setConversationId(null);
    setHandoff(null);
    void connect();
  };

  const hangUp = useCallback(() => {
    if (conversationId) void hangUpCall(conversationId).catch(() => undefined);
    void room.current?.disconnect();
  }, [conversationId]);

  useEffect(() => {
    if (!opened) return;
    // En un timer: con StrictMode el efecto corre dos veces y el primero se cancela antes de llamar.
    const t = window.setTimeout(() => void connect());
    return () => {
      window.clearTimeout(t);
      gen.current += 1;
      void room.current?.disconnect();
    };
  }, [opened, connect]);

  useEffect(() => {
    if (phase !== 'live') return;
    const t = window.setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => window.clearInterval(t);
  }, [phase]);

  useEffect(() => {
    viewport.current?.scrollTo({ top: viewport.current.scrollHeight, behavior: 'smooth' });
  }, [lines]);

  const close = () => {
    hangUp();
    onClose();
  };

  const status =
    phase === 'connecting'
      ? `Llamando a ${name}…`
      : phase === 'live'
        ? speaking === 'agent'
          ? `${name} habla…`
          : speaking === 'user'
            ? 'Te escucha…'
            : formatClock(seconds)
        : phase === 'ended'
          ? `Llamada terminada · ${formatClock(seconds)}`
          : 'No se pudo iniciar la llamada';

  return (
    <Modal opened={opened} onClose={close} title={`Hablar con ${name}`} size="md" centered>
      <Stack align="center" gap="md">
        <Box className="onb-call-avatar" data-speaking={speaking === 'agent' || undefined} data-phase={phase}>
          <Avatar src={image} size={128} radius={999} color="blue">
            {name.charAt(0)}
          </Avatar>
        </Box>
        <Stack gap={2} align="center">
          <Text fw={700} size="lg">
            {agent.name}
          </Text>
          <Text size="sm" c={phase === 'failed' ? 'red' : 'dimmed'} className="mono" aria-live="polite">
            {status}
          </Text>
        </Stack>
        {error && (
          <Alert color="red" w="100%">
            {error}
          </Alert>
        )}
        {phase === 'live' && lines.length === 0 && (
          <Group gap={6} c="dimmed">
            <IconMicrophone size={16} />
            <Text size="sm">Hablale como si fueras un cliente.</Text>
          </Group>
        )}
        {handoff && phase === 'live' && <HandoffProgress snapshot={handoff.snapshot} receivedAt={handoff.at} />}
        {lines.length > 0 && (
          <ScrollArea h={200} w="100%" viewportRef={viewport} className="onb-captions">
            <Stack gap={6} p="xs">
              {lines.map((l) => (
                <Box key={l.id} className="onb-bubble" data-user={l.user || undefined}>
                  <Text size="sm">{l.text}</Text>
                </Box>
              ))}
            </Stack>
          </ScrollArea>
        )}
        {phase === 'connecting' || phase === 'live' ? (
          <Button color="red" leftSection={<IconPhoneOff size={18} />} onClick={hangUp}>
            Cortar
          </Button>
        ) : (
          <Group>
            <Button variant="default" onClick={retry}>
              Llamar de nuevo
            </Button>
            {conversationId && phase === 'ended' && (
              <Button component={Link} to={`/calls/${conversationId}`} onClick={onClose}>
                Ver la conversación
              </Button>
            )}
          </Group>
        )}
      </Stack>
    </Modal>
  );
}
