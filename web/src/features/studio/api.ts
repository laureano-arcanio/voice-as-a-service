import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { unwrap } from '@/api/request';
import type { components } from '@/api/schema';

export type StudioItem = components['schemas']['StudioItemOut'];
export type StudioKind = StudioItem['kind'];

export const AUDIO_FORMATS = [
  { value: 'mp3', label: 'MP3' },
  { value: 'wav', label: 'WAV' },
  { value: 'ogg', label: 'OGG (Opus)' },
  { value: 'flac', label: 'FLAC' },
] as const;
export type AudioFormat = (typeof AUDIO_FORMATS)[number]['value'];

const POLL_MS = 2000;
const itemsKey = (kind: StudioKind) => ['studio', 'items', kind] as const;

export const isActive = (i: StudioItem) => i.status === 'queued' || i.status === 'processing';

/** El historial; mientras haya algo en proceso se actualiza solo. */
export function useStudioItems(kind: StudioKind) {
  return useQuery({
    queryKey: itemsKey(kind),
    queryFn: () => unwrap(api.GET('/api/v1/studio/items', { params: { query: { kind, limit: 100 } } })),
    refetchInterval: (q) => (q.state.data?.items.some(isActive) ? POLL_MS : false),
  });
}

/** Un elemento con su texto completo. */
export function useStudioItem(id: string | null) {
  return useQuery({
    queryKey: ['studio', 'item', id],
    queryFn: () => unwrap(api.GET('/api/v1/studio/items/{item_id}', { params: { path: { item_id: id! } } })),
    enabled: !!id,
  });
}

function useRefresh() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: ['studio'] });
    void qc.invalidateQueries({ queryKey: ['clients'] });
  };
}

export function useCreateSpeech() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (body: { text: string; voice: string }) => unwrap(api.POST('/api/v1/studio/speech', { body })),
    onSuccess: refresh,
  });
}

export function useCreateTranscription() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (file: File) =>
      unwrap(
        api.POST('/api/v1/studio/transcriptions', {
          body: { file: file as unknown as string },
          bodySerializer: (body) => {
            const form = new FormData();
            form.append('file', body.file as unknown as File);
            return form;
          },
        }),
      ),
    onSuccess: refresh,
  });
}

export function useDeleteStudioItem() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(api.DELETE('/api/v1/studio/items/{item_id}', { params: { path: { item_id: id } } })),
    onSuccess: refresh,
  });
}

export function audioUrl(id: string, format?: AudioFormat, download = false): string {
  const query = new URLSearchParams();
  if (format) query.set('format', format);
  if (download) query.set('download', 'true');
  const qs = query.toString();
  return `/api/v1/studio/items/${id}/audio${qs ? `?${qs}` : ''}`;
}

/** Descarga un texto como .txt, sin pasar por el servidor. */
export function downloadText(text: string, title: string) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = `${title.replace(/\.[^.]+$/, '') || 'transcripcion'}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}
