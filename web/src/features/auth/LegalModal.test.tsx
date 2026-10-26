import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Me } from '@/api/types';
import { CLIENT_USER, renderWithProviders } from '@/test/render';
import { LegalModal } from './LegalModal';

const TERMS = {
  document: 'terms' as const,
  title: 'Condiciones del servicio',
  version: '2026-10-25',
  sha256: 'a'.repeat(64),
  url: 'https://atentina.com.ar/terminos/2026-10-25',
};

describe('LegalModal', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('pide aceptar lo pendiente y manda solo esas versiones', async () => {
    const fetchMock = vi.fn(
      () => new Response(JSON.stringify({ ...CLIENT_USER, legal_pending: [] }), { status: 200 }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const me: Me = { ...CLIENT_USER, legal_pending: [TERMS] };
    renderWithProviders(<LegalModal />, { me });
    expect(await screen.findByText('Actualizamos nuestras condiciones')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /Condiciones del servicio \(versión 2026-10-25\)/ }),
    ).toHaveAttribute('href', TERMS.url);
    const accept = screen.getByRole('button', { name: 'Aceptar' });
    expect(accept).toBeDisabled();
    await userEvent.click(screen.getByRole('checkbox'));
    await userEvent.click(accept);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const req = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(req.url).toContain('/api/v1/auth/me/legal');
    expect(await req.json()).toEqual({ terms_version: '2026-10-25', privacy_version: '' });
  });

  it('sin nada pendiente: no aparece', () => {
    renderWithProviders(<LegalModal />, { me: CLIENT_USER });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
