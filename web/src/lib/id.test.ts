import { describe, expect, it } from 'vitest';
import { uuid } from './id';

const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

describe('uuid', () => {
  it('da un v4 distinto cada vez', () => {
    expect(uuid()).toMatch(V4);
    expect(uuid()).not.toBe(uuid());
  });

  it('sin contexto seguro (http por la LAN) lo arma con getRandomValues', () => {
    // Propiedad propia que tapa la del prototipo; al borrarla vuelve la original.
    Object.defineProperty(crypto, 'randomUUID', { value: undefined, configurable: true });
    try {
      expect(uuid()).toMatch(V4);
      expect(uuid()).not.toBe(uuid());
    } finally {
      delete (crypto as { randomUUID?: unknown }).randomUUID;
    }
  });
});
