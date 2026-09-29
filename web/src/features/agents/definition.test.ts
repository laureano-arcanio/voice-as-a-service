import { describe, expect, it } from 'vitest';
import {
  conditionLabel,
  findPathOffset,
  parseDefinition,
  readWorkflow,
  requiredLabel,
  toJsonText,
} from './definition';

const def = {
  id: 'demo',
  version: 3,
  engine: 'classic',
  agent: { name: 'Sofía', role: 'asesora', language: 'es-AR', voice: 'sofia' },
  objective: { description: 'Agendar una demo' },
  conversation: { opening: 'Hola', rules: ['Breve'] },
  fields: {
    zone: { priority: 2, description: 'Zona', question: '¿Dónde?', required_if: { wants: true } },
    wants: { priority: 1, description: 'Quiere', type: 'boolean', question: '¿Querés?', required: true },
  },
  completion: {
    outcomes: [
      { id: 'ok', label: 'Agendado', when: { wants: true }, message: 'Genial', goal: true },
      { id: 'no', label: 'No', message: 'Chau' },
    ],
  },
};

describe('readWorkflow', () => {
  it('ordena los datos por prioridad y arma etiquetas', () => {
    const w = readWorkflow(def);
    expect(w.fields.map(([n]) => n)).toEqual(['wants', 'zone']);
    expect(requiredLabel(w.fields[0][1])).toBe('Sí');
    expect(requiredLabel(w.fields[1][1])).toBe('Si wants = true');
    expect(conditionLabel(w.outcomes[1].when)).toBe('en otro caso');
    expect(w.agent.voice).toBe('sofia');
  });

  it('tolera definiciones incompletas', () => {
    const w = readWorkflow({});
    expect(w.fields).toEqual([]);
    expect(w.engine).toBe('structured');
  });
});

describe('editor', () => {
  it('ubica la ruta de un error en el JSON', () => {
    const text = toJsonText(def);
    const pos = findPathOffset(text, 'fields.zone.question');
    expect(text.slice(pos, pos + 10)).toBe('"question"');
    expect(pos).toBeGreaterThan(text.indexOf('"zone"'));
    expect(findPathOffset(text, 'completion.outcomes.1.label')).toBeGreaterThan(0);
  });

  it('valida que sea un objeto JSON', () => {
    expect(parseDefinition('{"a":1}').ok).toBe(true);
    expect(parseDefinition('[1]').ok).toBe(false);
    const bad = parseDefinition('{"a":');
    expect(bad.ok).toBe(false);
  });
});
