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
  withPhoneField,
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

  it('record_audio: false no va (como la voz); true si', () => {
    expect(toDraft(def).recordAudio).toBe(false);
    expect(fromDraft(toDraft(def))).not.toHaveProperty('record_audio');
    const d = toDraft({ ...def, record_audio: true });
    expect(d.recordAudio).toBe(true);
    expect(fromDraft(d)).toMatchObject({ record_audio: true });
  });

  it('call_summary_email: false no va (como record_audio); true si', () => {
    expect(toDraft(def).callSummaryEmail).toBe(false);
    expect(fromDraft(toDraft(def))).not.toHaveProperty('call_summary_email');
    const d = toDraft({ ...def, call_summary_email: true });
    expect(d.callSummaryEmail).toBe(true);
    expect(fromDraft(d)).toMatchObject({ call_summary_email: true });
    expect(errorTarget(d, 'call_summary_email')).toEqual({ section: 'voz' });
  });

  it('un tipo de dato que la UI no conoce se conserva (no pasa a string)', () => {
    const d = {
      ...def,
      fields: { ...def.fields, x: { ...Object.values(def.fields)[0], type: 'tipo_nuevo' } },
    };
    expect(fromDraft(toDraft(d)).fields).toMatchObject({ x: { type: 'tipo_nuevo' } });
  });

  it('withPhoneField: agrega telefono (tipo phone, obligatorio) si falta; no lo duplica', () => {
    const d = withPhoneField(toDraft(def));
    const phone = d.fields.at(-1)!;
    expect(phone).toMatchObject({ name: 'telefono', type: 'phone', requirement: 'yes', label: 'Teléfono' });
    expect(withPhoneField(d).fields).toHaveLength(d.fields.length);
    expect(fromDraft(d).fields).toMatchObject({ telefono: { type: 'phone', required: true } });
    expect(withPhoneField({ ...toDraft(def), engine: 'assistant' }).fields).toHaveLength(
      toDraft(def).fields.length,
    );
  });

  it('no_contact (baja por voz): sin marcar no va a la definicion; marcado, ida y vuelta', () => {
    expect(toDraft(def).outcomes.map((o) => o.noContact)).toEqual([false, false]);
    expect(JSON.stringify(fromDraft(toDraft(def)))).not.toContain('no_contact');
    const flagged = {
      ...def,
      completion: {
        ...def.completion,
        outcomes: [
          {
            id: 'baja',
            label: 'Baja',
            when: { wants: false },
            message: 'Listo',
            goal: false,
            no_contact: true,
          },
          ...def.completion.outcomes,
        ],
      },
    };
    const d = toDraft(flagged);
    expect(d.outcomes[0].noContact).toBe(true);
    expect(stableJson(fromDraft(d))).toBe(stableJson(flagged));
  });

  it('wa_session_minutes: sin valor no va (como record_audio); con valor, ida y vuelta', () => {
    expect(toDraft(def).waSessionMinutes).toBeNull();
    expect(fromDraft(toDraft(def))).not.toHaveProperty('wa_session_minutes');
    const d = toDraft({ ...def, wa_session_minutes: 2 });
    expect(d.waSessionMinutes).toBe(2);
    expect(fromDraft(d)).toMatchObject({ wa_session_minutes: 2 });
  });

  it('llm (conexiones BYOK): ida y vuelta, y sin etapas externas no va a la definicion', () => {
    const llm = {
      stages: [
        { from_turn: 1 },
        {
          from_turn: 4,
          connection: 'c1',
          model: 'vendor/model',
          generation: { params: { temperature: 0.3, top_p: 0.9 } },
        },
      ],
      fallback_local: false,
    };
    const d = toDraft({ ...def, llm });
    expect(
      d.llm?.stages.map((s) => [
        s.fromTurn,
        s.connection,
        s.model,
        s.generation.map((p) => [p.name, p.value]),
      ]),
    ).toEqual([
      [1, null, '', []],
      [
        4,
        'c1',
        'vendor/model',
        [
          ['temperature', 0.3],
          ['top_p', 0.9],
        ],
      ],
    ]);
    expect(fromDraft(d)).toMatchObject({ llm });
    expect(fromDraft(toDraft(def))).not.toHaveProperty('llm');
    const local = toDraft({ ...def, llm: { stages: [{ from_turn: 1 }], fallback_local: true } });
    expect(fromDraft(local)).not.toHaveProperty('llm');
    // Una etapa local con parametros si viaja (no necesita conexion).
    local.llm!.stages[0]!.generation = [{ key: 'k', name: 'temperature', value: 0.5 }];
    expect(fromDraft(local)).toMatchObject({
      llm: { stages: [{ from_turn: 1, generation: { params: { temperature: 0.5 } } }], fallback_local: true },
    });
  });

  it('generation del agente: ida y vuelta con tipos y sin parametros no va', () => {
    const d = toDraft({ ...def, generation: { params: { temperature: 0.4, enable_thinking: true } } });
    expect(d.generation.map((p) => [p.name, p.value])).toEqual([
      ['temperature', 0.4],
      ['enable_thinking', true],
    ]);
    expect(fromDraft(d)).toMatchObject({
      generation: { params: { temperature: 0.4, enable_thinking: true } },
    });
    expect(fromDraft(toDraft(def))).not.toHaveProperty('generation');
  });

  it('los errores de llm llevan a la seccion Modelo de lenguaje', () => {
    const d = toDraft(def);
    expect(errorTarget(d, 'llm.stages.1.connection')).toEqual({ section: 'modelo' });
    expect(errorTarget(d, 'generation.params.temperature')).toEqual({ section: 'modelo' });
    expect(pathLabel(d, 'llm.stages.1.connection')).toBe('Modelo de lenguaje › etapa 2 › conexión');
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

describe('motor assistant', () => {
  // Como la devuelve el servidor: sin datos y con las herramientas de una app.
  const assistant = {
    id: 'asistente',
    version: 2,
    engine: 'assistant',
    agent: { name: 'Asis', role: 'asistente del gym', language: 'es-AR' },
    objective: { description: 'Ayudar al dueño' },
    conversation: { opening: 'Hola', rules: [] },
    knowledge: '',
    fields: {},
    completion: {
      when: 'all_required_fields_completed',
      outcomes: [{ id: 'default', label: 'Conversación', when: {}, message: 'Chau', goal: false }],
    },
    tools: [
      { app: 'sugym-gestion', tools: ['*'] },
      { app: 'sugym-turnos', tools: ['buscar_turno', 'reservar'] },
    ],
  };

  it('ida y vuelta conserva el motor y las herramientas', () => {
    const d = toDraft(assistant);
    expect(d.engine).toBe('assistant');
    expect(d.tools).toEqual(assistant.tools);
    expect(stableJson(fromDraft(d))).toBe(stableJson(assistant));
  });

  it('con otro motor no manda tools (el servidor las rechaza)', () => {
    const out = fromDraft({ ...toDraft(assistant), engine: 'classic' });
    expect(out).not.toHaveProperty('tools');
    expect(out.engine).toBe('classic');
  });

  it('un motor desconocido queda en classic', () => {
    expect(toDraft({ ...assistant, engine: 'otro' }).engine).toBe('classic');
  });

  it('errores de tools van a la seccion Herramientas', () => {
    const d = toDraft(assistant);
    expect(errorTarget(d, 'tools.1.tools')).toEqual({ section: 'herramientas' });
    expect(pathLabel(d, 'tools.1.tools')).toBe('Herramientas › sugym-turnos › herramientas');
    expect(pathLabel(d, 'tools.0.app')).toBe('Herramientas › sugym-gestion › app');
  });
});

describe('setGrant', () => {
  it('agrega, cambia y saca la app', async () => {
    const { setGrant } = await import('./grants');
    const one = setGrant([], 'a', ['*']);
    expect(one).toEqual([{ app: 'a', tools: ['*'] }]);
    const two = setGrant(setGrant(one, 'b', ['x']), 'a', ['y', 'z']);
    expect(two).toEqual([
      { app: 'a', tools: ['y', 'z'] },
      { app: 'b', tools: ['x'] },
    ]);
    expect(setGrant(two, 'a', null)).toEqual([{ app: 'b', tools: ['x'] }]);
  });
});

describe('motor external (agente propio)', () => {
  const ext = {
    ...def,
    engine: 'external',
    external: {
      connection: 'c1',
      model: 'ventas',
      first_token_timeout_ms: 3000,
      error_message: 'Perdón, ¿me repetís?',
      max_errors: 3,
      on_errors: 'transfer:a1',
    },
    handoff: {
      areas: [{ area_id: 'a1', when: '' }],
      hold_music: { enabled: true, track: 'default', volume: 0.3 },
    },
  };

  it('ida y vuelta conserva el motor, la configuracion y la derivacion', () => {
    expect(stableJson(fromDraft(toDraft(ext as never)))).toBe(stableJson(ext));
  });

  it('sin modelo ni prompt no los manda; los defaults si', () => {
    const d = toDraft({ ...def, engine: 'external', external: { connection: 'c1' } } as never);
    expect(fromDraft(d).external).toEqual({
      connection: 'c1',
      first_token_timeout_ms: 4000,
      error_message: 'Disculpá, se me cortó. ¿Me lo repetís?',
      max_errors: 2,
      on_errors: 'hang_up',
    });
  });

  it('apagado (otro motor) no manda external; con external no manda llm ni generation', () => {
    const d = toDraft(ext as never);
    expect(fromDraft({ ...d, engine: 'classic' }).external).toBeUndefined();
    const withLlm = toDraft({ ...ext, generation: { params: { temperature: 0.2 } } } as never);
    expect(fromDraft(withLlm).generation).toBeUndefined();
  });

  it('el resumen por email no agrega un dato de telefono', () => {
    const d = toDraft({ ...ext, fields: {} } as never);
    expect(withPhoneField(d).fields).toHaveLength(0);
  });

  it('los errores de external van a la seccion Tu propio agente', () => {
    const d = toDraft(ext as never);
    expect(errorTarget(d, 'external.connection')).toEqual({ section: 'externo' });
    expect(pathLabel(d, 'external.on_errors')).toBe('Tu propio agente › después de los errores');
  });
});
