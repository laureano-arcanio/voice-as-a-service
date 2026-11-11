import { describe, expect, it } from 'vitest';
import { buildView, liveSeconds, parseHandoffStatus, phaseLabel, resultLabel } from './handoffProgress';

const base = {
  v: 1,
  id: 1,
  state: 'running',
  result: null,
  area: 'Ventas',
  elapsed: 10,
  phase: 'ringing',
  phase_elapsed: 4,
  pre: [['preparing', 1.2]],
  reroutes: [],
  legs: [
    { n: 1, of: 3, area: 'Ventas', person: 'Ana', no_answer: false, result: 'no_answer', phases: [['dialing', 2], ['ringing', 20]], total: 22 },
    { n: 2, of: 3, area: 'Ventas', person: 'Beto', no_answer: false, result: null, phases: [['dialing', 1.4]], total: 5 },
  ],
  total: null,
};

describe('parseHandoffStatus', () => {
  it('lee bytes, texto y objetos', () => {
    const bytes = new TextEncoder().encode(JSON.stringify(base));
    expect(parseHandoffStatus(bytes)?.legs).toHaveLength(2);
    expect(parseHandoffStatus(JSON.stringify(base))?.area).toBe('Ventas');
    expect(parseHandoffStatus(base)?.legs[1].of).toBe(3);
  });

  it('ignora JSON roto, otra versión y estados desconocidos', () => {
    expect(parseHandoffStatus('{no')).toBeNull();
    expect(parseHandoffStatus(new Uint8Array([1, 2, 3]))).toBeNull();
    expect(parseHandoffStatus({ ...base, v: 2 })).toBeNull();
    expect(parseHandoffStatus({ ...base, state: 'raro' })).toBeNull();
    expect(parseHandoffStatus(null)).toBeNull();
    expect(parseHandoffStatus(7)).toBeNull();
  });

  it('tolera campos que faltan o vienen mal', () => {
    const s = parseHandoffStatus({ v: 1, state: 'running', phase_elapsed: null, legs: [null, { n: 1 }], pre: [5, ['x']] })!;
    expect(s.legs).toHaveLength(1);
    expect(s.legs[0].person).toBeNull();
    expect(s.phase_elapsed).toBeNull();
    expect(liveSeconds(s, 0, 2000).phase).toBe(2);
    expect(liveSeconds({ ...s, state: 'failed' }, 0, 2000).phase).toBe(0);
    expect(s.total).toBeNull();
  });
});

describe('liveSeconds', () => {
  const s = parseHandoffStatus(base)!;
  it('corre con el reloj del navegador desde que llegó', () => {
    expect(liveSeconds(s, 1000, 4000)).toEqual({ total: 13, phase: 7 });
  });
  it('un reloj atrasado no resta', () => {
    expect(liveSeconds(s, 5000, 1000)).toEqual({ total: 10, phase: 4 });
  });
  it('al terminar queda el total del worker', () => {
    const end = parseHandoffStatus({ ...base, state: 'connected', total: 48.4 })!;
    expect(liveSeconds(end, 0, 99_000).total).toBe(48.4);
  });
});

describe('buildView', () => {
  it('con nombres: a quién se llama, fase con contador e intentos anteriores', () => {
    const v = buildView(parseHandoffStatus(base)!, 'names', 0, 3000);
    expect(v.headline).toBe('Llamando a Beto (Ventas)');
    expect(v.live).toBe('Sonando: 7 s · antes: Marcando: 1 s');
    expect(v.total).toBe('13 s');
    expect(v.attempts).toEqual([
      { who: 'Ana (Ventas)', whom: 'Ana (Ventas)', note: '', result: 'No atendió', detail: 'Marcando: 2 s · Sonando: 20 s' },
    ]);
    expect(v.extra).toEqual(['Preparando: 1 s']);
  });

  it('anónimo: sin nombres ni áreas', () => {
    const v = buildView(parseHandoffStatus({ ...base, reroutes: [{ at: 3, from: 'Ventas', to: 'Soporte', reason: 'no_members' }] })!, 'anonymous', 0, 0);
    expect(v.headline).toBe('Llamando a la persona 2 de 3');
    expect(v.attempts[0].who).toBe('Persona 1 de 3');
    expect(JSON.stringify(v)).not.toMatch(/Ana|Beto|Ventas|Soporte/);
  });

  it('la persona de "Si nadie atiende"', () => {
    const s = parseHandoffStatus({
      ...base,
      legs: [{ n: 3, of: 3, area: 'Ventas', person: 'Ana', no_answer: true, result: null, phases: [], total: 1 }],
    })!;
    expect(buildView(s, 'names', 0, 0).note).toBe('Si nadie atiende: Ana');
    expect(buildView(s, 'anonymous', 0, 0).note).toBe('Si nadie atiende: persona 3');
  });

  it('entre intentos y antes del primero', () => {
    const between = parseHandoffStatus({ ...base, phase: null, legs: [base.legs[0]] })!;
    expect(buildView(between, 'names', 0, 0).headline).toBe('Buscando a la siguiente persona (Ventas)');
    expect(buildView(between, 'anonymous', 0, 0).headline).toBe('Buscando a la siguiente persona');
    expect(buildView(between, 'names', 0, 0).live).toBe('');
    const first = parseHandoffStatus({ ...base, legs: [], phase: 'announcing', phase_elapsed: 2 })!;
    const v = buildView(first, 'names', 0, 0);
    expect(v.headline).toBe('Avisándote (Ventas)');
    expect(v.live).toBe('Avisándote: 2 s');
  });

  it('conectado: total y desglose por persona', () => {
    const s = parseHandoffStatus({
      ...base,
      state: 'connected',
      result: 'confirmed',
      phase: null,
      total: 75,
      legs: [base.legs[0], { ...base.legs[1], result: 'confirmed', phases: [['dialing', 1], ['ringing', 9], ['whisper', 3]] }],
    })!;
    const v = buildView(s, 'names', 0, 0);
    expect(v.headline).toBe('Conectado con Beto (Ventas)');
    expect(v.total).toBe('1:15');
    expect(v.live).toBe('');
    expect(v.attempts.map((a) => a.result)).toEqual(['No atendió', 'Atendió']);
    expect(v.attempts[1].detail).toBe('Marcando: 1 s · Sonando: 9 s · Contándole el caso: 3 s');
  });

  it('no muestra las fases de menos de medio segundo', () => {
    const s = parseHandoffStatus({ ...base, legs: [{ ...base.legs[0], phases: [['dialing', 0.2], ['ringing', 3]] }] })!;
    expect(buildView(s, 'names', 0, 0).attempts[0].detail).toBe('Sonando: 3 s');
  });

  it('el cliente cortó', () => {
    const s = parseHandoffStatus({ ...base, state: 'failed', result: 'customer_hung_up', total: 9 })!;
    expect(buildView(s, 'anonymous', 0, 0).headline).toBe('No se pudo derivar: Cortaste antes de que atendieran');
  });

  it('fallido, con pases entre áreas solo con nombres', () => {
    const s = parseHandoffStatus({
      ...base,
      state: 'failed',
      result: 'no_answer',
      total: 40,
      reroutes: [{ at: 3, from: 'Ventas', to: 'Soporte', reason: 'no_members' }],
    })!;
    expect(buildView(s, 'names', 0, 0).headline).toBe('No se pudo derivar: Nadie atendió');
    expect(buildView(s, 'names', 0, 0).extra).toContain('Pasó de Ventas a Soporte (No había nadie a quien llamar)');
    expect(buildView(s, 'anonymous', 0, 0).extra).toEqual(['Preparando: 1 s']);
  });
});

describe('etiquetas', () => {
  it('traduce fases y resultados; lo desconocido queda vacío', () => {
    expect(phaseLabel('waiting_digit')).toBe('Esperando que marque 1');
    expect(phaseLabel('xx')).toBe('');
    expect(resultLabel('machine')).toBe('Buzón de voz');
    expect(resultLabel(null)).toBe('');
  });
});
