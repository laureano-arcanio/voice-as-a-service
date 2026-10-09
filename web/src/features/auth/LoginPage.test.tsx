import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { jsonResponse, renderWithProviders } from '@/test/render';
import { LoginPage } from './LoginPage';

function mockFetch(handler: (url: string, init: Request) => Response) {
  const fn = vi.fn((input: RequestInfo | URL) => {
    const req = input instanceof Request ? input : new Request(String(input));
    return Promise.resolve(handler(new URL(req.url).pathname, req));
  });
  vi.stubGlobal('fetch', fn);
  return fn;
}

describe('LoginPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('pide email y clave', async () => {
    renderWithProviders(<LoginPage />, { me: null });
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Clave')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }));
    expect(await screen.findByText('Ingresá un email válido')).toBeInTheDocument();
  });

  it('prellena el email que viene en la URL (links de los mails)', () => {
    renderWithProviders(<LoginPage />, { me: null, path: '/login?email=ana%2Bventas%40acme.com' });
    expect(screen.getByLabelText('Email')).toHaveValue('ana+ventas@acme.com');
    expect(screen.getByLabelText('Clave')).toHaveFocus();
  });

  it('muestra credenciales incorrectas y demasiados intentos', async () => {
    let status = 401;
    mockFetch(() =>
      status === 401
        ? jsonResponse({ detail: 'Email o clave incorrectos', code: 'invalid_credentials' }, 401)
        : jsonResponse({ detail: 'Demasiados intentos.', code: 'too_many_attempts' }, 429),
    );
    renderWithProviders(<LoginPage />, { me: null });
    await userEvent.type(screen.getByLabelText('Email'), 'ana@acme.com');
    await userEvent.type(screen.getByLabelText('Clave'), 'mala-clave');
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Email o clave incorrectos.');

    status = 429;
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Demasiados intentos'));
  });

  it('con sesion abierta va al inicio', async () => {
    const fetch = mockFetch(() => jsonResponse({}));
    const { router } = renderWithProviders(<LoginPage />, {
      me: { id: '1', email: 'a@b.com', name: '', role: 'admin', client_id: null, client_name: null },
      path: '/login',
      routes: [
        { path: '/login', element: <LoginPage /> },
        { path: '/', element: <p>inicio</p> },
      ],
    });
    expect(await screen.findByText('inicio')).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/');
    expect(fetch).not.toHaveBeenCalled();
  });
});
