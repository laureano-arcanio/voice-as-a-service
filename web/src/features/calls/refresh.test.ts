import { describe, expect, it } from 'vitest';
import type { CallDetail } from '@/api/types';
import { detailRefetchMs, REFRESH_MS } from './api';

const base = { workflow_status: 'active', whatsapp: null, call: null } as unknown as CallDetail;

describe('refresco (H09)', () => {
  it('intervalos de las vistas', () => {
    expect(REFRESH_MS).toMatchObject({ list: 5000, live: 3000, stats: 30_000, daily: 60_000 });
  });

  it('detalle: 2 s en llamada en curso, 5 s en WhatsApp activo, nada si termino', () => {
    const call = { ...base, call: { status: 'en_curso' } } as unknown as CallDetail;
    const wa = { ...base, whatsapp: { closed_at: null } } as unknown as CallDetail;
    expect(detailRefetchMs(call)).toBe(2000);
    expect(detailRefetchMs(wa)).toBe(5000);
    expect(detailRefetchMs({ ...base, call: { status: 'finalizada' } } as unknown as CallDetail)).toBe(false);
    expect(detailRefetchMs(undefined)).toBe(false);
  });
});
