import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { navItemsFor } from '@/components/nav';
import { ADMIN, CLIENT_USER, renderWithProviders } from '@/test/render';
import { RequireAuth, RequireRole } from './guards';

describe('RequireRole', () => {
  it('deja pasar al rol pedido', () => {
    renderWithProviders(
      <RequireRole role="admin">
        <p>clientes</p>
      </RequireRole>,
      { me: ADMIN },
    );
    expect(screen.getByText('clientes')).toBeInTheDocument();
  });

  it('al usuario de un cliente le muestra sin acceso', () => {
    renderWithProviders(
      <RequireRole role="admin">
        <p>clientes</p>
      </RequireRole>,
      { me: CLIENT_USER },
    );
    expect(screen.queryByText('clientes')).not.toBeInTheDocument();
    expect(screen.getByText('Sin acceso')).toBeInTheDocument();
  });
});

describe('RequireAuth', () => {
  it('sin sesion manda a /login', async () => {
    const { router } = renderWithProviders(<></>, {
      me: null,
      path: '/agents',
      routes: [
        { path: '/login', element: <p>login</p> },
        {
          path: '/agents',
          element: (
            <RequireAuth>
              <p>agentes</p>
            </RequireAuth>
          ),
        },
      ],
    });
    expect(await screen.findByText('login')).toBeInTheDocument();
    expect(router.state.location.state).toMatchObject({ from: { pathname: '/agents' } });
  });
});

describe('navegación por rol', () => {
  it('el cliente no ve Clientes, Tiers ni Usuarios', () => {
    const client = navItemsFor('client').map((i) => i.label);
    expect(client).toContain('Mi cuenta');
    expect(client).toContain('Consumos');
    expect(client).not.toContain('Clientes');
    expect(client).not.toContain('Tiers');
    expect(client).not.toContain('Usuarios');
    expect(client).not.toContain('Números');
    const admin = navItemsFor('admin').map((i) => i.label);
    expect(admin).toEqual(expect.arrayContaining(['Clientes', 'Números', 'Tiers', 'Usuarios']));
    expect(admin).not.toContain('Mi cuenta');
    expect(admin).not.toContain('Consumos');
  });
});
