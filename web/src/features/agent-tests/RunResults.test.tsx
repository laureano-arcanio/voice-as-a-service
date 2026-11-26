import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '@/test/render';
import { RunResults } from './RunResults';
import type { CaseResult } from './api';

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
      repetitions: [
        {
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
        },
      ],
    },
  ],
};

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
});
