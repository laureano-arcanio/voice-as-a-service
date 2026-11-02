import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Client, User } from '@/api/types';
import { ADMIN, jsonResponse, renderWithProviders } from '@/test/render';
import { RegistrationCard } from './RegistrationCard';

const CLIENT = {
  id: 'c-1',
  name: 'Panadería Doña Rosa',
  slug: 'panaderia',
  created_via: 'signup',
  industry: 'gastronomia',
  website: 'https://rosa.com.ar',
  created_at: '2026-10-30T12:00:00Z',
} as Client;

const USER = (over: Partial<User>) =>
  ({
    id: 'u',
    email: 'otra@example.com',
    name: 'Otra',
    role: 'client',
    client_id: 'c-1',
    active: true,
    phone: null,
    phone_verified_at: null,
    created_at: '2026-10-31T12:00:00Z',
    last_login_at: null,
    ...over,
  }) as User;

function mockApi(users: User[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(String(input));
      if (req.url.includes('/onboarding/industries')) {
        return jsonResponse([{ id: 'gastronomia', label: 'Gastronomía', template_id: 'x' }]);
      }
      return jsonResponse(users);
    }),
  );
}

describe('RegistrationCard', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('muestra la empresa y los datos del primer usuario creado, no los de los siguientes', async () => {
    // El listado de la API viene por email: el primero alfabético no es el que se registró.
    mockApi([
      USER({ id: 'u2' }),
      USER({
        id: 'u1',
        email: 'rosa@example.com',
        name: 'Rosa',
        phone: '+5491155551234',
        phone_verified_at: '2026-10-30T13:00:00Z',
        created_at: '2026-10-30T12:00:00Z',
      }),
    ]);
    renderWithProviders(<RegistrationCard client={CLIENT} />, { me: ADMIN });

    expect(await screen.findByText('rosa@example.com')).toBeInTheDocument();
    expect(screen.getByText('Panadería Doña Rosa')).toBeInTheDocument();
    expect(screen.getByText('Rosa')).toBeInTheDocument();
    expect(screen.getByText('+5491155551234')).toBeInTheDocument();
    expect(screen.getByText('Verificado')).toBeInTheDocument();
    expect(await screen.findByText('Gastronomía')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'https://rosa.com.ar' })).toBeInTheDocument();
    expect(screen.queryByText('otra@example.com')).not.toBeInTheDocument();
  });

  it('sin celular ni rubro muestra guiones, y el celular sin verificar se marca', async () => {
    mockApi([USER({ phone: '+5491155551234' })]);
    const { unmount } = renderWithProviders(<RegistrationCard client={{ ...CLIENT, industry: '', website: '' }} />, {
      me: ADMIN,
    });
    expect(await screen.findByText('Sin verificar')).toBeInTheDocument();
    expect(screen.getAllByText('–')).toHaveLength(2);
    unmount();

    mockApi([USER({})]);
    renderWithProviders(<RegistrationCard client={{ ...CLIENT, industry: '', website: '' }} />, { me: ADMIN });
    expect(await screen.findByText('otra@example.com')).toBeInTheDocument();
    expect(screen.getAllByText('–')).toHaveLength(3);
  });
});
