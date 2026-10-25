import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { jsonResponse, renderWithProviders } from '@/test/render';
import { OAuthConsentPage } from './OAuthConsentPage';

const ME = {
  id: 'u1',
  email: 'ana@acme.com',
  name: 'Ana',
  role: 'client' as const,
  client_id: 'c1',
  client_name: 'Acme',
};
const QUERY = 'response_type=code&client_id=mcp_1&state=xyz&code_challenge=abc&code_challenge_method=S256';
const VALID = {
  valid: true,
  client_name: 'Claude',
  client_uri: 'https://claude.ai',
  verified: true,
  redirect_host: 'claude.ai',
  scope: 'mcp',
  resource: 'https://app.atentina.com.ar/mcp',
  needs_client: false,
  client_id: 'c1',
  client_name_tenant: 'Acme',
};

function mockApi(info: object, redirect = 'https://claude.ai/cb?code=k&state=xyz') {
  const posted: unknown[] = [];
  const requested: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(String(input));
      if (req.method === 'POST') {
        posted.push(await req.clone().json());
        return jsonResponse({ redirect_to: redirect });
      }
      requested.push(new URL(req.url).search);
      return jsonResponse(info);
    }),
  );
  return { posted, requested };
}

describe('OAuthConsentPage', () => {
  const assign = vi.fn();
  beforeEach(() => {
    vi.stubGlobal('location', { ...window.location, assign, origin: 'http://localhost' });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    assign.mockReset();
  });

  it('muestra qué agente pide acceso y al permitir vuelve a la app con el código', async () => {
    const { posted, requested } = mockApi(VALID);
    renderWithProviders(<OAuthConsentPage />, { me: ME, path: `/oauth/consent?${QUERY}` });
    expect(await screen.findByText('Conectar Claude')).toBeInTheDocument();
    expect(screen.getByText('Identificado por https://claude.ai')).toBeInTheDocument();
    expect(requested[0]).toContain('client_id=mcp_1');
    await userEvent.click(screen.getByRole('button', { name: 'Permitir acceso' }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith('https://claude.ai/cb?code=k&state=xyz'));
    expect(posted[0]).toMatchObject({ approve: true, params: { client_id: 'mcp_1', state: 'xyz' } });
  });

  it('cancelar devuelve el rechazo a la app', async () => {
    const { posted } = mockApi(VALID, 'https://claude.ai/cb?error=access_denied');
    renderWithProviders(<OAuthConsentPage />, { me: ME, path: `/oauth/consent?${QUERY}` });
    await userEvent.click(await screen.findByRole('button', { name: 'Cancelar' }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith('https://claude.ai/cb?error=access_denied'));
    expect(posted[0]).toMatchObject({ approve: false });
  });

  it('un admin puede conectar el agente a toda la plataforma', async () => {
    const posted: unknown[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const req = input instanceof Request ? input : new Request(String(input));
        if (req.method === 'POST') {
          posted.push(await req.clone().json());
          return jsonResponse({ redirect_to: 'https://claude.ai/cb?code=k' });
        }
        if (new URL(req.url).pathname.endsWith('/clients')) return jsonResponse([{ id: 'c1', name: 'Acme' }]);
        return jsonResponse({ ...VALID, needs_client: true, client_id: null, client_name_tenant: null });
      }),
    );
    const admin = { ...ME, role: 'admin' as const, client_id: null, client_name: null };
    renderWithProviders(<OAuthConsentPage />, { me: admin, path: `/oauth/consent?${QUERY}` });
    await userEvent.click(await screen.findByRole('textbox', { name: 'Cliente' }));
    await userEvent.type(screen.getByRole('textbox', { name: 'Cliente' }), 'Toda');
    await userEvent.click(await screen.findByText('Toda la plataforma (admin)'));
    expect(screen.getByText(/actuar como admin en toda la plataforma/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Permitir acceso' }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith('https://claude.ai/cb?code=k'));
    expect(posted[0]).toMatchObject({ approve: true, platform: true });
    expect((posted[0] as { client_id?: string }).client_id).toBeUndefined();
  });

  it('un pedido inválido explica qué pasó y no ofrece permitir', async () => {
    mockApi({ valid: false, error: 'invalid_request', error_description: 'redirect_uri no registrado.' });
    renderWithProviders(<OAuthConsentPage />, { me: ME, path: `/oauth/consent?${QUERY}` });
    expect(await screen.findByText('No se puede conectar el agente')).toBeInTheDocument();
    expect(screen.getByText(/redirect_uri no registrado/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Permitir acceso' })).not.toBeInTheDocument();
  });
});
