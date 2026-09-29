import { describe, expect, it } from 'vitest';
import { diffLines, withContext } from './diff';

describe('diffLines', () => {
  it('marca lineas agregadas y borradas', () => {
    const d = diffLines('a\nb\nc', 'a\nx\nc');
    expect(d).toEqual([
      { op: 'same', text: 'a' },
      { op: 'del', text: 'b' },
      { op: 'add', text: 'x' },
      { op: 'same', text: 'c' },
    ]);
  });

  it('recorta el contexto con saltos', () => {
    const a = Array.from({ length: 20 }, (_, i) => `l${i}`).join('\n');
    const b = a.replace('l10', 'L10');
    const ctx = withContext(diffLines(a, b), 1);
    expect(ctx[0]).toBeNull();
    expect(ctx[ctx.length - 1]).toBeNull();
    expect(ctx.filter(Boolean).map((l) => l!.text)).toEqual(['l9', 'l10', 'L10', 'l11']);
  });
});
