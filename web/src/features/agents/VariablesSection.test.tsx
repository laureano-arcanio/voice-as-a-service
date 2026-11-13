import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CATALOG } from '@/components/variables/fixtures';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { type Draft, toDraft } from './draft';
import { VariablesSection } from './VariablesSection';

const DEF = {
  id: 'a',
  version: 1,
  agent: { name: 'Sofía', language: 'es-AR' },
  prompt: 'Sos Sofía. Saludá con {{saludo}} y hoy es {{today}}.',
  first_message: '',
  variables: [{ name: 'deuda', default: '1000', description: 'Lo que debe' }],
  analysis: { summary: true, instructions: '', fields: [], outcomes: [] },
};

function Harness({ initial = toDraft(DEF) }: { initial?: Draft }) {
  const [draft, setDraft] = useState(initial);
  return <VariablesSection draft={draft} update={setDraft} />;
}

function mockApi() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL((input instanceof Request ? input : new Request(input)).url);
      if (url.pathname === '/api/v1/variables/catalog') return jsonResponse(CATALOG);
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('VariablesSection', () => {
  it('valida el nombre en vivo, como el backend', async () => {
    mockApi();
    renderWithProviders(<Harness />, { me: CLIENT_USER });
    const name = await screen.findByLabelText('Nombre de la variable 1');
    await userEvent.clear(name);
    await userEvent.type(name, 'Deuda-1');
    expect(await screen.findByText(/Minúsculas, números y _/)).toBeInTheDocument();
    await userEvent.clear(name);
    await userEvent.type(name, 'today');
    expect(await screen.findByText('today es del sistema.')).toBeInTheDocument();
  });

  it('avisa las usadas sin declarar y las declara con "Declarar"', async () => {
    mockApi();
    renderWithProviders(<Harness />, { me: CLIENT_USER });
    // Las del sistema no se avisan.
    const warning = await screen.findByTestId('undeclared-variables');
    expect(warning).toHaveTextContent('Usadas en el prompt sin declarar: {{saludo}}');
    await waitFor(() => expect(warning).not.toHaveTextContent('today'));
    expect(screen.getByTestId('unused-variables')).toHaveTextContent('Declaradas sin usar: {{deuda}}');
    await userEvent.click(screen.getByRole('button', { name: 'Declarar' }));
    await waitFor(() => expect(screen.queryByTestId('undeclared-variables')).toBeNull());
    expect(screen.getByLabelText('Nombre de la variable 2')).toHaveValue('saludo');
  });

  it('agrega y quita filas', async () => {
    mockApi();
    renderWithProviders(<Harness />, { me: CLIENT_USER });
    await screen.findByLabelText('Nombre de la variable 1');
    await userEvent.click(screen.getByRole('button', { name: 'Agregar variable' }));
    expect(await screen.findByLabelText('Nombre de la variable 2')).toHaveValue('variable_2');
    await userEvent.click(screen.getByRole('button', { name: 'Quitar la variable 1' }));
    await waitFor(() => expect(screen.queryByLabelText('Nombre de la variable 2')).toBeNull());
    expect(screen.getByLabelText('Nombre de la variable 1')).toHaveValue('variable_2');
  });
});
