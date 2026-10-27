import { QueryClient, QueryObserver } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';
import type { Me } from '@/api/types';
import { meKey, resetSession } from './api';

describe('resetSession', () => {
  it('el que ya observa `me` (el provider de la marca) ve la sesión nueva y se borra lo demás', () => {
    const qc = new QueryClient();
    qc.setQueryData(meKey, null);
    qc.setQueryData(['agents'], [1]);
    const seen: unknown[] = [];
    const observer = new QueryObserver(qc, { queryKey: meKey, enabled: false });
    const off = observer.subscribe((r) => seen.push(r.data));

    const admin = { id: 'a', role: 'admin', branding: null } as unknown as Me;
    resetSession(qc, admin);

    expect(seen.at(-1)).toBe(admin);
    expect(qc.getQueryData(['agents'])).toBeUndefined();
    off();
  });
});
