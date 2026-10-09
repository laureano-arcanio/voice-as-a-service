import { describe, expect, it } from 'vitest';
import { formatCallLimit, formatRetention, minutesToSeconds } from './format';

describe('limites de tier y cliente', () => {
  it('duracion maxima en minutos', () => {
    expect(formatCallLimit(900)).toBe('15 min');
    expect(formatCallLimit(1230)).toBe('20,5 min');
    expect(formatCallLimit(null)).toBe('–');
  });

  it('retencion en dias', () => {
    expect(formatRetention(null)).toBe('Sin borrado');
    expect(formatRetention(1)).toBe('1 día');
    expect(formatRetention(365)).toBe('365 días');
  });

  it('minutos del formulario a segundos', () => {
    expect(minutesToSeconds('')).toBeNull();
    expect(minutesToSeconds(20)).toBe(1200);
    // Sin cambios no redondea lo cargado por la API.
    expect(minutesToSeconds(21, 1230)).toBe(1230);
    expect(minutesToSeconds(30, 1230)).toBe(1800);
  });
});
