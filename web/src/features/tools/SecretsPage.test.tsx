import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ClientSecret, Credential } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { slugify } from './credentials';
import { SecretsPage } from './SecretsPage';

const CRED: Credential = {
  id: 'cr-1',
  slug: 'api_crm',
  name: 'API del CRM',
  description: '',
  type: 'bearer',
  auth: { type: 'bearer', secret: 'API_CRM_TOKEN' },
  secret: 'API_CRM_TOKEN',
  secret_set: true,
  used_by: ['consultar_turnos'],
  created_at: '2026-10-27T10:00:00Z',
  updated_at: '2026-10-27T10:00:00Z',
};

const SECRET: ClientSecret = {
  name: 'API_CRM_TOKEN',
  description: 'API del CRM',
  last4: 'ab12',
  missing: false,
  used_by: ['consultar_turnos'],
  credentials: ['api_crm'],
  agents: [{ id: 'a-1', name: 'Sucursal Norte' }],
  created_at: '2026-10-27T10:00:00Z',
  updated_at: '2026-10-27T10:00:00Z',
};

const posts: { path: string; body: unknown }[] = [];

function mockApi() {
  posts.length = 0;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const path = new URL(req.url).pathname;
      if (req.method === 'POST') {
        const body: unknown = await req.json();
        posts.push({ path, body });
        return jsonResponse({ ...CRED, ...(body as object) }, 201);
      }
      if (path === '/api/v1/clients/c-1/credentials') return jsonResponse([CRED]);
      if (path === '/api/v1/clients/c-1/secrets') return jsonResponse([SECRET]);
      if (path === '/api/v1/plan/features')
        return jsonResponse({
          client_id: 'c-1',
          tier_name: 'Sucursal',
          free: false,
          features: { custom_tools: { enabled: true, reason: null } },
        });
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('SecretsPage', () => {
  it('lista credenciales y secretos sin valores, con quién los usa', async () => {
    mockApi();
    renderWithProviders(<SecretsPage />, { me: CLIENT_USER });
    const cred = (await screen.findByText('API del CRM', { selector: 'p' })).closest('tr')!;
    expect(within(cred).getByText('Bearer token')).toBeInTheDocument();
    expect(within(cred).getByRole('link', { name: 'consultar_turnos' })).toBeInTheDocument();
    const secret = screen.getByText('••••ab12').closest('tr')!;
    expect(within(secret).getByText('Credencial api_crm')).toBeInTheDocument();
    expect(within(secret).getByRole('link', { name: 'Sucursal Norte' })).toHaveAttribute(
      'href',
      '/agents/a-1',
    );
  });

  it('crea una credencial con el valor en un secreto nuevo', async () => {
    mockApi();
    renderWithProviders(<SecretsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Nueva credencial' }));
    await userEvent.type(await screen.findByLabelText('Nombre'), 'Agenda Médica');
    await userEvent.type(screen.getByLabelText('Token'), 'tok-123456789');
    await userEvent.click(screen.getByRole('button', { name: 'Crear credencial' }));
    await waitFor(() =>
      expect(posts).toEqual([
        {
          path: '/api/v1/clients/c-1/credentials',
          body: {
            slug: 'agenda_medica',
            name: 'Agenda Médica',
            description: '',
            auth: { type: 'bearer', secret: 'AGENDA_MEDICA_TOKEN' },
            value: 'tok-123456789',
          },
        },
      ]),
    );
  });

  it('slugify', () => {
    expect(slugify('API del CRM')).toBe('api_del_crm');
    expect(slugify('3 Sucursales')).toBe('api_3_sucursales');
  });
});
