import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { ApiContentCard } from './ApiContentCard';

function mockApi(initial = { enabled: true, retention_days: 30 as number | null }) {
  const puts: unknown[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const { pathname } = new URL(req.url);
      if (pathname === '/api/v1/clients/c-1/api-content') {
        if (req.method === 'PUT') {
          const body = await req.json();
          puts.push(body);
          return jsonResponse({ ...body, stored_bytes: 1_258_291, stored_requests: 42 });
        }
        return jsonResponse({ ...initial, stored_bytes: 1_258_291, stored_requests: 42 });
      }
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return puts;
}

afterEach(() => vi.unstubAllGlobals());

describe('Contenido de la API (tarjeta)', () => {
  it('carga el ajuste con lo ocupado y guarda el cambio a Indefinido como null', async () => {
    const puts = mockApi();
    renderWithProviders(<ApiContentCard clientId="c-1" />, { me: CLIENT_USER });
    const sw = await screen.findByRole('switch', { name: /Guardar el contenido de la API/ });
    expect(sw).toBeChecked();
    expect(screen.getByText(/42 pedidos, 1,2 MB/)).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /Se borra a los/ })).toHaveValue('30 días');
    expect(screen.queryByText(/No vence/)).not.toBeInTheDocument();
    const save = screen.getByRole('button', { name: 'Guardar' });
    expect(save).toBeDisabled();
    await userEvent.click(screen.getByRole('textbox', { name: /Se borra a los/ }));
    await userEvent.click(await screen.findByRole('option', { name: 'Indefinido', hidden: true }));
    expect(screen.getByText('No vence: ocupa disco hasta que lo borres.')).toBeInTheDocument();
    await userEvent.click(save);
    await waitFor(() => expect(puts).toEqual([{ enabled: true, retention_days: null }]));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Guardar' })).toBeDisabled());
  });

  it('apaga el guardado y manda el vencimiento que ya tenía', async () => {
    const puts = mockApi({ enabled: true, retention_days: 90 });
    renderWithProviders(<ApiContentCard clientId="c-1" />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('switch', { name: /Guardar el contenido de la API/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(puts).toEqual([{ enabled: false, retention_days: 90 }]));
  });

  it('un cliente con vencimiento indefinido lo ve elegido y avisa que no vence', async () => {
    mockApi({ enabled: false, retention_days: null });
    renderWithProviders(<ApiContentCard clientId="c-1" />, { me: CLIENT_USER });
    expect(await screen.findByRole('textbox', { name: /Se borra a los/ })).toHaveValue('Indefinido');
    expect(screen.getByText(/No vence/)).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: /Guardar el contenido de la API/ })).not.toBeChecked();
  });
});
