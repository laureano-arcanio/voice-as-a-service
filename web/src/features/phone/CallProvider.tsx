// El teléfono del panel (docs/LLAMADAS_DIRECTAS_PLAN.md, secciones 4, 5 y 8): una llamada a la vez que vive
// en el layout del cliente, para poder abrir otras pantallas sin cortar. Saliente (POST /direct-calls),
// volver a entrar o abrir una creada por API (/join) y atender una entrante del timbre (/answer): las tres
// entran a la room de LiveKit con el micrófono y escuchan los temas `call_status` y `transcript` del worker.
import { useQueryClient } from '@tanstack/react-query';
import { createLocalAudioTrack, type LocalAudioTrack, Room, RoomEvent, Track } from 'livekit-client';
import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '@/api/client';
import { ApiError } from '@/api/errors';
import { unwrap } from '@/api/request';
import { confirmAction } from '@/components/confirm';
import { useMe } from '@/features/auth/api';
import { useFeatureLock, usePlanFeatures } from '@/features/billing/features';
import { isLiveStatus } from '@/lib/labels';
import { notifyError } from '@/lib/notify';
import {
  answerDirectCall,
  declineDirectCall,
  hangupCall,
  joinDirectCall,
  phoneKeys,
  putPresence,
  startDirectCall,
  useRinging,
} from './api';
import {
  type CallPhase,
  type CallProblem,
  type CallResult,
  type CallTarget,
  DirectCallContext,
  type DirectCallValue,
  dtmfCode,
  type JoinOutcome,
  LIVE_PHASES,
  PresenceContext,
  type PresenceValue,
  type TranscriptLine,
} from './context';
import {
  answerProblem,
  connectProblem,
  joinProblem,
  micProblem,
  NO_BROWSER,
  startProblem,
  SUPPORT_REASON,
} from './errors';
import { playRingtone } from './ringtone';
import { storedAvailable, storedCall } from './storage';
import type { CallStatusData, DirectCallOut, Ringing, TranscriptData } from './types';

const PRESENCE_PULSE_MS = 20_000;
const RING_REPEAT_MS = 3_000;
const MAX_LINES = 300;
const BUSY: CallProblem = {
  title: 'Ya estás en una llamada',
  message: 'Cortala antes de empezar otra.',
  code: 'busy',
};

const decoder = new TextDecoder();

export function CallProvider({ children }: { children: ReactNode }) {
  const { data: me } = useMe();
  const qc = useQueryClient();
  const plan = usePlanFeatures();
  const lock = useFeatureLock('direct_calls');
  const enabled = me?.role === 'client' && !!plan.data && !lock.locked;
  const disabledReason = me?.support ? SUPPORT_REASON : null;

  const [phase, setPhaseState] = useState<CallPhase>('idle');
  const [direction, setDirection] = useState<'outbound' | 'inbound' | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [target, setTarget] = useState<CallTarget | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [endedAt, setEndedAt] = useState<number | null>(null);
  const [result, setResult] = useState<CallResult | null>(null);
  const [error, setError] = useState<CallProblem | null>(null);
  const [muted, setMuted] = useState(false);
  const [audioBlocked, setAudioBlocked] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [rejoinId, setRejoinId] = useState<string | null>(null);
  // Timbres rechazados o que ya no se pueden atender: no se vuelven a mostrar.
  const [declined, setDeclined] = useState<string[]>([]);

  const phaseRef = useRef<CallPhase>('idle');
  const convRef = useRef<string | null>(null);
  const targetRef = useRef<CallTarget | null>(null);
  const room = useRef<Room | null>(null);
  const mic = useRef<LocalAudioTrack | null>(null);
  // Cada intento sube el número: si cortan mientras se arma, lo que vuelve de un await viejo se descarta.
  const gen = useRef(0);
  const lineId = useRef(0);

  const setPhase = useCallback((p: CallPhase) => {
    phaseRef.current = p;
    setPhaseState(p);
  }, []);

  const release = useCallback(() => {
    const r = room.current;
    room.current = null;
    if (r) {
      r.removeAllListeners();
      void r.disconnect();
    }
    mic.current?.stop();
    mic.current = null;
    document.querySelectorAll('audio[data-direct-call]').forEach((el) => el.remove());
  }, []);

  const begin = useCallback((dir: 'outbound' | 'inbound', t: CallTarget) => {
    gen.current += 1;
    convRef.current = null;
    targetRef.current = t;
    setConversationId(null);
    setDirection(dir);
    setTarget(t);
    setStartedAt(null);
    setEndedAt(null);
    setResult(null);
    setError(null);
    setMuted(false);
    setAudioBlocked(false);
    setTranscript([]);
    setRejoinId(null);
    return gen.current;
  }, []);

  const finish = useCallback(
    (res: CallResult) => {
      if (!LIVE_PHASES.includes(phaseRef.current)) return;
      gen.current += 1;
      release();
      storedCall.set(null);
      setResult(res);
      setEndedAt(Date.now());
      setMuted(false);
      setAudioBlocked(false);
      setPhase('ended');
      void qc.invalidateQueries({ queryKey: ['calls'] });
    },
    [qc, release, setPhase],
  );

  /** No llegó a empezar: el aviso en la barra. Si la llamada ya existía, se corta (no queda sonando). */
  const fail = useCallback(
    (problem: CallProblem) => {
      gen.current += 1;
      release();
      const id = convRef.current;
      if (id && problem.code === 'connect_failed') void hangupCall(id).catch(() => undefined);
      if (problem.code !== 'busy') storedCall.set(null);
      setError(problem);
      setPhase('error');
    },
    [release, setPhase],
  );

  const openMic = useCallback(async (): Promise<CallProblem | null> => {
    if (!navigator.mediaDevices?.getUserMedia) {
      fail(NO_BROWSER);
      return NO_BROWSER;
    }
    setPhase('mic');
    const g = gen.current;
    try {
      const track = await createLocalAudioTrack({
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      });
      if (g !== gen.current) {
        track.stop();
        return { title: 'Cancelada', message: '', code: 'cancelled' };
      }
      mic.current = track;
      return null;
    } catch (e) {
      const p = micProblem(e);
      fail(p);
      return p;
    }
  }, [fail, setPhase]);

  const applyStatus = useCallback(
    (s: CallStatusData) => {
      const current = phaseRef.current;
      if (!LIVE_PHASES.includes(current)) return;
      if (s.state === 'ended') return finish(s.result ?? 'completed');
      if (s.state === 'active') {
        if (current !== 'active') {
          setStartedAt(Date.now());
          setPhase('active');
        }
        return;
      }
      if (current === 'active') return;
      setPhase(s.state === 'ringing' ? 'ringing' : 'dialing');
    },
    [finish, setPhase],
  );

  const addLine = useCallback((t: TranscriptData) => {
    if (!t.text?.trim()) return;
    const other = targetRef.current?.name || targetRef.current?.phone || 'Contacto';
    const mine = t.role === 'assistant';
    lineId.current += 1;
    const line: TranscriptLine = {
      id: lineId.current,
      mine,
      who: mine ? t.person || 'Vos' : other,
      text: t.text.trim(),
    };
    setTranscript((prev) => [...prev, line].slice(-MAX_LINES));
  }, []);

  /** Entra a la room con el token, publica el micrófono y reproduce lo que llega. */
  const connectRoom = useCallback(
    async (url: string, token: string) => {
      const r = new Room({ adaptiveStream: false, dynacast: false });
      room.current = r;
      r.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind !== Track.Kind.Audio) return;
        const el = track.attach();
        el.dataset.directCall = '';
        el.hidden = true;
        document.body.appendChild(el);
      });
      r.on(RoomEvent.TrackUnsubscribed, (track) => track.detach().forEach((el) => el.remove()));
      r.on(RoomEvent.AudioPlaybackStatusChanged, () => setAudioBlocked(!r.canPlaybackAudio));
      r.on(RoomEvent.DataReceived, (payload: Uint8Array, _p?: unknown, _k?: unknown, topic?: string) => {
        if (topic !== 'call_status' && topic !== 'transcript') return;
        let msg: unknown;
        try {
          msg = JSON.parse(decoder.decode(payload));
        } catch {
          return;
        }
        if (!msg || typeof msg !== 'object') return;
        if (topic === 'call_status') applyStatus(msg as CallStatusData);
        else addLine(msg as TranscriptData);
      });
      // Se cerró la room (cortó el otro, el worker o la red): si estaba En curso, terminó bien.
      r.on(RoomEvent.Disconnected, () => finish(phaseRef.current === 'active' ? 'completed' : 'failed'));
      await r.connect(url, token);
      if (mic.current) await r.localParticipant.publishTrack(mic.current);
      await r.startAudio().catch(() => undefined);
      setAudioBlocked(!r.canPlaybackAudio);
    },
    [addLine, applyStatus, finish],
  );

  /** Ya entró a la llamada: se recuerda en la pestaña por si recarga. */
  const joined = useCallback((id: string) => {
    convRef.current = id;
    setConversationId(id);
    storedCall.set(id);
  }, []);

  const call = useCallback<DirectCallValue['call']>(
    async (t, fromNumberId = null, confirmOptedOut = false) => {
      if (disabledReason) {
        notifyError(new Error(disabledReason), 'No se puede llamar');
        return false;
      }
      if (LIVE_PHASES.includes(phaseRef.current)) {
        notifyError(new Error(BUSY.message), BUSY.title);
        return false;
      }
      const g = begin('outbound', t);
      if (await openMic()) return false;
      setPhase('connecting');
      const request = (confirm: boolean) =>
        startDirectCall({
          contact_id: t.contactId ?? null,
          phone: t.contactId ? null : (t.phone ?? null),
          from_number_id: fromNumberId ?? null,
          confirm_opted_out: confirm,
        });
      let started: DirectCallOut;
      try {
        started = await request(confirmOptedOut);
      } catch (e) {
        if (g !== gen.current) return false;
        if (!(e instanceof ApiError && e.code === 'opted_out' && !confirmOptedOut)) {
          fail(startProblem(e));
          return false;
        }
        const ok = await confirmAction({
          title: 'Contacto dado de baja',
          message: 'Este contacto pidió no recibir llamadas. ¿Llamar igual?',
          confirmLabel: 'Llamar igual',
        });
        if (g !== gen.current) return false;
        if (!ok) {
          gen.current += 1;
          release();
          setPhase('idle');
          return false;
        }
        try {
          started = await request(true);
        } catch (e2) {
          if (g === gen.current) fail(startProblem(e2));
          return false;
        }
      }
      if (g !== gen.current) {
        // Cortó mientras se pedía: la llamada ya existe, se corta.
        void hangupCall(started.conversation_id).catch(() => undefined);
        return false;
      }
      joined(started.conversation_id);
      if (!started.token) {
        fail({ title: 'No pudimos entrar a la llamada', message: 'Probá de nuevo.', code: 'connect_failed' });
        return false;
      }
      try {
        await connectRoom(started.livekit_url, started.token);
      } catch (e) {
        if (g === gen.current) fail(connectProblem(e));
        return false;
      }
      if (g !== gen.current) return false;
      if (phaseRef.current === 'connecting') setPhase('dialing');
      return true;
    },
    [begin, connectRoom, disabledReason, fail, joined, openMic, release, setPhase],
  );

  const join = useCallback<DirectCallValue['join']>(
    async (id): Promise<JoinOutcome> => {
      if (disabledReason) {
        const problem = { title: 'No se puede entrar', message: disabledReason, code: 'support_read_only' };
        return { ok: false, code: problem.code, problem };
      }
      if (LIVE_PHASES.includes(phaseRef.current)) {
        if (convRef.current === id) return { ok: true };
        return { ok: false, code: BUSY.code, problem: BUSY };
      }
      const g = begin('outbound', {});
      // Para la barra: el teléfono, la línea y si ya está En curso. Sin el detalle, igual se entra.
      const detail = await unwrap(
        api.GET('/api/v1/calls/{conversation_id}', { params: { path: { conversation_id: id } } }),
      ).catch(() => null);
      if (g !== gen.current) return { ok: false, code: 'cancelled' };
      const info = detail?.call;
      const t: CallTarget = { phone: info?.phone ?? null, fromLabel: info?.client_number ?? null };
      targetRef.current = t;
      setTarget(t);
      setDirection(info && info.mode !== 'directa' ? 'inbound' : 'outbound');
      const micFailed = await openMic();
      if (micFailed) return { ok: false, code: micFailed.code, problem: micFailed };
      setPhase('connecting');
      let creds;
      try {
        creds = await joinDirectCall(id);
      } catch (e) {
        const problem = joinProblem(e);
        if (g === gen.current) fail(problem);
        return { ok: false, code: problem.code, problem };
      }
      if (g !== gen.current) return { ok: false, code: 'cancelled' };
      joined(id);
      try {
        await connectRoom(creds.livekit_url, creds.token);
      } catch (e) {
        const problem = connectProblem(e);
        if (g === gen.current) fail(problem);
        return { ok: false, code: problem.code, problem };
      }
      if (g !== gen.current) return { ok: false, code: 'cancelled' };
      if (phaseRef.current === 'connecting') {
        if (info?.status === 'en_curso') {
          const since = info.started_at ? Date.parse(info.started_at) : NaN;
          setStartedAt(Number.isNaN(since) ? Date.now() : since);
          setPhase('active');
        } else setPhase('dialing');
      }
      return { ok: true };
    },
    [begin, connectRoom, disabledReason, fail, joined, openMic, setPhase],
  );

  const answer = useCallback<DirectCallValue['answer']>(
    async (ring) => {
      if (disabledReason) {
        notifyError(new Error(disabledReason), 'No se puede atender');
        return false;
      }
      if (LIVE_PHASES.includes(phaseRef.current)) {
        notifyError(new Error(BUSY.message), BUSY.title);
        return false;
      }
      const g = begin('inbound', {
        contactId: ring.contact_id ?? null,
        phone: ring.phone,
        name: ring.contact_name ?? null,
        fromLabel: ring.number_label || ring.number_e164,
      });
      if (await openMic()) return false;
      setPhase('connecting');
      let creds;
      try {
        creds = await answerDirectCall(ring.conversation_id);
      } catch (e) {
        // Ya no le suena (la atendió otro o se cortó): ese timbre no se muestra más.
        setDeclined((prev) => [...prev, ring.conversation_id]);
        if (g === gen.current) fail(answerProblem(e));
        void qc.invalidateQueries({ queryKey: phoneKeys.ringing });
        return false;
      }
      if (g !== gen.current) {
        // Cortó mientras se atendía: la llamada ya es suya, se corta (no queda sin nadie).
        void hangupCall(ring.conversation_id).catch(() => undefined);
        return false;
      }
      joined(ring.conversation_id);
      try {
        await connectRoom(creds.livekit_url, creds.token);
      } catch (e) {
        if (g === gen.current) fail(connectProblem(e));
        return false;
      }
      if (g !== gen.current) return false;
      // La entrante ya está atendida: entra En curso.
      setStartedAt(Date.now());
      setPhase('active');
      void qc.invalidateQueries({ queryKey: phoneKeys.ringing });
      return true;
    },
    [begin, connectRoom, disabledReason, fail, joined, openMic, qc, setPhase],
  );

  const hangup = useCallback(() => {
    const id = convRef.current;
    if (id) void hangupCall(id).catch(() => undefined);
    finish(phaseRef.current === 'active' ? 'completed' : 'hangup');
  }, [finish]);

  const toggleMute = useCallback(() => {
    const track = mic.current;
    if (!track) return;
    const next = !track.isMuted;
    void (next ? track.mute() : track.unmute()).then(() => setMuted(next));
  }, []);

  const dtmf = useCallback((digit: string) => {
    const code = dtmfCode(digit);
    const r = room.current;
    if (code === null || !r || phaseRef.current !== 'active') return;
    void r.localParticipant.publishDtmf(code, digit).catch((e) => notifyError(e, 'No se pudo marcar'));
  }, []);

  const startAudio = useCallback(() => {
    const r = room.current;
    if (!r) return;
    void r
      .startAudio()
      .then(() => setAudioBlocked(!r.canPlaybackAudio))
      .catch(() => undefined);
  }, []);

  const dismiss = useCallback(() => {
    if (LIVE_PHASES.includes(phaseRef.current)) return;
    convRef.current = null;
    setConversationId(null);
    setTarget(null);
    setDirection(null);
    setError(null);
    setResult(null);
    setTranscript([]);
    setPhase('idle');
  }, [setPhase]);

  const dismissRejoin = useCallback(() => {
    storedCall.set(null);
    setRejoinId(null);
  }, []);

  // Recargó con una llamada en curso: si sigue viva, "Volver a entrar".
  const isClient = me?.role === 'client';
  useEffect(() => {
    const id = storedCall.get();
    if (!id || !isClient) return;
    let cancelled = false;
    unwrap(api.GET('/api/v1/calls/{conversation_id}', { params: { path: { conversation_id: id } } }))
      .then((d) => {
        if (cancelled) return;
        if (isLiveStatus(d.call?.status) && !LIVE_PHASES.includes(phaseRef.current)) setRejoinId(id);
        else if (!isLiveStatus(d.call?.status)) storedCall.set(null);
      })
      .catch(() => storedCall.set(null));
    return () => {
      cancelled = true;
    };
  }, [isClient]);

  // Aviso del navegador al cerrar o recargar la pestaña con una llamada.
  const live = LIVE_PHASES.includes(phase);
  useEffect(() => {
    if (!live) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [live]);

  useEffect(() => () => release(), [release]);

  // ---- Presencia y timbre ----

  const [availableWanted, setAvailableWanted] = useState(() => storedAvailable.get());
  const presenceOn = availableWanted && enabled && !disabledReason;

  useEffect(() => {
    if (!presenceOn) return;
    const pulse = () =>
      putPresence(true).catch((e) => {
        setAvailableWanted(false);
        storedAvailable.set(false);
        notifyError(e, 'No pudimos dejarte Disponible');
      });
    void pulse();
    const t = window.setInterval(() => void pulse(), PRESENCE_PULSE_MS);
    // Al apagarlo, al perder el plan o al salir del panel (cerrar sesión): deja de estar Disponible ya,
    // sin esperar los 60 s sin pulso.
    return () => {
      window.clearInterval(t);
      void putPresence(false).catch(() => undefined);
    };
  }, [presenceOn]);

  const setAvailable = useCallback((on: boolean) => {
    setAvailableWanted(on);
    storedAvailable.set(on);
  }, []);

  const ringing = useRinging(presenceOn && !live);
  const rings = useMemo(
    () =>
      presenceOn && !live ? (ringing.data ?? []).filter((r) => !declined.includes(r.conversation_id)) : [],
    [declined, live, presenceOn, ringing.data],
  );
  const ringKey = rings.map((r) => r.conversation_id).join(',');
  useEffect(() => {
    if (!ringKey) return;
    playRingtone();
    const t = window.setInterval(playRingtone, RING_REPEAT_MS);
    return () => window.clearInterval(t);
  }, [ringKey]);

  const decline = useCallback((ring: Ringing) => {
    setDeclined((prev) => [...prev, ring.conversation_id]);
    void declineDirectCall(ring.conversation_id).catch((e) => notifyError(e, 'No se pudo rechazar'));
  }, []);

  const callValue = useMemo<DirectCallValue>(
    () => ({
      phase,
      direction,
      conversationId,
      target,
      enabled,
      startedAt,
      endedAt,
      result,
      error,
      muted,
      audioBlocked,
      transcript,
      busy: live,
      rejoinId,
      disabledReason,
      call,
      join,
      answer,
      hangup,
      toggleMute,
      dtmf,
      startAudio,
      dismiss,
      dismissRejoin,
    }),
    [
      phase,
      direction,
      conversationId,
      target,
      enabled,
      startedAt,
      endedAt,
      result,
      error,
      muted,
      audioBlocked,
      transcript,
      live,
      rejoinId,
      disabledReason,
      call,
      join,
      answer,
      hangup,
      toggleMute,
      dtmf,
      startAudio,
      dismiss,
      dismissRejoin,
    ],
  );

  const presenceValue = useMemo<PresenceValue>(
    () => ({ available: presenceOn, setAvailable, rings, decline, disabledReason }),
    [decline, disabledReason, presenceOn, rings, setAvailable],
  );

  return (
    <DirectCallContext.Provider value={callValue}>
      <PresenceContext.Provider value={presenceValue}>{children}</PresenceContext.Provider>
    </DirectCallContext.Provider>
  );
}
