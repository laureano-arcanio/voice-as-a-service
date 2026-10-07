import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { WaAccount, WaCampaign } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { CampaignDetailPage } from './CampaignDetailPage';
import { CampaignsPage } from './CampaignsPage';
import { csvHelp, renderTemplate } from './labels';

const ACCOUNT: WaAccount = {
  id: 'wa-1',
  client_id: 'c-1',
  client_name: 'Acme',
  agent_id: 'ag-1',
  agent_name: 'Ventas',
  phone_number_id: '111',
  waba_id: '222',
  business_id: null,
  display_phone_number: '+54 351 555 0000',
  name: '',
  has_token: true,
  has_pin: true,
  active: true,
  status: 'connected',
  status_reason: null,
  status_changed_at: null,
  quality_rating: 'GREEN',
  messaging_limit: null,
  source: 'embedded_signup',
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
};

const CAMPAIGN: WaCampaign = {
  id: 'cmp-1',
  client_id: 'c-1',
  client_name: 'Acme',
  account_id: 'wa-1',
  display_phone_number: '+54 351 555 0000',
  agent_id: null,
  agent_name: 'Ventas',
  name: 'Prospectos octubre',
  template_name: 'demo',
  template_language: 'es_AR',
  template_category: 'MARKETING',
  template_body: 'Hola {{1}}, probá la demo.',
  template_params: 1,
  status: 'draft',
  status_reason: null,
  rate_per_minute: 20,
  window_start: 9,
  window_end: 20,
  timezone: 'America/Argentina/Buenos_Aires',
  stats: {
    total: 10,
    pending: 4,
    sent: 6,
    delivered: 5,
    read: 3,
    replied: 2,
    failed: 0,
    skipped: 0,
    opted_out: 1,
  },
  started_at: null,
  finished_at: null,
  created_at: '2026-10-07T12:00:00Z',
  updated_at: '2026-10-07T12:00:00Z',
};

function mockApi(routes: Record<string, () => Response>) {
  const calls: { method: string; path: string }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const path = new URL(req.url).pathname;
      calls.push({ method: req.method, path });
      const route = routes[`${req.method} ${path}`];
      return route ? route() : jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

describe('campañas', () => {
  it('helpers: texto de la plantilla y ayuda del CSV', () => {
    expect(renderTemplate('Hola {{1}}, {{2}}', ['Ana'])).toBe('Hola Ana, {{2}}');
    expect(csvHelp(2)).toContain('telefono,nombre');
    expect(csvHelp(0)).not.toContain('{{1}}');
  });

  it('lista: cliente sin columna de cliente, con progreso y bajas', async () => {
    mockApi({
      'GET /api/v1/whatsapp/campaigns': () => jsonResponse([CAMPAIGN]),
      'GET /api/v1/whatsapp/accounts': () => jsonResponse([ACCOUNT]),
      'GET /api/v1/whatsapp/optouts': () =>
        jsonResponse([
          { client_id: 'c-1', wa_id: '5493515551234', source: 'keyword', created_at: '2026-10-07T13:00:00Z' },
        ]),
    });
    renderWithProviders(<CampaignsPage />, { me: CLIENT_USER });
    expect(await screen.findByRole('link', { name: 'Prospectos octubre' })).toHaveAttribute(
      'href',
      '/campaigns/cmp-1',
    );
    expect(screen.getByText('6 / 10')).toBeInTheDocument();
    expect(screen.getByText('Borrador')).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Cliente' })).not.toBeInTheDocument();
    expect(await screen.findByText('5493515551234')).toBeInTheDocument();
    expect(screen.getByText('La pidió por WhatsApp')).toBeInTheDocument();
  });

  it('lista: sin numero propio conectado no deja crear', async () => {
    mockApi({
      'GET /api/v1/whatsapp/campaigns': () => jsonResponse([]),
      'GET /api/v1/whatsapp/accounts': () => jsonResponse([{ ...ACCOUNT, has_token: false }]),
      'GET /api/v1/whatsapp/optouts': () => jsonResponse([]),
    });
    renderWithProviders(<CampaignsPage />, { me: CLIENT_USER });
    expect(await screen.findByText(/primero conectá un número/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Nueva campaña/ })).toHaveAttribute('data-disabled', 'true');
  });

  it('detalle: muestra los totales e inicia el envio', async () => {
    const calls = mockApi({
      'GET /api/v1/whatsapp/campaigns/cmp-1': () => jsonResponse(CAMPAIGN),
      'GET /api/v1/whatsapp/campaigns/cmp-1/recipients': () =>
        jsonResponse({
          total: 1,
          items: [
            {
              id: 'r1',
              wa_id: '5493515551234',
              name: 'Ana',
              params: ['Ana'],
              status: 'replied',
              error: null,
              sent_at: '2026-10-07T13:00:00Z',
              replied_at: '2026-10-07T13:05:00Z',
              conversation_id: 'conv-1',
            },
          ],
        }),
      'POST /api/v1/whatsapp/campaigns/cmp-1/start': () => jsonResponse({ ...CAMPAIGN, status: 'running' }),
    });
    renderWithProviders(<CampaignDetailPage />, {
      me: CLIENT_USER,
      path: '/campaigns/cmp-1',
      routes: [{ path: '/campaigns/:id', element: <CampaignDetailPage /> }],
    });
    expect(await screen.findByText('Hola Ana, probá la demo.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ver conversación' })).toHaveAttribute('href', '/calls/conv-1');
    expect(
      within(screen.getByRole('row', { name: /5493515551234/ })).getByText('Respondió'),
    ).toBeInTheDocument();
    expect(screen.getByText('9 a 20 h')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Iniciar envío/ }));
    await waitFor(() =>
      expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/start'))).toBe(true),
    );
  });
});
