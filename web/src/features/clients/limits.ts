import type { LimitField } from '@/api/types';

/** Como se nombra cada limite del tier en la UI, con su unidad y el grupo del selector. */
export const LIMIT_META: Record<LimitField, { label: string; unit: string; group: string }> = {
  max_concurrent_calls: { label: 'Llamadas simultáneas', unit: '', group: 'Llamadas' },
  max_calls_per_hour: { label: 'Llamadas por hora', unit: '', group: 'Llamadas' },
  max_calls_per_day: { label: 'Llamadas por día', unit: '', group: 'Llamadas' },
  max_calls_per_month: { label: 'Llamadas por mes', unit: '', group: 'Llamadas' },
  inbound_minutes: { label: 'Minutos entrantes por mes', unit: ' min', group: 'Minutos y números' },
  outbound_minutes: { label: 'Minutos salientes por mes', unit: ' min', group: 'Minutos y números' },
  max_phone_numbers: { label: 'Números de teléfono', unit: '', group: 'Minutos y números' },
  api_llm_input_tokens: { label: 'Tokens de entrada del LLM por mes', unit: '', group: 'API de inferencia' },
  api_llm_output_tokens: { label: 'Tokens de salida del LLM por mes', unit: '', group: 'API de inferencia' },
  api_tts_minutes: { label: 'Minutos de síntesis (TTS) por mes', unit: ' min', group: 'API de inferencia' },
  api_stt_minutes: { label: 'Minutos de transcripción (STT) por mes', unit: ' min', group: 'API de inferencia' },
  api_rate_limit: { label: 'Pedidos por minuto', unit: '', group: 'API de inferencia' },
};

/** Campos en el orden del selector (agrupados). */
export const LIMIT_FIELDS = Object.keys(LIMIT_META) as LimitField[];

/** El ultimo dia del mes en curso (hora local), YYYY-MM-DD. */
export function endOfThisMonth(today = new Date()): string {
  const d = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
