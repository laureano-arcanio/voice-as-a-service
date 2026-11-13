import { describe, expect, it } from 'vitest';
import {
  conditionLabel,
  findPathOffset,
  firstLines,
  parseDefinition,
  readWorkflow,
  toJsonText,
} from './definition';

const def = {
  id: 'demo',
  version: 3,
  agent: { name: 'Sofía', language: 'es-AR', voice: 'sofia' },
  prompt: '# Identidad\nSos Sofía.\n\n# Objetivo\nAgendar una demo.\n',
  first_message: 'Hola',
  first_message_delay_ms: 300,
  variables: [
    { name: 'deuda', default: '1000', description: 'Lo que debe' },
    { name: 'saludo', default: '', description: '' },
  ],
  analysis: {
    summary: false,
    instructions: 'Extraé lo que dijo.',
    fields: [
      { name: 'z', description: 'Zeta', type: 'string' },
      { name: 'a', label: 'Alfa', description: 'Alfa', type: 'choice', options: ['si', 'no'] },
      { name: 'm', description: 'Me', type: 'boolean' },
    ],
    outcomes: [
      { id: 'ok', label: 'Agendado', when: { a: 'si' }, goal: true },
      { id: 'no', label: 'No', when: {} },
    ],
  },
};

describe('readWorkflow', () => {
  it('lee prompt, variables y el análisis en el orden de las listas', () => {
    const w = readWorkflow(def);
    expect(w.prompt).toContain('# Objetivo');
    expect(w.firstMessage).toBe('Hola');
    expect(w.firstMessageDelayMs).toBe(300);
    expect(w.variables.map((v) => [v.name, v.default])).toEqual([
      ['deuda', '1000'],
      ['saludo', ''],
    ]);
    expect(w.fields.map((f) => f.name)).toEqual(['z', 'a', 'm']);
    expect(w.fields[1]).toMatchObject({ label: 'Alfa', type: 'choice', options: ['si', 'no'] });
    expect(w.analysisInstructions).toBe('Extraé lo que dijo.');
    expect(w.summary).toBe(false);
    expect(conditionLabel(w.outcomes[1].when)).toBe('en otro caso');
    expect(w.agent.voice).toBe('sofia');
  });

  it('tolera definiciones incompletas', () => {
    const w = readWorkflow({});
    expect(w.fields).toEqual([]);
    expect(w.outcomes).toEqual([]);
    expect(w.variables).toEqual([]);
    expect(w.summary).toBe(true);
    expect(w.external).toBe(false);
  });

  it('las primeras líneas del prompt', () => {
    expect(firstLines('# Uno\na\nb\nc\nd\ne\nf', 3)).toBe('# Uno\na\nb');
  });
});

describe('editor', () => {
  it('ubica la ruta de un error en el JSON', () => {
    const text = toJsonText(def);
    const pos = findPathOffset(text, 'analysis.fields.1.description');
    expect(text.slice(pos, pos + 13)).toBe('"description"');
    expect(pos).toBeGreaterThan(text.indexOf('"fields"'));
    expect(findPathOffset(text, 'analysis.outcomes.1.label')).toBeGreaterThan(0);
  });

  it('valida que sea un objeto JSON', () => {
    expect(parseDefinition('{"a":1}').ok).toBe(true);
    expect(parseDefinition('[1]').ok).toBe(false);
    const bad = parseDefinition('{"a":');
    expect(bad.ok).toBe(false);
  });
});
