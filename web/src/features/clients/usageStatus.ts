import type { InferenceUsage, Usage } from '@/api/types';
import { recentMonths, usagePercent } from '@/lib/format';

/** Desde este % de un tope, el consumo se marca como cerca (el color amarillo de las barras). */
export const NEAR_PCT = 70;

export interface UsageStatus {
  level: 'ok' | 'near' | 'full';
  /** Los consumos que llegaron al 100 % de su tope. */
  full: string[];
  /** Los que pasaron el NEAR_PCT sin llegar al tope, con su %. */
  near: { label: string; pct: number }[];
  /** Los minutos del mes que, al ritmo actual, van a pasar el tope. */
  willExceed: string[];
}

/** El estado de toda la cuenta de un vistazo: qué topes del plan se llegaron, están cerca o se van a pasar. */
export function usageStatus(usage: Usage, api?: InferenceUsage): UsageStatus {
  const current = usage.month === recentMonths(1)[0];
  const meters: [string, number | null][] = [
    ['Minutos entrantes', usagePercent(usage.inbound.used_minutes, usage.inbound.limit_minutes)],
    ['Minutos salientes', usagePercent(usage.outbound.used_minutes, usage.outbound.limit_minutes)],
    ['Llamadas simultáneas', usagePercent(usage.active_calls, usage.max_concurrent_calls)],
    ['Llamadas del mes', usagePercent(usage.calls_month.used, usage.calls_month.limit)],
    ['Números', usagePercent(usage.phone_numbers.used, usage.phone_numbers.limit)],
  ];
  if (current) {
    meters.push(
      ['Llamadas esta hora', usagePercent(usage.calls_hour.used, usage.calls_hour.limit)],
      ['Llamadas hoy', usagePercent(usage.calls_day.used, usage.calls_day.limit)],
    );
  }
  if (api) {
    // Un motor con tope 0 no está en el plan: no es un consumo para vigilar.
    const engines: [string, InferenceUsage['llm_input_tokens']][] = [
      ['LLM · tokens de entrada', api.llm_input_tokens],
      ['LLM · tokens de salida', api.llm_output_tokens],
      ['Síntesis (TTS)', api.tts_minutes],
      ['Transcripción (STT)', api.stt_minutes],
    ];
    for (const [label, m] of engines) if (m.limit) meters.push([label, usagePercent(m.used, m.limit)]);
  }
  const full: string[] = [];
  const near: UsageStatus['near'] = [];
  for (const [label, pct] of meters) {
    if (pct == null) continue;
    if (pct >= 100) full.push(label);
    else if (pct >= NEAR_PCT) near.push({ label, pct });
  }
  const willExceed = (
    [
      ['minutos entrantes', usage.inbound],
      ['minutos salientes', usage.outbound],
    ] as const
  )
    .filter(
      ([, m]) =>
        m.limit_minutes != null && m.projected_minutes != null && m.projected_minutes > m.limit_minutes,
    )
    .map(([label]) => label);
  return {
    level: full.length ? 'full' : near.length || willExceed.length ? 'near' : 'ok',
    full,
    near,
    willExceed,
  };
}
