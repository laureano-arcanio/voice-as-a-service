import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ADMIN_NAV, CLIENT_NAV, isGroup, navFor, navItemsFor } from '@/components/nav';
import { ADMIN, CLIENT_USER, renderWithProviders } from '@/test/render';
import { RequireAdminArea, RequireAuth, RequireClientArea } from './guards';

const areaRoutes = (guard: 'client' | 'admin') => {
  const Guard = guard === 'client' ? RequireClientArea : RequireAdminArea;
  return [
    { path: '/admin', element: <p>administración</p> },
    { path: '/', element: <p>inicio del cliente</p> },
    {
      path: '/area',
      element: (
        <Guard>
          <p>contenido</p>
        </Guard>
      ),
    },
  ];
};

describe('RequireClientArea', () => {
  it('un admin sin cliente activo va a /admin', async () => {
    const { router } = renderWithProviders(<></>, { me: ADMIN, path: '/area', routes: areaRoutes('client') });
    expect(await screen.findByText('administración')).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/admin');
    expect(screen.queryByText('contenido')).not.toBeInTheDocument();
  });

  it('el cliente ve el panel', () => {
    renderWithProviders(<></>, { me: CLIENT_USER, path: '/area', routes: areaRoutes('client') });
    expect(screen.getByText('contenido')).toBeInTheDocument();
  });

  it('un admin en soporte (rol client) ve el panel del cliente', () => {
    renderWithProviders(<></>, {
      me: { ...CLIENT_USER, support: true },
      path: '/area',
      routes: areaRoutes('client'),
    });
    expect(screen.getByText('contenido')).toBeInTheDocument();
  });
});

describe('RequireAdminArea', () => {
  it('el admin ve la administración', () => {
    renderWithProviders(<></>, { me: ADMIN, path: '/area', routes: areaRoutes('admin') });
    expect(screen.getByText('contenido')).toBeInTheDocument();
  });

  it('el usuario de un cliente vuelve a /', async () => {
    const { router } = renderWithProviders(<></>, {
      me: CLIENT_USER,
      path: '/area',
      routes: areaRoutes('admin'),
    });
    expect(await screen.findByText('inicio del cliente')).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/');
    expect(screen.queryByText('contenido')).not.toBeInTheDocument();
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

describe('navegación por área', () => {
  it('el cliente no ve Clientes, Tiers ni Usuarios', () => {
    const client = navItemsFor('client').map((i) => i.label);
    expect(client).toContain('Mi cuenta');
    expect(client).toContain('Consumos');
    expect(client).toContain('Contactos');
    for (const l of ['Clientes', 'Tiers', 'Usuarios', 'Números', 'Cobros']) expect(client).not.toContain(l);
    expect(navItemsFor('client').every((i) => !i.to.startsWith('/admin'))).toBe(true);
  });

  it('la administración solo tiene pantallas de la plataforma, todas bajo /admin', () => {
    const items = navItemsFor('admin');
    expect(items.every((i) => i.to.startsWith('/admin'))).toBe(true);
    const admin = items.map((i) => i.label);
    expect(admin).toEqual(
      expect.arrayContaining(['Clientes', 'Números', 'Tiers', 'Cobros', 'Usuarios', 'Agentes']),
    );
    for (const l of ['Mi cuenta', 'Consumos', 'Contactos', 'Equipo']) expect(admin).not.toContain(l);
  });

  it('navFor devuelve el menú del área', () => {
    expect(navFor('admin')).toBe(ADMIN_NAV);
    expect(navFor('client')).toBe(CLIENT_NAV);
  });

  it('agrupa el menú del cliente', () => {
    const shape = navFor('client').map((e) =>
      isGroup(e) ? `${e.label}: ${e.items.map((i) => i.label).join(', ')}` : e.label,
    );
    expect(shape).toEqual([
      'Inicio',
      'Reportes',
      'Conversaciones',
      'Agentes: Mis agentes, Herramientas, Secretos, Modelos, Playground, Voces',
      'Canales: WhatsApp, Llamadas, Campañas',
      'Organización: Contactos, Equipo',
      'Developers: API keys, Uso de la API',
      'Cuenta: Mi cuenta, Plan, Consumos',
    ]);
  });

  it('el menú de administración es plano y en orden', () => {
    expect(navFor('admin').map((e) => e.label)).toEqual([
      'Inicio',
      'Reportes',
      'Conversaciones',
      'Agentes',
      'Uso de la API',
      'Clientes',
      'Números',
      'Tiers',
      'Cobros',
      'Usuarios',
    ]);
  });
});
