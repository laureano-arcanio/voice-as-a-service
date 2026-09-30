import { ActionIcon, Group, Loader, Progress, Stack, Text, Textarea } from '@mantine/core';
import { IconPlayerPauseFilled, IconPlayerPlayFilled } from '@tabler/icons-react';
import { useEffect, useRef, useState } from 'react';
import { errorMessage } from '@/api/errors';
import { formatClock, formatNumber } from '@/lib/format';
import { useTtsPreview } from './api';

export const DEFAULT_PREVIEW_TEXT =
  'Hola, ¿qué tal? Te hablo de Voz Directa. Te llamo porque dejaste tus datos en nuestra web pidiendo una demo del asistente telefónico. Si te parece, coordinamos una videollamada de veinte minutos esta semana para mostrarte cómo funciona con tus clientes. Atiende las llamadas las veinticuatro horas, agenda turnos y responde las consultas más frecuentes, con una voz natural como esta. ¿Qué día y horario te queda cómodo?';

const MAX_CHARS = 600;

/**
 * Prueba de voz: sintetiza el texto con la voz (POST /tts/preview) y lo reproduce.
 * Play/pausa sobre el mismo audio; si cambian la voz o el texto, se vuelve a generar.
 */
export function VoicePreview({
  voice,
  compact = false,
}: {
  voice: string | null | undefined;
  compact?: boolean;
}) {
  const [text, setText] = useState(DEFAULT_PREVIEW_TEXT);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState({ current: 0, duration: 0 });
  const [msg, setMsg] = useState<{ text: string; bad: boolean } | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const cache = useRef<{ key: string; url: string } | null>(null);
  const tts = useTtsPreview();

  // Otra voz: se corta lo que suena (el audio se regenera al volver a dar play).
  useEffect(() => {
    audioRef.current?.pause();
  }, [voice]);

  // Libera el audio generado al desmontar.
  useEffect(
    () => () => {
      if (cache.current) URL.revokeObjectURL(cache.current.url);
    },
    [],
  );

  const toggle = async () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (!audio.paused) {
      audio.pause();
      return;
    }
    const t = text.trim();
    if (!voice) return setMsg({ text: 'Elegí una voz.', bad: true });
    if (!t) return setMsg({ text: 'Escribí un texto.', bad: true });
    const key = `${voice}\n${t}`;
    if (cache.current?.key !== key) {
      setMsg({ text: `Generando con ${voice}…`, bad: false });
      const t0 = performance.now();
      try {
        const blob = await tts.mutateAsync({ voice, text: t });
        if (cache.current) URL.revokeObjectURL(cache.current.url);
        cache.current = { key, url: URL.createObjectURL(blob) };
        audio.src = cache.current.url;
        setMsg({
          text: `${voice} · ${t.length} caracteres · generado en ${formatNumber((performance.now() - t0) / 1000)} s`,
          bad: false,
        });
      } catch (e) {
        setMsg({ text: `No se pudo generar el audio: ${errorMessage(e)}`, bad: true });
        return;
      }
    }
    try {
      await audio.play();
    } catch (e) {
      setMsg({ text: errorMessage(e), bad: true });
    }
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
          radius="xl"
          variant="filled"
          onClick={() => void toggle()}
          disabled={tts.isPending}
          aria-label={playing ? 'Pausar' : 'Reproducir'}
          title="Escuchar la voz elegida"
        >
          {tts.isPending ? (
            <Loader size={14} color="var(--atentina-on-primary)" />
          ) : playing ? (
            <IconPlayerPauseFilled size={16} />
          ) : (
            <IconPlayerPlayFilled size={16} />
          )}
        </ActionIcon>
        <Progress value={pct} style={{ flex: 1 }} size="sm" aria-label="Progreso" transitionDuration={100} />
        <Text size="xs" c="dimmed" className="mono" style={{ whiteSpace: 'nowrap' }}>
          {formatClock(time.current)} / {formatClock(time.duration)}
        </Text>
      </Group>
      <Text size="xs" c={msg?.bad ? 'red' : 'dimmed'}>
        {msg?.text ??
          `Escuchá ${voice ? `la voz ${voice}` : 'la voz elegida'} con este texto (editalo si querés). Va directo al TTS, sin llamada.`}
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
