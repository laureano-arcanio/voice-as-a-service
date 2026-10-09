import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { jsonResponse, renderWithProviders } from '@/test/render';
import { SetPasswordPage } from './SetPasswordPage';

const ME = {
  id: 'u1',
  email: 'ana@acme.com',
  name: 'Ana',
  role: 'client',
  client_id: 'c1',
  client_name: 'Acme',
};
const INFO = { email: 'ana@acme.com', name: 'Ana', client_name: 'Acme' };

function mockApi(check: () => Response, save: () => Response = () => jsonResponse(ME)) {
  const bodies: Record<string, unknown> = {};
  const fn = vi.fn(async (input: RequestInfo | URL) => {
    const req = input instanceof Request ? input : new Request(String(input));
    const path = new URL(req.url).pathname;
    bodies[path] = await req.clone().json();
    return path.endsWith('/check') ? check() : save();
  });
  vi.stubGlobal('fetch', fn);
  return bodies;
}

const routes = [
  { path: '/set-password', element: <SetPasswordPage /> },
  { path: '/', element: <p>inicio</p> },
];

describe('SetPasswordPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('muestra a quién es el link, valida y guarda la clave entrando al inicio', async () => {
    const bodies = mockApi(() => jsonResponse(INFO));
    const { router } = renderWithProviders(<SetPasswordPage />, {
      me: null,
      path: '/set-password?token=abc.def.ghi-123',
      routes,
    });
    expect(await screen.findByText('Acme · ana@acme.com')).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText('Clave nueva'), 'corta');
    await userEvent.type(screen.getByLabelText('Repetí la clave'), 'otra');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar y entrar' }));
    expect(await screen.findByText('Usá al menos 10 caracteres')).toBeInTheDocument();
    expect(screen.getByText('Las claves no coinciden')).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText('Clave nueva'));
    await userEvent.clear(screen.getByLabelText('Repetí la clave'));
    await userEvent.type(screen.getByLabelText('Clave nueva'), 'mi-clave-larga-1');
    await userEvent.type(screen.getByLabelText('Repetí la clave'), 'mi-clave-larga-1');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar y entrar' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(bodies['/api/v1/auth/password-setup']).toEqual({
      token: 'abc.def.ghi-123',
      password: 'mi-clave-larga-1',
    });
  });

  it('con el link vencido o usado avisa y ofrece ir a ingresar', async () => {
    mockApi(() => jsonResponse({ detail: 'El link venció o ya se usó.', code: 'invalid_setup_token' }, 422));
    renderWithProviders(<SetPasswordPage />, { me: null, path: '/set-password?token=viejo-123456' });
    expect(await screen.findByRole('alert')).toHaveTextContent('El link venció o ya se usó.');
    expect(screen.queryByLabelText('Clave nueva')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ir a ingresar' })).toHaveAttribute('href', '/login');
  });

  it('sin token no consulta a la API', async () => {
    const fn = vi.fn();
    vi.stubGlobal('fetch', fn);
    renderWithProviders(<SetPasswordPage />, { me: null, path: '/set-password' });
    expect(await screen.findByRole('alert')).toHaveTextContent('Falta el link del mail');
    expect(fn).not.toHaveBeenCalled();
  });
});
