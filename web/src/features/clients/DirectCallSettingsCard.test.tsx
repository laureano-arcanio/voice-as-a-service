import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Me } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { DirectCallSettingsCard } from './DirectCallSettingsCard';

const PLAN = (direct: boolean) => ({
  client_id: 'c-1',
  tier_name: direct ? 'Sucursal' : 'Free',
  free: !direct,
  features: {
    direct_calls: {
      enabled: direct,
      reason: direct ? null : 'Está en los planes Mostrador, Sucursal y Red.',
    },
  },
});

function mockApi({ notice = false, direct = true } = {}) {
  const puts: unknown[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const { pathname } = new URL(req.url);
      if (pathname === '/api/v1/plan/features') return jsonResponse(PLAN(direct));
      if (pathname === '/api/v1/clients/c-1/direct-call-settings') {
        if (req.method === 'PUT') {
          const body = await req.json();
          puts.push(body);
          return jsonResponse(body);
        }
        return jsonResponse({ recording_notice: notice });
      }
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return puts;
}

afterEach(() => vi.unstubAllGlobals());

describe('Mi cuenta: llamadas del equipo', () => {
  it('prende el aviso de grabación y avisa que grabar es responsabilidad del cliente', async () => {
    const puts = mockApi();
    renderWithProviders(<DirectCallSettingsCard clientId="c-1" />, { me: CLIENT_USER });
    const sw = await screen.findByRole('switch', { name: /Avisar que la llamada se graba/ });
    expect(sw).not.toBeChecked();
    expect(screen.getByText(/se graban siempre/)).toBeInTheDocument();
    expect(screen.getByText(/responsabilidad de tu empresa/)).toBeInTheDocument();
    const save = screen.getByRole('button', { name: 'Guardar' });
    expect(save).toBeDisabled();
    await userEvent.click(sw);
    await userEvent.click(save);
    await waitFor(() => expect(puts).toEqual([{ recording_notice: true }]));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Guardar' })).toBeDisabled());
  });

  it('muestra el aviso prendido y lo apaga', async () => {
    const puts = mockApi({ notice: true });
    renderWithProviders(<DirectCallSettingsCard clientId="c-1" />, { me: CLIENT_USER });
    const sw = await screen.findByRole('switch', { name: /Avisar que la llamada se graba/ });
    expect(sw).toBeChecked();
    await userEvent.click(sw);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(puts).toEqual([{ recording_notice: false }]));
  });

  it('sin llamadas directas en el plan avisa y bloquea', async () => {
    mockApi({ direct: false });
    renderWithProviders(<DirectCallSettingsCard clientId="c-1" />, { me: CLIENT_USER });
    expect(await screen.findByText(/no incluye llamadas directas/)).toBeInTheDocument();
    expect(await screen.findByRole('switch', { name: /Avisar que la llamada se graba/ })).toBeDisabled();
  });

  it('un admin en soporte lo puede cambiar, como el resto de Mi cuenta (la API no lo corta)', async () => {
    const puts = mockApi();
    const support: Me = { ...CLIENT_USER, support: true };
    renderWithProviders(<DirectCallSettingsCard clientId="c-1" />, { me: support });
    const sw = await screen.findByRole('switch', { name: /Avisar que la llamada se graba/ });
    expect(sw).toBeEnabled();
    await userEvent.click(sw);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(puts).toEqual([{ recording_notice: true }]));
  });
});
