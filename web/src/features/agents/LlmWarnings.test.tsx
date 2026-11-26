import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '@/test/render';
import { LlmWarnings } from './LlmWarnings';

const WARNINGS = [
  { path: 'llm.stages.0.model', code: 'model_not_found', message: 'El modelo no existe en OpenRouter' },
  { path: 'llm.stages.1.connection', code: 'connection_test_failed', message: 'La última prueba falló' },
];

describe('LlmWarnings', () => {
  it('muestra el título y cada aviso con el nombre de su campo', () => {
    renderWithProviders(<LlmWarnings warnings={WARNINGS} label={(p) => p} onPick={() => {}} />);
    expect(screen.getByText('Avisos del modelo de lenguaje')).toBeInTheDocument();
    expect(screen.getByText(/El modelo no existe en OpenRouter/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'llm.stages.0.model' })).toBeInTheDocument();
  });

  it('al tocar el campo lleva al aviso con onPick', async () => {
    const onPick = vi.fn();
    renderWithProviders(<LlmWarnings warnings={WARNINGS} label={() => 'modelo'} onPick={onPick} />);
    await userEvent.click(screen.getAllByRole('button', { name: 'modelo' })[0]);
    expect(onPick).toHaveBeenCalledWith('llm.stages.0.model');
  });

  it('sin avisos no muestra nada', () => {
    renderWithProviders(<LlmWarnings warnings={[]} label={(p) => p} onPick={() => {}} />);
    expect(screen.queryByText('Avisos del modelo de lenguaje')).not.toBeInTheDocument();
  });
});
