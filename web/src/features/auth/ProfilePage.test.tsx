import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { jsonResponse, renderWithProviders } from '@/test/render';
import { ProfilePage } from './ProfilePage';

const ME = {
  id: 'u1',
  email: 'ana@acme.com',
  name: 'Ana',
  role: 'client' as const,
  client_id: 'c1',
  client_name: 'Acme',
};
const SENT = {
  challenge: 'desafio.firmado.123',
  sent_to: 'ana@acme.com',
  expires_at: '2026-10-22T15:30:00Z',
};

function mockApi(responses: Record<string, () => Response>) {
  const bodies: Record<string, unknown> = {};
  const fn = vi.fn(async (input: RequestInfo | URL) => {
    const req = input instanceof Request ? input : new Request(String(input));
    const path = new URL(req.url).pathname;
    bodies[path] = await req
      .clone()
      .json()
      .catch(() => null);
    return (responses[path] ?? (() => jsonResponse(ME)))();
  });
  vi.stubGlobal('fetch', fn);
  return bodies;
}

async function typeCode(code: string) {
  const group = screen.getByRole('group', { name: 'Código del email' });
  await userEvent.click(within(group).getAllByRole('textbox')[0]);
  await userEvent.keyboard(code);
}

describe('ProfilePage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('cambia la clave con el código del email', async () => {
    const bodies = mockApi({ '/api/v1/auth/me/password/code': () => jsonResponse(SENT) });
    renderWithProviders(<ProfilePage />, { me: ME });
    const buttons = screen.getAllByRole('button', { name: 'Mandar código' });
    await userEvent.click(buttons[buttons.length - 1]);
    expect(await screen.findByText(/Mandamos un código a/)).toBeInTheDocument();

    await typeCode('123456');
    await userEvent.type(screen.getByLabelText('Clave nueva'), 'mi-clave-larga-1');
    await userEvent.type(screen.getByLabelText('Repetí la clave'), 'mi-clave-larga-1');
    await userEvent.click(screen.getByRole('button', { name: 'Cambiar clave' }));
    await waitFor(() =>
      expect(bodies['/api/v1/auth/me/password']).toEqual({
        challenge: SENT.challenge,
        code: '123456',
        password: 'mi-clave-larga-1',
      }),
    );
  });

  it('pide el código para el email nuevo y lo confirma', async () => {
    const bodies = mockApi({
      '/api/v1/auth/me/email/code': () => jsonResponse(SENT),
      '/api/v1/auth/me/email': () => jsonResponse({ ...ME, email: 'ana@nueva.com' }),
    });
    renderWithProviders(<ProfilePage />, { me: ME });
    await userEvent.type(screen.getByLabelText('Email nuevo'), 'ana@nueva.com');
    await userEvent.click(screen.getAllByRole('button', { name: 'Mandar código' })[0]);
    expect(await screen.findByText(/Mandamos un código a/)).toBeInTheDocument();
    expect(bodies['/api/v1/auth/me/email/code']).toEqual({ email: 'ana@nueva.com' });

    await typeCode('654321');
    await userEvent.click(screen.getByRole('button', { name: 'Cambiar email' }));
    await waitFor(() =>
      expect(bodies['/api/v1/auth/me/email']).toEqual({ challenge: SENT.challenge, code: '654321' }),
    );
  });
});
