import { useCallback, useEffect, useRef, useState } from 'react';
import { notifyError } from '@/lib/notify';
import { PcmStreamPlayback } from '@/lib/pcmPlayer';
import { streamTtsPreview } from '@/features/voices/api';

/**
 * Reproduce una frase con una voz (POST /tts/preview en streaming), de a una por vez: dar play en otra voz
 * corta la anterior. `playing` es la voz que suena; `loading`, la que se está generando.
 */
export function useSample() {
  const [playing, setPlaying] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const ctx = useRef<AudioContext | null>(null);
  const live = useRef<{ player?: PcmStreamPlayback; abort: AbortController } | null>(null);

  const stop = useCallback(() => {
    live.current?.abort.abort();
    live.current?.player?.stop();
    live.current = null;
    setPlaying(null);
    setLoading(null);
  }, []);

  useEffect(
    () => () => {
      stop();
      void ctx.current?.close();
    },
    [stop],
  );

  const play = useCallback(
    async (voice: string, text: string) => {
      stop();
      const audio = (ctx.current ??= new AudioContext());
      await audio.resume();
      const abort = new AbortController();
      const current: { player?: PcmStreamPlayback; abort: AbortController } = { abort };
      live.current = current;
      setLoading(voice);
      try {
        const body = await streamTtsPreview({ voice, text }, abort.signal);
        if (live.current !== current) return;
        current.player = new PcmStreamPlayback(audio, body, {
          onStart: () => {
            setLoading(null);
            setPlaying(voice);
          },
          onEnd: () => {
            if (live.current !== current) return;
            live.current = null;
            setPlaying(null);
          },
        });
      } catch (e) {
        if (e instanceof DOMException && e.name === 'AbortError') return;
        stop();
        notifyError(e, 'No se pudo reproducir la voz');
      }
    },
    [stop],
  );

  return { play, stop, playing, loading };
}
