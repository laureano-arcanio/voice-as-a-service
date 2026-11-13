import { describe, expect, it } from 'vitest';
import {
  errorTarget,
  EXTERNAL_DEFAULTS,
  fromDraft,
  hasAnalysis,
  keepKeys,
  move,
  newField,
  newVariable,
  pathLabel,
  renameField,
  stableJson,
  toDraft,
  variableNameError,
  withPhoneField,
} from './draft';

// Como la devuelve el servidor (model_dump con exclude_none), con lo que maneja el editor.
const def = {
  id: 'demo',
  version: 3,
  agent: { name: 'Sofía', language: 'es-AR', voice: 'sofia' },
  prompt: '# Identidad\nSos Sofía.\n\n# Objetivo\nAgendar una demo con {{nombre}}.\n',
  first_message: 'Hola, ¿hablo con {{nombre}}?',
  first_message_audio: true,
  first_message_delay_ms: 300,
  variables: [
    { name: 'nombre', default: 'Ana', description: 'Nombre de la persona' },
    { name: 'deuda', default: '1000', description: '' },
  ],
  analysis: {
    summary: true,
    instructions: 'Extraé lo que la persona dijo.',
    fields: [
      { name: 'wants', label: 'Quiere', description: 'Quiere una demo', type: 'boolean' },
      { name: 'zone', description: 'Zona', type: 'choice', options: ['norte', 'sur'] },
    ],
    outcomes: [
      { id: 'ok', label: 'Agendado', when: { wants: true }, goal: true },
      { id: 'no', label: 'No', when: {}, goal: false },
    ],
  },
  record_audio: true,
};

describe('toDraft / fromDraft', () => {
  it('ida y vuelta con prompt, variables y análisis', () => {
    expect(stableJson(fromDraft(toDraft(def)))).toBe(stableJson(def));
    const d = toDraft(def);
    expect(d.prompt).toContain('# Objetivo');
    expect(d.variables.map((v) => [v.name, v.default])).toEqual([
      ['nombre', 'Ana'],
      ['deuda', '1000'],
    ]);
    expect(d.analysis.fields.map((f) => f.name)).toEqual(['wants', 'zone']);
    expect(d.analysis.outcomes.map((o) => o.id)).toEqual(['ok', 'no']);
  });

  it('el orden de los datos y las variables es el de la definición (listas)', () => {
    const d = toDraft({
      ...def,
      variables: [
        { name: 'zeta', default: '', description: '' },
        { name: 'alfa', default: '', description: '' },
      ],
      analysis: {
        ...def.analysis,
        fields: [
          { name: 'z', description: 'z', type: 'string' },
          { name: 'a', description: 'a', type: 'string' },
          { name: 'm', description: 'm', type: 'string' },
        ],
      },
    });
    expect(d.variables.map((v) => v.name)).toEqual(['zeta', 'alfa']);
    expect(d.analysis.fields.map((f) => f.name)).toEqual(['z', 'a', 'm']);
    const out = fromDraft(d) as { analysis: { fields: { name: string }[] } };
    expect(out.analysis.fields.map((f) => f.name)).toEqual(['z', 'a', 'm']);
  });

  it('sin datos, instrucciones ni resultados no va analysis', () => {
    const d = toDraft({ ...def, analysis: undefined });
    expect(d.analysis).toEqual({ summary: true, instructions: '', fields: [], outcomes: [] });
    expect(hasAnalysis(d.analysis)).toBe(false);
    expect(fromDraft(d)).not.toHaveProperty('analysis');
    expect(fromDraft({ ...d, analysis: { ...d.analysis, summary: false } })).not.toHaveProperty('analysis');
    // Con un dato, sí, con su resumen.
    expect(fromDraft(withPhoneField(d))).toMatchObject({ analysis: { summary: true } });
  });

  it('una variable a medio completar (sin nombre) no se guarda', () => {
    const d = toDraft(def);
    d.variables.push({ ...newVariable(d.variables), name: '  ' });
    const out = fromDraft(d) as { variables: { name: string }[] };
    expect(out.variables.map((v) => v.name)).toEqual(['nombre', 'deuda']);
  });

  it('record_audio: false no va (como la voz); true si', () => {
    expect(toDraft({ ...def, record_audio: false }).recordAudio).toBe(false);
    expect(fromDraft(toDraft({ ...def, record_audio: false }))).not.toHaveProperty('record_audio');
    expect(fromDraft(toDraft(def))).toMatchObject({ record_audio: true });
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
      analysis: {
        ...def.analysis,
        fields: [{ name: 'x', description: 'x', type: 'tipo_nuevo' }],
      },
    };
    expect(fromDraft(toDraft(d)).analysis).toMatchObject({ fields: [{ type: 'tipo_nuevo' }] });
  });

  it('withPhoneField: agrega telefono (tipo phone) al análisis si falta; no lo duplica', () => {
    const d = withPhoneField(toDraft(def));
    const phone = d.analysis.fields.at(-1)!;
    expect(phone).toMatchObject({ name: 'telefono', type: 'phone', label: 'Teléfono' });
    expect(withPhoneField(d).analysis.fields).toHaveLength(d.analysis.fields.length);
    const fields = (fromDraft(d) as { analysis: { fields: object[] } }).analysis.fields;
    expect(fields.at(-1)).toMatchObject({ name: 'telefono', type: 'phone' });
  });

  it('no_contact (baja por voz): sin marcar no va a la definición; marcado, ida y vuelta', () => {
    expect(toDraft(def).analysis.outcomes.map((o) => o.noContact)).toEqual([false, false]);
    expect(JSON.stringify(fromDraft(toDraft(def)))).not.toContain('no_contact');
    const flagged = {
      ...def,
      analysis: {
        ...def.analysis,
        outcomes: [
          { id: 'baja', label: 'Baja', when: { wants: false }, goal: false, no_contact: true },
          ...def.analysis.outcomes,
        ],
      },
    };
    const d = toDraft(flagged);
    expect(d.analysis.outcomes[0].noContact).toBe(true);
    expect(stableJson(fromDraft(d))).toBe(stableJson(flagged));
  });

  it('wa_session_minutes: sin valor no va (como record_audio); con valor, ida y vuelta', () => {
    expect(toDraft(def).waSessionMinutes).toBeNull();
    expect(fromDraft(toDraft(def))).not.toHaveProperty('wa_session_minutes');
    const d = toDraft({ ...def, wa_session_minutes: 2 });
    expect(d.waSessionMinutes).toBe(2);
    expect(fromDraft(d)).toMatchObject({ wa_session_minutes: 2 });
  });

  it('llm (conexiones BYOK): ida y vuelta, y sin etapas externas no va a la definición', () => {
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

  it('los errores de llm llevan a la sección Modelo de lenguaje', () => {
    const d = toDraft(def);
    expect(errorTarget(d, 'llm.stages.1.connection')).toEqual({ section: 'modelo' });
    expect(errorTarget(d, 'generation.params.temperature')).toEqual({ section: 'modelo' });
    expect(pathLabel(d, 'llm.stages.1.connection')).toBe('Modelo de lenguaje › etapa 2 › conexión');
  });

  it('sin voz, sin etiqueta y sin opciones fuera de choice: no van', () => {
    const d = toDraft(def);
    d.voice = '';
    d.analysis.fields[1] = { ...d.analysis.fields[1]!, type: 'string', label: '' };
    const out = fromDraft(d) as { agent: object; analysis: { fields: Record<string, unknown>[] } };
    expect(out.agent).not.toHaveProperty('voice');
    expect(out.analysis.fields[1]).not.toHaveProperty('options');
    expect(out.analysis.fields[1]).not.toHaveProperty('label');
  });

  it('el último resultado queda sin condiciones', () => {
    const d = toDraft(def);
    d.analysis.outcomes[1]!.conditions = [{ key: 'x', field: 'wants', value: false }];
    const out = fromDraft(d) as { analysis: { outcomes: { when: object }[] } };
    expect(out.analysis.outcomes[1]!.when).toEqual({});
  });
});

describe('edición', () => {
  it('renombrar un dato actualiza las condiciones que lo usan', () => {
    const d = renameField(toDraft(def), 0, 'quiere');
    expect(d.analysis.fields[0]!.name).toBe('quiere');
    expect(d.analysis.outcomes[0]!.conditions[0]!.field).toBe('quiere');
  });

  it('mover y datos nuevos', () => {
    const d = toDraft(def);
    expect(move(d.analysis.fields, 1, 0).map((f) => f.name)).toEqual(['zone', 'wants']);
    expect(move(d.analysis.fields, 0, -1)).toBe(d.analysis.fields);
    expect(newField(d.analysis.fields).name).toBe('dato_3');
    expect(newVariable(d.variables).name).toBe('variable_3');
  });

  it('conserva las claves de las filas al recargar la guardada', () => {
    const d = toDraft(def);
    const fresh = toDraft(def);
    const next = keepKeys(d, fresh);
    expect(next.analysis.fields.map((f) => f.key)).toEqual(d.analysis.fields.map((f) => f.key));
    expect(next.analysis.outcomes.map((o) => o.key)).toEqual(d.analysis.outcomes.map((o) => o.key));
    expect(next.variables.map((v) => v.key)).toEqual(d.variables.map((v) => v.key));
  });
});

describe('variables', () => {
  const catalog = {
    name_pattern: '^[a-z][a-z0-9_]{0,63}$',
    reserved: ['channel', 'today', 'now'],
    reserved_prefixes: ['call.', 'agent.', 'secrets.', 'fields.'],
  };

  it('valida el nombre como el backend', () => {
    expect(variableNameError('deuda', catalog, [])).toBeNull();
    expect(variableNameError('Deuda-1', catalog, [])).toMatch(/Minúsculas/);
    expect(variableNameError('today', catalog, [])).toMatch(/sistema/);
    expect(variableNameError('call.phone', catalog, [])).toMatch(/sistema/);
    expect(variableNameError('secrets.X', catalog, [])).toMatch(/sistema/);
    expect(variableNameError('deuda', catalog, ['deuda', 'otra'], 0)).toBeNull();
    expect(variableNameError('deuda', catalog, ['otra', 'deuda'], 0)).toBe('Repetida.');
    expect(variableNameError('', catalog, [])).toBe('Ponele un nombre.');
  });
});

describe('errores', () => {
  it('ubica la ruta en el formulario y la traduce', () => {
    const d = toDraft(def);
    expect(errorTarget(d, 'prompt')).toEqual({ section: 'prompt' });
    expect(errorTarget(d, 'first_message')).toEqual({ section: 'primer_mensaje' });
    expect(errorTarget(d, 'first_message_delay_ms')).toEqual({ section: 'primer_mensaje' });
    expect(errorTarget(d, 'variables.1.name')).toEqual({ section: 'variable', key: d.variables[1]!.key });
    expect(errorTarget(d, 'variables')).toEqual({ section: 'variables' });
    expect(errorTarget(d, 'analysis.instructions')).toEqual({ section: 'analisis' });
    expect(errorTarget(d, 'analysis.fields.1.description')).toEqual({
      section: 'dato',
      key: d.analysis.fields[1]!.key,
    });
    expect(errorTarget(d, 'analysis.outcomes.0.when')).toEqual({
      section: 'resultado',
      key: d.analysis.outcomes[0]!.key,
    });
    expect(errorTarget(d, 'analysis.outcomes.no.when')).toEqual({
      section: 'resultado',
      key: d.analysis.outcomes[1]!.key,
    });
    expect(errorTarget(d, 'agent.voice')).toEqual({ section: 'voz' });
    expect(errorTarget(d, '')).toBeNull();
    expect(pathLabel(d, 'prompt')).toBe('Prompt');
    expect(pathLabel(d, 'analysis.fields.1.description')).toBe(
      'Análisis al terminar › Datos › zone › descripción',
    );
    expect(pathLabel(d, 'analysis.outcomes.0.when')).toBe('Análisis al terminar › Agendado › condiciones');
    expect(pathLabel(d, 'variables.0.name')).toBe('Variables › nombre › nombre');
  });
});

describe('herramientas del cliente', () => {
  const withTools = {
    ...def,
    tools: [{ tool: 'consultar_turnos' }, { tool: 'reservar' }],
    tool_settings: { max_calls_per_turn: 2, limit_message: 'No pude.' },
  };

  it('ida y vuelta de {tool} y tool_settings; nunca manda engine', () => {
    const d = toDraft(withTools);
    expect(d.clientTools.map((g) => g.tool)).toEqual(['consultar_turnos', 'reservar']);
    expect(d.maxToolCallsPerTurn).toBe(2);
    expect(d.toolLimitMessage).toBe('No pude.');
    const out = fromDraft(d);
    expect(stableJson(out)).toBe(stableJson(withTools));
    expect(out).not.toHaveProperty('engine');
  });

  it('una definición vieja (engine, apps, confirm por agente) se lee sin eso', () => {
    const d = toDraft({
      ...def,
      engine: 'assistant',
      tools: [
        { app: 'gestion', tools: ['*'] },
        { tool: 'reservar', confirm: true },
      ],
    });
    const out = fromDraft(d);
    expect(out.tools).toEqual([{ tool: 'reservar' }]);
    expect(out).not.toHaveProperty('engine');
  });

  it('con tu propio agente no manda tools ni tool_settings', () => {
    const d = toDraft(withTools);
    const ext = fromDraft({ ...d, external: { connection: 'c1', ...EXTERNAL_DEFAULTS } });
    expect(ext).not.toHaveProperty('tools');
    expect(ext).not.toHaveProperty('tool_settings');
  });

  it('el error tools.N.tool nombra la herramienta', () => {
    const d = toDraft(withTools);
    expect(errorTarget(d, 'tools.1.tool')).toEqual({ section: 'herramientas' });
    expect(pathLabel(d, 'tools.1.tool')).toBe('Herramientas › reservar › herramienta');
    expect(errorTarget(d, 'tool_settings.limit_message')).toEqual({ section: 'herramientas' });
    expect(pathLabel(d, 'tool_settings.limit_message')).toBe('Herramientas › mensaje al llegar al tope');
  });
});

describe('tu propio agente (external)', () => {
  const ext = {
    ...def,
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

  it('ida y vuelta conserva la configuración y la derivación', () => {
    expect(stableJson(fromDraft(toDraft(ext as never)))).toBe(stableJson(ext));
  });

  it('sin modelo ni prompt no los manda; los defaults si', () => {
    const d = toDraft({ ...def, external: { connection: 'c1' } } as never);
    expect(fromDraft(d).external).toEqual({
      connection: 'c1',
      first_token_timeout_ms: 4000,
      error_message: 'Disculpá, se me cortó. ¿Me lo repetís?',
      max_errors: 2,
      on_errors: 'hang_up',
    });
  });

  it('apagado no manda external; con external no manda llm ni generation', () => {
    const d = toDraft(ext as never);
    expect(fromDraft({ ...d, external: null }).external).toBeUndefined();
    const withLlm = toDraft({ ...ext, generation: { params: { temperature: 0.2 } } } as never);
    expect(fromDraft(withLlm).generation).toBeUndefined();
  });

  it('el resumen por email no agrega un dato de teléfono', () => {
    const d = toDraft({ ...ext, analysis: { summary: true, fields: [], outcomes: [] } } as never);
    expect(withPhoneField(d).analysis.fields).toHaveLength(0);
  });

  it('los errores de external van a la sección Tu propio agente', () => {
    const d = toDraft(ext as never);
    expect(errorTarget(d, 'external.connection')).toEqual({ section: 'externo' });
    expect(pathLabel(d, 'external.on_errors')).toBe('Tu propio agente › después de los errores');
  });
});
