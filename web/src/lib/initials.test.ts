import { initials } from './initials';

describe('initials', () => {
  it('primera y última palabra, sin conectores', () => {
    expect(initials('Clínica del Sur')).toBe('CS');
    expect(initials('Estudio Jurídico Pérez y Asociados')).toBe('EA');
  });
  it('una palabra y vacío', () => {
    expect(initials('acme')).toBe('A');
    expect(initials('  ')).toBe('·');
  });
});
