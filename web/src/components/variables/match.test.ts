import { describe, expect, it } from 'vitest';
import { filter, insert, openAt, usedVariables, variableRanges } from './match';

describe('openAt', () => {
  it('{{ al final del texto abre con la búsqueda vacía', () => {
    expect(openAt('Hola {{', 7)).toEqual({ from: 5, query: '' });
  });
  it('{{nom filtra por lo escrito', () => {
    expect(openAt('Hola {{nom', 10)).toEqual({ from: 5, query: 'nom' });
  });
  it('{{nombre}} ya cerrado no abre', () => {
    expect(openAt('Hola {{nombre}}', 15)).toBeNull();
  });
  it('un espacio, una llave o un salto de línea cierran', () => {
    expect(openAt('{{ a b', 6)).toBeNull();
    expect(openAt('{{ ', 3)).toBeNull();
    expect(openAt('{{a}}b', 6)).toBeNull();
    expect(openAt('{{a\nb', 5)).toBeNull();
  });
  it('con dos {{ en la misma línea usa el último antes del cursor', () => {
    expect(openAt('{{a}} y {{b', 11)).toEqual({ from: 8, query: 'b' });
    expect(openAt('{{a}} y {{b', 3)).toEqual({ from: 0, query: 'a' });
  });
  it('mira solo lo anterior al cursor', () => {
    expect(openAt('{{nom y más', 5)).toEqual({ from: 0, query: 'nom' });
  });
  it('sin {{ no abre; admite punto y mayúsculas tras él (secrets.TOKEN)', () => {
    expect(openAt('hola', 4)).toBeNull();
    expect(openAt('{', 1)).toBeNull();
    expect(openAt('{{secrets.TO', 12)).toEqual({ from: 0, query: 'secrets.TO' });
  });
});

describe('filter', () => {
  const opts = [{ name: 'nombre' }, { name: 'call.phone' }, { name: 'phone_extra' }, { name: 'día' }];
  it('vacío devuelve todo en el mismo orden', () => {
    expect(filter(opts, '').map((o) => o.name)).toEqual(['nombre', 'call.phone', 'phone_extra', 'día']);
  });
  it('prefijo primero, después subcadena', () => {
    expect(filter(opts, 'phone').map((o) => o.name)).toEqual(['phone_extra', 'call.phone']);
  });
  it('sin acentos ni mayúsculas', () => {
    expect(filter(opts, 'DIA').map((o) => o.name)).toEqual(['día']);
    expect(filter(opts, 'NOM').map((o) => o.name)).toEqual(['nombre']);
  });
  it('hasta 50', () => {
    const many = Array.from({ length: 80 }, (_, i) => ({ name: `v${i}` }));
    expect(filter(many, '')).toHaveLength(50);
    expect(filter(many, 'v')).toHaveLength(50);
  });
});

describe('insert', () => {
  it('reemplaza lo tipeado por {{name}} y deja el cursor al final', () => {
    const r = insert('Hola {{no', 5, 9, 'nombre');
    expect(r.text).toBe('Hola {{nombre}}');
    expect(r.cursor).toBe(15);
  });
  it('se come el }} que ya estaba justo después del cursor', () => {
    const r = insert('Hola {{no}} che', 5, 9, 'nombre');
    expect(r.text).toBe('Hola {{nombre}} che');
    expect(r.cursor).toBe(15);
    expect(r.to).toBe(11);
  });
  it('un solo } después no se come', () => {
    expect(insert('{{a} x', 0, 3, 'b').text).toBe('{{b}}} x');
  });
  it('con dos {{ en la línea toca solo el de adelante', () => {
    const r = insert('{{a}} y {{b', 8, 11, 'today');
    expect(r.text).toBe('{{a}} y {{today}}');
  });
  it('sin {{ tipeado (from == cursor) inserta en el cursor', () => {
    expect(insert('ab', 1, 1, 'x').text).toBe('a{{x}}b');
  });
  it('parcial: deja {{fields. abierto y no come el }}', () => {
    const r = insert('{{fi}}', 0, 4, 'fields.', true);
    expect(r.text).toBe('{{fields.}}');
    expect(r.cursor).toBe(9);
  });
});

describe('usedVariables', () => {
  it('únicos y en orden, con espacios y punto', () => {
    expect(usedVariables('{{b}} {{ a }} {{b}} {{call.phone}} {{secrets.TOKEN}} {{Mal}} {{ x y }}')).toEqual([
      'b',
      'a',
      'call.phone',
      'secrets.TOKEN',
    ]);
  });
  it('posiciones', () => {
    expect(variableRanges('ab {{x}}')).toEqual([{ from: 3, to: 8, name: 'x' }]);
  });
});

describe('texto grande', () => {
  it('40.000 caracteres en menos de 50 ms', () => {
    const text = 'línea con {{nombre}} y texto de relleno para el prompt.\n'.repeat(740) + 'cierre {{no';
    expect(text.length).toBeGreaterThan(40_000 - 100);
    const t0 = performance.now();
    const m = openAt(text, text.length);
    filter(
      Array.from({ length: 200 }, (_, i) => ({ name: `variable_${i}` })),
      'var',
    );
    usedVariables(text);
    insert(text, m!.from, text.length, 'nombre');
    expect(performance.now() - t0).toBeLessThan(50);
    expect(m!.query).toBe('no');
  });
});
