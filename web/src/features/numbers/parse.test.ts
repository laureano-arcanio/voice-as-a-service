import { describe, expect, it } from 'vitest';
import { MAX_BULK, matchesNumber, normalizeE164, plural, previewNumbers, splitNumbers } from './parse';

describe('splitNumbers', () => {
  it('separa por línea, coma o punto y coma, sin partir los espacios internos', () => {
    expect(splitNumbers('+541152630861\n+54 11 5263-0862, +541152630863;+541152630864\r\n\n  ,')).toEqual([
      '+541152630861',
      '+54 11 5263-0862',
      '+541152630863',
      '+541152630864',
    ]);
    expect(splitNumbers('  \n , ')).toEqual([]);
  });
});

describe('normalizeE164', () => {
  it('normaliza como el server', () => {
    expect(normalizeE164('+54 (11) 5263-0861')).toBe('+541152630861');
    expect(normalizeE164('+54.11.5263.0861')).toBe('+541152630861');
    expect(normalizeE164('541152630861')).toBeNull(); // sin +
    expect(normalizeE164('+1234567')).toBeNull(); // menos de 8 digitos
    expect(normalizeE164('+54 11 abc')).toBeNull();
  });
});

describe('previewNumbers', () => {
  it('cuenta válidos, inválidos y repetidos (normalizados)', () => {
    const p = previewNumbers('+541152630861\n+54 11 5263-0861\nhola\n+541152630862');
    expect(p.valid).toBe(2);
    expect(p.invalid).toEqual(['hola']);
    expect(p.duplicated).toEqual(['+54 11 5263-0861']);
    expect(p.tokens).toHaveLength(4); // se mandan todos: el server informa los salteados
    expect(p.tooMany).toBe(false);
  });

  it('avisa si se pasa del máximo por carga', () => {
    const text = Array.from({ length: MAX_BULK + 1 }, (_, i) => `+5411${String(i).padStart(8, '0')}`).join(
      '\n',
    );
    expect(previewNumbers(text).tooMany).toBe(true);
  });
});

describe('matchesNumber', () => {
  const n = { e164: '+541152630861', label: 'Recepción' };
  it('busca por dígitos ignorando espacios y guiones, o por etiqueta', () => {
    expect(matchesNumber(n, '11 5263-08')).toBe(true);
    expect(matchesNumber(n, '999')).toBe(false);
    expect(matchesNumber(n, 'recep')).toBe(true);
    expect(matchesNumber(n, '')).toBe(true);
  });
});

describe('plural', () => {
  it('usa singular solo para 1', () => {
    expect(plural(1, 'número cargado', 'números cargados')).toBe('1 número cargado');
    expect(plural(0, 'número cargado', 'números cargados')).toBe('0 números cargados');
  });
});
