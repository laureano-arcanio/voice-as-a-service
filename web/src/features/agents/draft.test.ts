import { describe, expect, it } from 'vitest';
import {
  errorTarget,
  fromDraft,
  move,
  newField,
  pathLabel,
  renameField,
  renumber,
  stableJson,
  toDraft,
} from './draft';

// Como la devuelve el servidor (model_dump con exclude_none).
const def = {
  id: 'demo',
  version: 3,
  engine: 'classic',
  agent: { name: 'Sofía', role: 'asesora', language: 'es-AR', voice: 'sofia' },
  objective: { description: 'Agendar una demo\n' },
  conversation: { opening: 'Hola', rules: ['Breve'] },
  knowledge: '- Precio: lo cotiza un asesor.\n',
  fields: {
    zone: {
      priority: 20,
      description: 'Zona',
      type: 'choice',
      options: ['norte', 'sur'],
      required: false,
      required_if: { wants: true },
      question: '¿Dónde?',
    },
    wants: {
      priority: 10,
      label: 'Quiere',
      description: 'Quiere',
      type: 'boolean',
      required: true,
      question: '¿Querés?',
    },
  },
  completion: {
    when: 'all_required_fields_completed',
    outcomes: [
      { id: 'ok', label: 'Agendado', when: { wants: true }, message: 'Genial', goal: true },
      { id: 'no', label: 'No', when: {}, message: 'Chau', goal: false },
    ],
  },
};

describe('toDraft / fromDraft', () => {
  it('ida y vuelta da la misma definicion', () => {
    expect(stableJson(fromDraft(toDraft(def)))).toBe(stableJson(def));
  });

  it('ordena los datos por prioridad y lee las condiciones', () => {
    const d = toDraft(def);
    expect(d.fields.map((f) => f.name)).toEqual(['wants', 'zone']);
    expect(d.fields[1]).toMatchObject({ requirement: 'if', type: 'choice', options: ['norte', 'sur'] });
    expect(d.fields[1]!.conditions[0]).toMatchObject({ field: 'wants', value: true });
  });

  it('el mismo borrador con el otro motor solo cambia engine', () => {
    const d = toDraft(def);
    const a = fromDraft(d);
    const b = fromDraft({ ...d, engine: 'structured' });
    expect({ ...a, engine: null }).toEqual({ ...b, engine: null });
  });

  it('sin voz, sin etiqueta y sin opciones fuera de choice: no van', () => {
    const d = toDraft(def);
    d.voice = '';
    d.fields[1] = { ...d.fields[1]!, type: 'string', label: '' };
    const out = fromDraft(d) as { agent: object; fields: Record<string, object> };
    expect(out.agent).not.toHaveProperty('voice');
    expect(out.fields.zone).not.toHaveProperty('options');
    expect(out.fields.zone).not.toHaveProperty('label');
  });

  it('el ultimo resultado queda sin condiciones y las reglas vacias se descartan', () => {
    const d = toDraft(def);
    d.outcomes[1]!.conditions = [{ key: 'x', field: 'wants', value: false }];
    d.rules.push({ key: 'y', text: '  ' });
    const out = fromDraft(d) as {
      completion: { outcomes: { when: object }[] };
      conversation: { rules: string[] };
    };
    expect(out.completion.outcomes[1]!.when).toEqual({});
    expect(out.conversation.rules).toEqual(['Breve']);
  });

  it('condicional sin condiciones no manda required_if', () => {
    const d = toDraft(def);
    d.fields[1]!.conditions = [];
    const out = fromDraft(d) as { fields: Record<string, object> };
    expect(out.fields.zone).not.toHaveProperty('required_if');
    expect(out.fields.zone).toMatchObject({ required: false });
  });
});

describe('edicion', () => {
  it('renombrar un dato actualiza sus referencias', () => {
    const d = renameField(toDraft(def), 0, 'quiere');
    expect(d.fields[0]!.name).toBe('quiere');
    expect(d.fields[1]!.conditions[0]!.field).toBe('quiere');
    expect(d.outcomes[0]!.conditions[0]!.field).toBe('quiere');
  });

  it('mover y renumerar', () => {
    const d = toDraft(def);
    const moved = renumber(move(d.fields, 1, 0));
    expect(moved.map((f) => [f.name, f.priority])).toEqual([
      ['zone', 10],
      ['wants', 20],
    ]);
    expect(move(d.fields, 0, -1)).toBe(d.fields);
  });

  it('dato nuevo: nombre libre y prioridad al final', () => {
    const f = newField(toDraft(def).fields);
    expect(f.name).toBe('dato_3');
    expect(f.priority).toBe(30);
  });
});

describe('errores', () => {
  it('ubica la ruta en el formulario y la traduce', () => {
    const d = toDraft(def);
    expect(errorTarget(d, 'fields.zone.question')).toEqual({ section: 'dato', key: d.fields[1]!.key });
    expect(errorTarget(d, 'completion.outcomes.0.when')).toEqual({
      section: 'resultado',
      key: d.outcomes[0]!.key,
    });
    expect(errorTarget(d, 'agent.voice')).toEqual({ section: 'voz' });
    expect(errorTarget(d, '')).toBeNull();
    expect(pathLabel(d, 'fields.zone.question')).toBe('Datos › zone › pregunta');
    expect(pathLabel(d, 'completion.outcomes.0.message')).toBe('Resultados › Agendado › mensaje');
    expect(errorTarget(d, 'completion.outcomes.no.when')).toEqual({
      section: 'resultado',
      key: d.outcomes[1]!.key,
    });
    expect(pathLabel(d, 'completion.outcomes')).toBe('Resultados');
  });
});
