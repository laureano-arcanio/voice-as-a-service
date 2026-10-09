import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { toApiError } from '@/api/errors';
import { unwrap } from '@/api/request';

export interface VoiceFilters {
  genero: string;
  wer_max: number | '';
  car_min: number | '';
  car_max: number | '';
}

export const EMPTY_VOICE_FILTERS: VoiceFilters = { genero: '', wer_max: '', car_min: '', car_max: '' };

export function useVoices(f: VoiceFilters = EMPTY_VOICE_FILTERS) {
  const query = {
    genero: f.genero || undefined,
    wer_max: f.wer_max === '' ? undefined : f.wer_max,
    car_min: f.car_min === '' ? undefined : f.car_min,
    car_max: f.car_max === '' ? undefined : f.car_max,
  };
  return useQuery({
    queryKey: ['voices', query],
    queryFn: () => unwrap(api.GET('/api/v1/voices', { params: { query } })),
    staleTime: 5 * 60_000,
    placeholderData: keepPreviousData,
  });
}

/**
 * Sintetiza texto con una voz y devuelve el audio PCM crudo (16 bits, mono, 24 kHz) como stream: llega a medida que
 * el TTS lo genera y se reproduce con PcmStreamPlayback (directo al TTS, sin llamada).
 */
export async function streamTtsPreview(
  body: { voice: string; text: string },
  signal?: AbortSignal,
): Promise<ReadableStream<Uint8Array>> {
  const { data, error, response } = await api.POST('/api/v1/tts/preview', {
    body: { ...body, format: 'pcm' },
    parseAs: 'stream',
    signal,
  });
  if (!response.ok) throw toApiError(error, response.status);
  if (!data) throw new Error('El servidor no devolvió audio.');
  return data as ReadableStream<Uint8Array>;
}
