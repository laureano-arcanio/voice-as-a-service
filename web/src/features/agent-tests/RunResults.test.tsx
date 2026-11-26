import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '@/test/render';
import { RunResults } from './RunResults';
import { fallbackCount, summaryText, type CaseResult, type Repetition, type VariantResult } from './api';

const REPETITION: Repetition = {
  text: 'Sale $130 por persona.',
  tool_calls: [{ name: 'salidas', arguments: {} }],
  handoff: null,
  status: 'active',
  failures: [
    {
      check: { type: 'datos_de_la_herramienta' },
      message: 'El importe «$130» no está en el resultado de la herramienta',
      span: '$130',
    },
  ],
  error: null,
  ms: 420,
  input_tokens: 10,
  output_tokens: 5,
  llm: {},
  tools: [{ name: 'salidas', result: '{"precio": 13500}', recorded: true }],
  passed: false,
};

const result: CaseResult = {
  case_id: 'c1',
  name: 'Salidas a Castelli',
  known_failure: false,
  variants: [
    {
      key: 'publicada',
      version: 3,
      passed: 0,
      total: 1,
      errors: 0,
      repetitions: [REPETITION],
    },
  ],
};

const respuesta = (fallback = true): Repetition => ({
  ...REPETITION,
  text: 'Sale a las 20:00.',
  failures: [],
  tools: [],
  passed: true,
  llm: fallback
    ? {
        provider: 'local',
        model: 'local-model',
        fallback_from: 'openrouter:vendor/model',
        fallback_reason: 'BadRequestError 400',
      }
    : { provider: 'openrouter', model: 'vendor/model' },
});

const variante = (over: Partial<VariantResult>): VariantResult => ({
  ...result.variants[0],
  ...over,
});

const unCaso = (variant: VariantResult): CaseResult => ({ ...result, variants: [variant] });

describe('RunResults', () => {
  it('resalta el span de la falla y cuenta pasa X/N', () => {
    renderWithProviders(<RunResults results={[result]} />);
    expect(screen.getByText('pasa 0/1')).toBeInTheDocument();
    expect(screen.getByTestId('check-span')).toHaveTextContent('$130');
    expect(screen.getByText(/El importe/)).toBeInTheDocument();
    expect(screen.getByText(/Herramientas: salidas/)).toBeInTheDocument();
  });

  it('sin resultados avisa', () => {
    renderWithProviders(<RunResults results={[]} />);
    expect(screen.getByText('Todavía no hay resultados.')).toBeInTheDocument();
  });

  it('una repetición de respaldo dice qué modelo contestó y por qué', () => {
    const variant = variante({ passed: 1, total: 1, repetitions: [respuesta()] });
    renderWithProviders(<RunResults results={[unCaso(variant)]} />);
    expect(
      screen.getByText(
        'Respaldo local (local-model) en lugar de openrouter:vendor/model: BadRequestError 400',
      ),
    ).toBeInTheDocument();
  });

  it('una variante con 3 de 5 respaldos muestra el badge con el motivo', () => {
    const variant = variante({
      passed: 3,
      total: 5,
      fallbacks: 3,
      fallback_reasons: { 'BadRequestError 400': 3 },
      repetitions: [],
    });
    renderWithProviders(<RunResults results={[unCaso(variant)]} />);
    expect(screen.getByText('3 de 5 las contestó el respaldo local (BadRequestError 400)')).toBeInTheDocument();
  });

  it('una corrida vieja sin fallbacks cuenta los respaldos de las repeticiones', () => {
    const variant = variante({
      passed: 5,
      total: 5,
      repetitions: [respuesta(), respuesta(), respuesta(), respuesta(false), respuesta(false)],
    });
    expect(fallbackCount(variant)).toBe(3);
    renderWithProviders(<RunResults results={[unCaso(variant)]} />);
    expect(screen.getByText('3 de 5 las contestó el respaldo local (BadRequestError 400)')).toBeInTheDocument();
  });

  it('el resumen de la lista suma los respaldos', () => {
    expect(
      summaryText({
        variants: [
          { key: 'publicada', passed: 5, total: 5, fallbacks: 5 },
          { key: 'borrador', passed: 4, total: 5 },
        ],
      }),
    ).toBe('Publicada: pasa 5/5 · 5 respaldo · Cambios sin guardar: pasa 4/5');
  });
});
