import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

/** La landing es otro paquete y no puede importar de web/: su reproductor es una copia. Que no se desvien. */
describe('reproductor de PCM de la landing', () => {
  it('es el mismo codigo que el del dashboard', () => {
    const normalize = (path: string) =>
      readFileSync(new URL(path, import.meta.url), 'utf8')
        .replace(/^\s*\* COPIA de .*\n/m, '')
        .replace(/['"]/g, '"')
        .replace(/\s+/g, '')
        .replace(/,([)\]}])/g, '$1'); // las comas finales no cambian nada
    expect(normalize('../../../landing/src/scripts/pcm-player.ts')).toBe(normalize('./pcmPlayer.ts'));
  });
});
