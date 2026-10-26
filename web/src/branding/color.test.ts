import { describe, expect, it } from 'vitest';
import { theme } from '@/theme';
import { contrast, isHex, scale, textOn } from './color';

describe('color', () => {
  it('mide el contraste como el backend (docs/MARCA_BLANCA_PLAN.md, 3.3)', () => {
    const table: Record<string, [number, number]> = {
      '#2456e6': [5.92, 3.16],
      '#0068fd': [4.77, 3.92],
      '#272a35': [14.3, 1.31],
      '#4d39c3': [7.81, 2.4],
      '#fd6421': [2.99, 6.26],
    };
    for (const [color, [onWhite, onInk]] of Object.entries(table)) {
      expect(Math.round(contrast('#ffffff', color) * 100) / 100).toBe(onWhite);
      expect(Math.round(contrast('#0b1220', color) * 100) / 100).toBe(onInk);
    }
    expect(textOn('#272a35')).toBe('#ffffff');
    expect(textOn('#ffffff')).toBe('#0b1220');
    expect(textOn('#fd6421')).toBe('#0b1220');
  });

  it('la escala del azul de Atentina reproduce la del tema (hasta 10 puntos por canal)', () => {
    const made = scale('#2456e6');
    const real = theme.colors!.blue!;
    expect(made[6]).toBe('#2456e6');
    const channel = (hex: string, i: number) => parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16);
    for (let shade = 0; shade < 10; shade++) {
      for (let i = 0; i < 3; i++) {
        expect(Math.abs(channel(made[shade], i) - channel(real[shade], i))).toBeLessThanOrEqual(11);
      }
    }
  });

  it('valida #rrggbb', () => {
    expect(isHex('#0068FD')).toBe(true);
    expect(isHex('0068fd')).toBe(false);
    expect(isHex('#06f')).toBe(false);
  });
});
