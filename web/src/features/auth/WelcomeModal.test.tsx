import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CLIENT_USER, renderWithProviders } from '@/test/render';
import { WelcomeModal } from './WelcomeModal';

describe('WelcomeModal', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('primera vez: muestra los videos y al cerrar lo marca visto', async () => {
    const fetchMock = vi.fn(
      () => new Response(JSON.stringify({ ...CLIENT_USER, welcome_pending: false }), { status: 200 }),
    );
    vi.stubGlobal('fetch', fetchMock);
    renderWithProviders(<WelcomeModal />, { me: { ...CLIENT_USER, welcome_pending: true } });
    expect(await screen.findByText('Te damos la bienvenida a Atentina')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Cómo crear y probar agentes/ })).toHaveAttribute(
      'href',
      'https://www.youtube.com/shorts/azBM8bJl_Xw',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Explorar el panel' }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const req = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(req.url).toContain('/api/v1/auth/me/welcome');
  });

  it('ya visto: no aparece', () => {
    renderWithProviders(<WelcomeModal />, { me: CLIENT_USER });
    expect(screen.queryByText('Te damos la bienvenida a Atentina')).not.toBeInTheDocument();
  });
});
