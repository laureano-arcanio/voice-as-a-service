import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { LegalVersion } from '@/api/types';
import { ADMIN, jsonResponse, renderWithProviders } from '@/test/render';
import { LegalPage } from './LegalPage';

const terms = (version: string, current: boolean, acceptances: number): LegalVersion => ({
  document: 'terms',
  title: 'Condiciones del servicio',
  version,
  sha256: 'a'.repeat(64),
  url: `https://atentina.com.ar/terminos/${version}`,
  current,
  acceptances,
});

afterEach(() => vi.unstubAllGlobals());

describe('LegalPage', () => {
  it('lista las versiones y abre el texto de una anterior', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(input instanceof Request ? input.url : String(input), 'http://x');
        if (url.pathname === '/api/v1/legal/versions')
          return jsonResponse([terms('2026-10-28', true, 12), terms('2026-10-01', false, 3)]);
        if (url.pathname === '/api/v1/legal/versions/terms/2026-10-01')
          return jsonResponse({ ...terms('2026-10-01', false, 3), text: '# Texto viejo' });
        return jsonResponse({}, 404);
      }),
    );
    renderWithProviders(<LegalPage />, { me: ADMIN });
    expect(await screen.findByText('2026-10-28')).toBeInTheDocument();
    expect(screen.getByText('1/10/2026')).toBeInTheDocument();
    expect(screen.getAllByText('Vigente')).toHaveLength(1);
    await userEvent.click(screen.getAllByRole('button', { name: 'Ver texto' })[1]);
    const dialog = await screen.findByRole('dialog');
    expect(await within(dialog).findByText('# Texto viejo')).toBeInTheDocument();
    expect(within(dialog).getByText('https://atentina.com.ar/terminos/2026-10-01')).toBeInTheDocument();
  });
});
