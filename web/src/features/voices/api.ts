import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';
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

/** Sintetiza texto con una voz: WAV como Blob (directo al TTS, sin llamada). */
export function useTtsPreview() {
  return useMutation({
    mutationFn: async (body: { voice: string; text: string }): Promise<Blob> => {
      const { data, error, response } = await api.POST('/api/v1/tts/preview', { body, parseAs: 'blob' });
      if (!response.ok) throw toApiError(error, response.status);
      return data as Blob;
    },
  });
}
