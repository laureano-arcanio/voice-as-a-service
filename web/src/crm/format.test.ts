import { fmtAgo, fmtDate, parseUtc, toIsoDay } from './format';

describe('formatos del CRM', () => {
  it('lee las horas UTC sin zona como UTC', () => {
    expect(parseUtc('2026-10-21T13:00:00')?.toISOString()).toBe('2026-10-21T13:00:00.000Z');
    expect(parseUtc('2026-10-21T10:00:00-03:00')?.toISOString()).toBe('2026-10-21T13:00:00.000Z');
    expect(parseUtc(null)).toBeNull();
  });

  it('no corre de día una fecha sola', () => {
    expect(fmtDate('2026-10-01')).toBe('1/10/2026');
    // 01:00 UTC del 22 es el 21 a la noche en Argentina (TZ de los tests).
    expect(fmtDate('2026-10-22T01:00:00')).toBe('21/10/2026');
    expect(fmtDate(null)).toBe('–');
  });

  it('dice hace cuánto en días', () => {
    const now = new Date('2026-10-21T15:00:00-03:00');
    expect(fmtAgo('2026-10-21T12:00:00', now)).toBe('hoy');
    expect(fmtAgo('2026-10-20T15:00:00', now)).toBe('ayer');
    expect(fmtAgo('2026-10-16T15:00:00', now)).toBe('hace 5 d');
  });

  it('pasa una fecha local a ISO', () => {
    expect(toIsoDay(new Date(2026, 9, 5))).toBe('2026-10-05');
    expect(toIsoDay('2026-10-05')).toBe('2026-10-05');
  });
});
