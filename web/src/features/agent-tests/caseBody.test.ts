import { describe, expect, it } from 'vitest';
import { addNoDice, buildCaseBody } from './caseBody';
import { summaryText, worsening, type CaseResult, type Preview } from './api';

const preview: Preview = {
  snapshot: { messages: [{ role: 'assistant', text: 'Hola' }], user_message: '¿Hay lugar?' },
  reply: {
    text: 'Hay lugar a las 12:00 por $13.500.',
    tool_calls: [{ name: 'salidas', arguments: { destino: 'Charata' } }],
    handoff: null,
    tool_results: ['{"hay_lugar": 1}'],
  },
  checks: [{ type: 'usa_herramienta', tool: 'salidas' }],
};

describe('buildCaseBody', () => {
  it('arma el body con los sugeridos, lo grabado y la copia de la conversación', () => {
    const body = buildCaseBody(preview, {
      conversationId: 'cv-1',
      messageIndex: 2,
      name: '  Salidas a Charata ',
      checks: [...preview.checks, { type: 'no_dice', text: 'asientos libres' }],
    });
    expect(body.name).toBe('Salidas a Charata');
    expect(body.conversation_id).toBe('cv-1');
    expect(body.message_index).toBe(2);
    expect(body.checks).toEqual([
      { type: 'usa_herramienta', tool: 'salidas' },
      { type: 'no_dice', text: 'asientos libres' },
    ]);
    expect(body.messages).toEqual(preview.snapshot.messages);
    expect(body.user_message).toBe('¿Hay lugar?');
    expect(body.tool_results).toEqual([
      { name: 'salidas', arguments: { destino: 'Charata' }, result: '{"hay_lugar": 1}' },
    ]);
  });
});

describe('addNoDice', () => {
  it('suma el texto seleccionado una vez y con los espacios colapsados', () => {
    const once = addNoDice([{ type: 'dice', text: 'hay lugar' }], '  asientos   libres ');
    expect(once).toEqual([
      { type: 'dice', text: 'hay lugar' },
      { type: 'no_dice', text: 'asientos libres' },
    ]);
    expect(addNoDice(once, 'asientos libres')).toEqual(once);
    expect(addNoDice(once, '   ')).toEqual(once);
  });
});

describe('resumen de una corrida', () => {
  const results: CaseResult[] = [
    {
      case_id: 'c1',
      name: 'Mejora',
      known_failure: false,
      variants: [
        { key: 'publicada', version: 1, passed: 2, total: 5, errors: 0, repetitions: [] },
        { key: 'borrador', version: 2, passed: 4, total: 5, errors: 0, repetitions: [] },
      ],
    },
    {
      case_id: 'c2',
      name: 'Empeora',
      known_failure: false,
      variants: [
        { key: 'publicada', version: 1, passed: 5, total: 5, errors: 0, repetitions: [] },
        { key: 'borrador', version: 2, passed: 3, total: 5, errors: 0, repetitions: [] },
      ],
    },
  ];

  it('nombra solo lo que empeora', () => {
    expect(worsening(results).map((c) => c.name)).toEqual(['Empeora']);
  });

  it('el resumen dice pasa X/N por variante', () => {
    expect(
      summaryText({
        variants: [
          { key: 'publicada', passed: 2, total: 5 },
          { key: 'borrador', passed: 4, total: 5 },
        ],
      }),
    ).toBe('Publicada: pasa 2/5 · Cambios sin guardar: pasa 4/5');
  });
});
