import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { isGroup, navFor, navItemsFor } from '@/components/nav';
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
    expect(client).toContain('Contactos');
    expect(client).not.toContain('Clientes');
    expect(client).not.toContain('Tiers');
    expect(client).not.toContain('Usuarios');
    expect(client).not.toContain('Números');
    const admin = navItemsFor('admin').map((i) => i.label);
    expect(admin).toEqual(expect.arrayContaining(['Clientes', 'Números', 'Tiers', 'Usuarios']));
    expect(admin).toContain('Contactos');
    expect(admin).not.toContain('Mi cuenta');
    expect(admin).not.toContain('Consumos');
  });

  it('agrupa el menú y saca los grupos vacíos del rol', () => {
    const shape = (role: 'admin' | 'client') =>
      navFor(role).map((e) =>
        isGroup(e) ? `${e.label}: ${e.items.map((i) => i.label).join(', ')}` : e.label,
      );
    expect(shape('client')).toEqual([
      'Inicio',
      'Conversaciones',
      'Agentes: Mis agentes, Herramientas, Modelos, Playground, Voces',
      'Canales: WhatsApp, Llamadas, Campañas',
      'Organización: Contactos, Equipo',
      'Developers: API keys, Uso de la API',
      'Cuenta: Mi cuenta, Plan, Consumos',
    ]);
    const admin = shape('admin');
    expect(admin).toContain('Agentes: Mis agentes, Herramientas, Playground, Voces');
    expect(admin.some((e) => e.startsWith('Configuración'))).toBe(false);
    expect(admin).toContain('Developers: Uso de la API');
    expect(admin.some((e) => e.startsWith('Cuenta'))).toBe(false);
    expect(admin.slice(-5)).toEqual(['Clientes', 'Números', 'Tiers', 'Cobros', 'Usuarios']);
  });
});
