import { describe, expect, it } from 'vitest';
import type { InferenceUsage, Usage } from '@/api/types';
import { recentMonths } from '@/lib/format';
import { usageStatus } from './usageStatus';

const none = { used: 0, limit: null };
const USAGE: Usage = {
  month: recentMonths(1)[0],
  period_start: '2026-10-01T03:00:00Z',
  period_end: '2026-11-01T03:00:00Z',
  active_calls: 0,
  max_concurrent_calls: 4,
  inbound: {
    used_seconds: 600,
    used_minutes: 10,
    limit_minutes: 100,
    remaining_minutes: 90,
    projected_minutes: 30,
  },
  outbound: {
    used_seconds: 0,
    used_minutes: 0,
    limit_minutes: null,
    remaining_minutes: null,
    projected_minutes: 0,
  },
  phone_numbers: { used: 1, limit: 2 },
  calls_hour: none,
  calls_day: none,
  calls_month: none,
};
const API: InferenceUsage = {
  month: USAGE.month,
  period_start: '2026-10-01',
  period_end: '2026-11-01',
  rate_limit: null,
  llm_input_tokens: { used: 100, limit: 1000, remaining: 900 },
  llm_output_tokens: { used: 0, limit: null, remaining: null },
  tts_minutes: { used: 0, limit: 0, remaining: 0 },
  stt_minutes: { used: 0, limit: 10, remaining: 10 },
  requests: { llm: 0, stt: 0, tts: 0 },
  keys: [],
  studio: { tts_minutes: 0, stt_minutes: 0 },
};

describe('usageStatus', () => {
  it('unificado: vigila la bolsa compartida, no las dos barras', () => {
    const unified: Usage = {
      ...USAGE,
      unified_minutes: true,
      minutes: {
        used_seconds: 3000,
        used_minutes: 50,
        limit_minutes: 50,
        remaining_minutes: 0,
        projected_minutes: 80,
      },
      inbound: { ...USAGE.inbound, limit_minutes: 50, remaining_minutes: 0 },
      outbound: { ...USAGE.outbound, limit_minutes: 50, remaining_minutes: 0 },
    };
    const s = usageStatus(unified);
    expect(s.full).toEqual(['Minutos del plan']);
    expect(s.willExceed).toEqual(['minutos del plan']);
    expect(s.near.map((n) => n.label)).not.toContain('Minutos entrantes');
  });

  it('todo en orden: nada pasa del 70 %', () => {
    expect(usageStatus(USAGE, API)).toEqual({ level: 'ok', full: [], near: [], willExceed: [] });
  });

  it('cerca del tope: lo que pasó el 70 % y sin llegar al 100', () => {
    const s = usageStatus({ ...USAGE, phone_numbers: { used: 3, limit: 4 } }, API);
    expect(s.level).toBe('near');
    expect(s.near).toEqual([{ label: 'Números', pct: 75 }]);
  });

  it('tope alcanzado: el 100 %, también el de un motor de la API', () => {
    const s = usageStatus(USAGE, { ...API, stt_minutes: { used: 10, limit: 10, remaining: 0 } });
    expect(s.level).toBe('full');
    expect(s.full).toEqual(['Transcripción (STT)']);
  });

  it('un motor con tope 0 no está en el plan y no cuenta', () => {
    expect(usageStatus(USAGE, { ...API, tts_minutes: { used: 0, limit: 0, remaining: 0 } }).level).toBe('ok');
  });

  it('avisa si al ritmo actual los minutos pasan el tope', () => {
    const inbound = { ...USAGE.inbound, projected_minutes: 140 };
    const s = usageStatus({ ...USAGE, inbound }, API);
    expect(s.level).toBe('near');
    expect(s.willExceed).toEqual(['minutos entrantes']);
  });

  it('en un mes pasado no mira la hora ni el día en curso', () => {
    const past = { ...USAGE, month: '2020-01', calls_hour: { used: 5, limit: 5 } };
    expect(usageStatus(past, API).level).toBe('ok');
  });
});
