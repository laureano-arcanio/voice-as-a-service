import { describe, expect, it } from 'vitest';
import {
  formatDateTime,
  formatDuration,
  formatLimit,
  formatPeriod,
  formatSeconds,
  lastDays,
  recentMonths,
  slugify,
  toIsoDate,
  usageColor,
  usagePercent,
} from './format';

describe('formatDuration', () => {
  it('formatea m:ss y h:mm:ss', () => {
    expect(formatDuration(0)).toBe('–');
    expect(formatDuration(null)).toBe('–');
    expect(formatDuration(5)).toBe('0:05');
    expect(formatDuration(125)).toBe('2:05');
    expect(formatDuration(3725)).toBe('1:02:05');
  });
});

describe('fechas', () => {
  it('muestra la hora local (es-AR) de un ISO en UTC, con Z o +00:00', () => {
    // 15:30 UTC = 12:30 en Buenos Aires (TZ del test).
    expect(formatDateTime('2026-09-29T15:30:00Z')).toBe('29/9/2026 12:30');
    expect(formatDateTime('2026-09-29T15:30:00+00:00')).toBe('29/9/2026 12:30');
    expect(formatDateTime(null)).toBe('–');
    expect(formatDateTime('basura')).toBe('–');
  });

  it('arma rangos con fechas locales, sin pasar por UTC', () => {
    const today = new Date(2026, 8, 29, 23, 30); // tarde a la noche: en UTC ya es 30/9
    expect(toIsoDate(today)).toBe('2026-09-29');
    expect(lastDays(7, today)).toEqual({ from: '2026-09-23', to: '2026-09-29' });
    expect(recentMonths(3, today)).toEqual(['2026-09', '2026-08', '2026-07']);
  });

  it('muestra el período [inicio, fin) con el último día incluido', () => {
    expect(formatPeriod('2026-09-01T03:00:00Z', '2026-10-01T03:00:00Z')).toBe('1/9/2026 al 30/9/2026');
  });
});

describe('números', () => {
  it('usa coma decimal', () => {
    expect(formatSeconds(1.234)).toBe('1,23 s');
    expect(formatSeconds(null)).toBe('–');
    expect(formatLimit(null)).toBe('Ilimitado');
    expect(formatLimit(1500, ' min')).toBe('1.500 min');
  });
});

describe('slugify', () => {
  it('saca acentos y deja minúsculas, números y _', () => {
    expect(slugify('Clínica Atentina — Córdoba 2')).toBe('clinica_atentina_cordoba_2');
    expect(slugify('  __Hola__ ')).toBe('hola');
    expect(slugify('x'.repeat(80))).toHaveLength(64);
  });
});

describe('consumo', () => {
  it('calcula % y color; sin límite no hay %', () => {
    expect(usagePercent(50, 100)).toBe(50);
    expect(usagePercent(5, null)).toBeNull();
    expect(usagePercent(1, 0)).toBe(100);
    expect(usageColor(null)).toBe('gray');
    expect(usageColor(50)).toBe('green');
    expect(usageColor(75)).toBe('yellow');
    expect(usageColor(95)).toBe('red');
  });
});
