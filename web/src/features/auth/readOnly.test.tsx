import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Agent, Client, PhoneNumber } from '@/api/types';
import { ReadOnlyBanner } from '@/components/ReadOnlyBanner';
import { NewCallForm } from '@/features/calls/NewCallForm';
import { ApiKeysSection } from '@/features/clients/ApiKeysSection';
import { ADMIN, CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';

const CLIENT: Client = {
  id: 'c-1',
  name: 'Acme',
  slug: 'acme',
  active: true,
  tier: { id: 't-1', name: 'Pyme' },
  retention_days: null,
  created_at: '2026-10-01T12:00:00Z',
  effective_retention_days: 90,
  effective_max_call_seconds: 900,
};

const AGENT = {
  id: 'ag-1',
  client_id: 'c-1',
  name: 'Ventas',
  voice: 'sofia',
  archived: false,
} as Agent;

const NUMBER = { id: 'n-1', client_id: 'c-1', e164: '+541152630861', label: '' } as PhoneNumber;

interface Seen {
  method: string;
  path: string;
  headers: Headers;
}

function mockApi(routes: Record<string, () => Response>) {
  const seen: Seen[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const path = new URL(req.url).pathname;
      seen.push({ method: req.method, path, headers: req.headers });
      const route = routes[`${req.method} ${path}`];
      return route ? route() : jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return seen;
}

afterEach(() => vi.unstubAllGlobals());

describe('cuenta en solo lectura', () => {
  it('cliente inactivo: aviso arriba y sin crear API keys', async () => {
    mockApi({
      'GET /api/v1/clients/c-1': () => jsonResponse({ ...CLIENT, active: false }),
      'GET /api/v1/clients/c-1/api-keys': () => jsonResponse([]),
    });
    renderWithProviders(
      <>
        <ReadOnlyBanner />
        <ApiKeysSection clientId="c-1" />
      </>,
      { me: CLIENT_USER },
    );
    expect(await screen.findByText('Cuenta en solo lectura')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Nueva API key/ })).toHaveAttribute('data-disabled', 'true');
  });

  it('cliente activo y admin: sin aviso', async () => {
    const seen = mockApi({ 'GET /api/v1/clients/c-1': () => jsonResponse(CLIENT) });
    renderWithProviders(<ReadOnlyBanner />, { me: CLIENT_USER });
    await waitFor(() => expect(seen.some((r) => r.path === '/api/v1/clients/c-1')).toBe(true));
    expect(screen.queryByText('Cuenta en solo lectura')).not.toBeInTheDocument();

    const admin = mockApi({});
    renderWithProviders(<ReadOnlyBanner />, { me: ADMIN });
    expect(screen.queryByText('Cuenta en solo lectura')).not.toBeInTheDocument();
    expect(admin.some((r) => r.path.startsWith('/api/v1/clients'))).toBe(false);
  });

  it('cliente inactivo: no deja llamar', async () => {
    mockApi({
      'GET /api/v1/clients/c-1': () => jsonResponse({ ...CLIENT, active: false }),
      'GET /api/v1/agents': () => jsonResponse([AGENT]),
      'GET /api/v1/phone-numbers': () => jsonResponse([NUMBER]),
      'GET /api/v1/voices': () => jsonResponse([]),
    });
    renderWithProviders(<NewCallForm fixedAgent={AGENT} />, { me: CLIENT_USER });
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Llamar/ })).toHaveAttribute('data-disabled', 'true'),
    );
  });
});

describe('nueva llamada', () => {
  it('cliente sin numero propio: avisa y no deja hacer salientes', async () => {
    mockApi({
      'GET /api/v1/clients/c-1': () => jsonResponse(CLIENT),
      'GET /api/v1/agents': () => jsonResponse([AGENT]),
      'GET /api/v1/phone-numbers': () => jsonResponse([]),
      'GET /api/v1/voices': () => jsonResponse([]),
    });
    renderWithProviders(<NewCallForm fixedAgent={AGENT} />, { me: CLIENT_USER });
    expect(await screen.findByText(/salen con un número de tu cuenta/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Llamar/ })).toHaveAttribute('data-disabled', 'true');
  });

  it('manda Idempotency-Key y explica el 409 no_caller_id', async () => {
    const seen = mockApi({
      'GET /api/v1/agents': () => jsonResponse([AGENT]),
      'GET /api/v1/clients': () => jsonResponse([CLIENT]),
      'GET /api/v1/phone-numbers': () => jsonResponse([]),
      'GET /api/v1/voices': () => jsonResponse([]),
      'POST /api/v1/calls': () =>
        jsonResponse({ detail: 'El cliente no tiene un número propio', code: 'no_caller_id' }, 409),
    });
    renderWithProviders(<NewCallForm fixedAgent={AGENT} />, { me: ADMIN });
    await userEvent.type(screen.getByLabelText('Teléfono'), '+5491155551234');
    await userEvent.click(screen.getByRole('button', { name: /Llamar/ }));
    expect(await screen.findByText('Asigná un número al cliente para hacer salientes.')).toBeInTheDocument();
    const posts = seen.filter((r) => r.method === 'POST');
    expect(posts).toHaveLength(1);
    expect(posts[0].headers.get('Idempotency-Key')).toMatch(/^[0-9a-f-]{36}$/);

    // Con respuesta (aunque sea error) el reintento lleva otra clave.
    await userEvent.click(screen.getByRole('button', { name: /Llamar/ }));
    await waitFor(() => expect(seen.filter((r) => r.method === 'POST')).toHaveLength(2));
    const [a, b] = seen.filter((r) => r.method === 'POST');
    expect(a.headers.get('Idempotency-Key')).not.toBe(b.headers.get('Idempotency-Key'));
  });
});
