import { ActionIcon, Group, Loader, Progress, Stack, Text, Textarea } from '@mantine/core';
import { IconPlayerPause, IconPlayerPlay } from '@tabler/icons-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage } from '@/api/errors';
import { formatClock, formatNumber } from '@/lib/format';
import { PcmStreamPlayback, wavFromPcm } from '@/lib/pcmPlayer';
import { streamTtsPreview } from './api';
import { voiceName } from './names';

export const DEFAULT_PREVIEW_TEXT =
  'Hola, ¿qué tal? Te hablo de Voz Directa. Te llamo porque dejaste tus datos en nuestra web pidiendo una demo del asistente telefónico. Si te parece, coordinamos una videollamada de veinte minutos esta semana para mostrarte cómo funciona con tus clientes. Atiende las llamadas las veinticuatro horas, agenda turnos y responde las consultas más frecuentes, con una voz natural como esta. ¿Qué día y horario te queda cómodo?';

const MAX_CHARS = 600;

/**
 * Prueba de voz: sintetiza el texto con la voz (POST /tts/preview, PCM en streaming) y lo reproduce mientras se genera:
 * suena a los ~0,5 s en vez de esperar la sintesis entera. Al terminar de generarse queda guardado como WAV: volver a
 * dar play lo reproduce al instante, con pausa. Si cambian la voz o el texto, se vuelve a generar.
 */
export function VoicePreview({
  voice,
  compact = false,
  initialText,
}: {
  voice: string | null | undefined;
  compact?: boolean;
  /** Texto de partida (ej. la apertura del agente); sin el, uno de ejemplo. */
  initialText?: string;
}) {
  const [text, setText] = useState(() => (initialText?.trim() || DEFAULT_PREVIEW_TEXT).slice(0, MAX_CHARS));
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [time, setTime] = useState({ current: 0, duration: 0 });
  const [msg, setMsg] = useState<{ text: string; bad: boolean } | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const cache = useRef<{ key: string; url: string } | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const live = useRef<{ player: PcmStreamPlayback; abort: AbortController; tick: number } | null>(null);

  /** Corta la reproduccion en streaming (si hay) y su descarga. */
  const stopLive = useCallback(() => {
    const l = live.current;
    live.current = null;
    if (!l) return;
    window.clearInterval(l.tick);
    l.abort.abort();
    l.player.stop();
    setPlaying(false);
    setLoading(false);
    setTime((t) => ({ ...t, current: 0 }));
  }, []);

  // Otra voz: se corta lo que suena (el audio se regenera al volver a dar play).
  useEffect(() => {
    audioRef.current?.pause();
    stopLive();
  }, [voice, stopLive]);

  // Libera el audio generado y el contexto de audio al desmontar.
  useEffect(
    () => () => {
      stopLive();
      if (cache.current) URL.revokeObjectURL(cache.current.url);
      void ctxRef.current?.close();
    },
    [stopLive],
  );

  const stream = async (v: string, t: string, key: string) => {
    const ctx = (ctxRef.current ??= new AudioContext());
    await ctx.resume();
    const abort = new AbortController();
    const t0 = performance.now();
    setLoading(true);
    setMsg({ text: `Generando con ${voiceName(v)}…`, bad: false });
    let startedAfter = 0;
    try {
      const body = await streamTtsPreview({ voice: v, text: t }, abort.signal);
      const player = new PcmStreamPlayback(ctx, body, {
        onStart: () => {
          startedAfter = (performance.now() - t0) / 1000;
          setLoading(false);
          setPlaying(true);
          setMsg({ text: `${voiceName(v)} · ${t.length} caracteres · generando…`, bad: false });
        },
        onEnd: () => {
          if (live.current?.player !== player) return;
          window.clearInterval(live.current.tick);
          live.current = null;
          setPlaying(false);
          setTime((x) => ({ ...x, current: 0 }));
        },
      });
      const tick = window.setInterval(
        () => setTime({ current: player.elapsed(), duration: player.isFinal() ? player.total() : 0 }),
        100,
      );
      live.current = { player, abort, tick };
      const pcm = await player.generated;
      if (!pcm?.length) {
        if (pcm) setMsg({ text: 'El servidor no devolvió audio.', bad: true });
        return;
      }
      // Ya se genero todo: queda guardado para volver a escucharlo sin regenerar.
      if (cache.current) URL.revokeObjectURL(cache.current.url);
      cache.current = { key, url: URL.createObjectURL(new Blob([wavFromPcm(pcm)], { type: 'audio/wav' })) };
      if (audioRef.current) audioRef.current.src = cache.current.url;
      setTime((x) => ({ ...x, duration: player.total() }));
      setMsg({
        text: `${voiceName(v)} · ${t.length} caracteres · empezó a sonar a los ${formatNumber(startedAfter)} s · generado en ${formatNumber((performance.now() - t0) / 1000)} s`,
        bad: false,
      });
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') return;
      stopLive();
      setMsg({ text: `No se pudo generar el audio: ${errorMessage(e)}`, bad: true });
    } finally {
      setLoading(false);
    }
  };

  const toggle = async () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (!audio.paused) {
      audio.pause();
      return;
    }
    const ctx = ctxRef.current;
    if (live.current && ctx) {
      // Pausa y continua sobre el audio que se esta generando.
      if (ctx.state === 'running') {
        await ctx.suspend();
        setPlaying(false);
      } else {
        await ctx.resume();
        setPlaying(true);
      }
      return;
    }
    const t = text.trim();
    if (!voice) return setMsg({ text: 'Elegí una voz.', bad: true });
    if (!t) return setMsg({ text: 'Escribí un texto.', bad: true });
    const key = `${voice}\n${t}`;
    if (cache.current?.key === key) {
      try {
        await audio.play();
      } catch (e) {
        setMsg({ text: errorMessage(e), bad: true });
      }
      return;
    }
    await stream(voice, t, key);
  };

  const pct = time.duration > 0 ? (time.current / time.duration) * 100 : 0;
  const onTime = (a: HTMLAudioElement) =>
    setTime({ current: a.currentTime, duration: Number.isFinite(a.duration) ? a.duration : 0 });

  return (
    <Stack gap={6}>
      <Textarea
        label="Prueba de voz"
        value={text}
        onChange={(e) => setText(e.currentTarget.value.slice(0, MAX_CHARS))}
        maxLength={MAX_CHARS}
        autosize
        minRows={compact ? 2 : 3}
        maxRows={8}
        spellCheck={false}
        description={`${text.length}/${MAX_CHARS} caracteres`}
      />
      <Group gap="sm" wrap="nowrap">
        <ActionIcon
          size="lg"
          radius={999}
          variant="filled"
          onClick={() => void toggle()}
          disabled={loading}
          aria-label={playing ? 'Pausar' : 'Reproducir'}
          title="Escuchar la voz elegida"
        >
          {loading ? (
            <Loader size={14} color="white" />
          ) : playing ? (
            <IconPlayerPause size={18} />
          ) : (
            <IconPlayerPlay size={18} />
          )}
        </ActionIcon>
        <Progress value={pct} style={{ flex: 1 }} size="sm" aria-label="Progreso" transitionDuration={100} />
        <Text size="xs" c="dimmed" className="mono" style={{ whiteSpace: 'nowrap' }}>
          {formatClock(time.current)} / {time.duration > 0 ? formatClock(time.duration) : '…'}
        </Text>
      </Group>
      <Text size="xs" c={msg?.bad ? 'red' : 'dimmed'}>
        {msg?.text ??
          `Escuchá ${voice ? voiceName(voice) : 'la voz elegida'} con este texto (editalo si querés). Va directo al TTS, sin llamada.`}
      </Text>
      <audio
        ref={audioRef}
        hidden
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onTimeUpdate={(e) => onTime(e.currentTarget)}
        onLoadedMetadata={(e) => onTime(e.currentTarget)}
        onEnded={(e) => {
          e.currentTarget.currentTime = 0;
          onTime(e.currentTarget);
        }}
      />
    </Stack>
  );
}
