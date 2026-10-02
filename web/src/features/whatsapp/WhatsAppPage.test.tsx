import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { WaAccount, WaConfig } from '@/api/types';
import { ADMIN, CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { WhatsAppPage } from './WhatsAppPage';

const ACCOUNT: WaAccount = {
  id: 'wa-1',
  client_id: 'c-1',
  client_name: 'Acme',
  agent_id: 'ag-1',
  agent_name: 'Turnos',
  phone_number_id: '111',
  waba_id: '222',
  business_id: null,
  display_phone_number: '+54 351 555 0000',
  name: 'Acme',
  has_token: true,
  has_pin: true,
  active: true,
  status: 'disconnected',
  status_reason: 'token_invalid code=190',
  status_changed_at: null,
  quality_rating: 'GREEN',
  messaging_limit: 'TIER_1K',
  source: 'embedded_signup',
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
};

const ENABLED: WaConfig = {
  enabled: true,
  reason: null,
  app_id: '2192489028351511',
  config_id: '999',
  graph_version: 'v25.0',
  sdk_locale: 'es_LA',
};

type Route = (url: URL, init: Request) => Response | Promise<Response>;

function mockApi(routes: Record<string, Route>) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL) => {
    const req = input instanceof Request ? input : new Request(input);
    const url = new URL(req.url);
    const text = req.method === 'GET' ? '' : await req.clone().text();
    calls.push({ method: req.method, path: url.pathname, body: text ? JSON.parse(text) : null });
    const route = routes[`${req.method} ${url.pathname}`];
    return route ? route(url, req) : jsonResponse({ detail: 'no mock' }, 404);
  });
  vi.stubGlobal('fetch', fn);
  return calls;
}

afterEach(() => {
  vi.unstubAllGlobals();
  delete window.FB;
});

describe('WhatsAppPage', () => {
  it('cliente: sin columna de cliente ni alta manual; boton deshabilitado con el motivo', async () => {
    mockApi({
      'GET /api/v1/whatsapp/accounts': () => jsonResponse([ACCOUNT]),
      'GET /api/v1/whatsapp/config': () =>
        jsonResponse({ ...ENABLED, enabled: false, reason: 'Falta configurar WA_CONFIG_ID en el servidor' }),
      'GET /api/v1/agents': () => jsonResponse([]),
    });
    renderWithProviders(<WhatsAppPage />, { me: CLIENT_USER });

    expect(await screen.findByText('+54 351 555 0000')).toBeInTheDocument();
    expect(await screen.findByText(/Falta configurar WA_CONFIG_ID/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Conectar WhatsApp/ })).toHaveAttribute(
      'data-disabled',
      'true',
    );
    expect(screen.queryByRole('button', { name: /Alta manual/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Cliente' })).not.toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Token' })).not.toBeInTheDocument();
    expect(screen.getByText('Desconectado')).toBeInTheDocument();
    expect(screen.getByText('TIER_1K')).toBeInTheDocument(); // limite de mensajes
    // Desconectada: no se piden las plantillas a Meta.
    expect(screen.getByText(/volvé a conectarlo para ver sus plantillas/)).toBeInTheDocument();
  });

  it('cliente: en un numero de alta manual no ofrece registro, Meta ni plantillas', async () => {
    const calls = mockApi({
      'GET /api/v1/whatsapp/accounts': () =>
        jsonResponse([{ ...ACCOUNT, status: 'connected', has_token: false, source: 'manual' }]),
      'GET /api/v1/whatsapp/config': () => jsonResponse(ENABLED),
      'GET /api/v1/agents': () => jsonResponse([]),
    });
    renderWithProviders(<WhatsAppPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Acciones de \+54 351 555 0000/ }));
    expect(await screen.findByRole('menuitem', { name: /Desactivar/ })).toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: /Reintentar registro/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: /Releer datos/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: /Plantillas/ })).not.toBeInTheDocument();
    expect(calls.some((c) => c.path.endsWith('/templates'))).toBe(false);
  });

  it('admin: ve cliente, token y alta manual', async () => {
    mockApi({
      'GET /api/v1/whatsapp/accounts': () => jsonResponse([{ ...ACCOUNT, status: 'connected' }]),
      'GET /api/v1/whatsapp/config': () => jsonResponse(ENABLED),
      'GET /api/v1/clients': () => jsonResponse([]),
      'GET /api/v1/agents': () => jsonResponse([]),
      'GET /api/v1/whatsapp/accounts/wa-1/templates': () =>
        jsonResponse([
          {
            id: 't1',
            name: 'recordatorio_turno',
            language: 'es_AR',
            category: 'UTILITY',
            status: 'REJECTED',
            rejected_reason: 'INVALID_FORMAT',
            components: [{ type: 'BODY', text: 'Hola {{1}}' }],
          },
        ]),
    });
    renderWithProviders(<WhatsAppPage />, { me: ADMIN });
    expect(await screen.findByRole('columnheader', { name: 'Cliente' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Alta manual/ })).toBeInTheDocument();
    expect(screen.getByText('Propio')).toBeInTheDocument();
    expect(await screen.findByText('recordatorio_turno')).toBeInTheDocument();
    expect(screen.getByText('Rechazada')).toBeInTheDocument();
    expect(screen.getByText('INVALID_FORMAT')).toBeInTheDocument();
  });

  it('alta por Embedded Signup: junta codigo y FINISH y manda el signup', async () => {
    const calls = mockApi({
      'GET /api/v1/whatsapp/accounts': () => jsonResponse([]),
      'GET /api/v1/whatsapp/config': () => jsonResponse(ENABLED),
      'GET /api/v1/agents': () => jsonResponse([{ id: 'ag-1', name: 'Turnos' }]),
      'POST /api/v1/whatsapp/signup': () =>
        jsonResponse({ ...ACCOUNT, status: 'connected', status_reason: null }, 201),
    });
    let loginCb: ((r: { authResponse?: { code?: string } }) => void) | null = null;
    const init = vi.fn();
    const login = vi.fn((cb: (r: { authResponse?: { code?: string } }) => void) => {
      loginCb = cb;
    });
    window.FB = { init, login };

    const user = userEvent.setup();
    renderWithProviders(<WhatsAppPage />, { me: CLIENT_USER });
    const open = await screen.findByRole('button', { name: /Conectar WhatsApp/ });
    await waitFor(() => expect(open).not.toHaveAttribute('data-disabled'));
    await user.click(open);

    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('textbox', { name: 'Agente que responde' }));
    await user.click(await screen.findByRole('option', { name: 'Turnos', hidden: true }));
    const connect = within(dialog).getByRole('button', { name: /Conectar WhatsApp/ });
    await waitFor(() => expect(connect).toBeEnabled());
    await user.click(connect);

    expect(init).toHaveBeenCalledWith(expect.objectContaining({ appId: ENABLED.app_id, version: 'v25.0' }));
    expect(login).toHaveBeenCalledWith(
      expect.any(Function),
      expect.objectContaining({
        config_id: '999',
        response_type: 'code',
        override_default_response_type: true,
      }),
    );

    const finish = JSON.stringify({
      type: 'WA_EMBEDDED_SIGNUP',
      event: 'FINISH',
      data: { phone_number_id: '111', waba_id: '222', business_id: '333' },
    });
    act(() => {
      // Un origen falso se ignora; el de Facebook cuenta.
      window.dispatchEvent(new MessageEvent('message', { origin: 'https://evilfacebook.com', data: finish }));
      window.dispatchEvent(new MessageEvent('message', { origin: 'https://www.facebook.com', data: finish }));
      loginCb?.({ authResponse: { code: 'CODE123' } });
    });

    expect(await screen.findByText('Número conectado')).toBeInTheDocument();
    expect(within(dialog).getByRole('link', { name: 'WhatsApp Manager' })).toHaveAttribute(
      'href',
      'https://business.facebook.com/wa/manage/home/',
    );
    const posts = calls.filter((c) => c.method === 'POST');
    expect(posts).toHaveLength(1);
    expect(posts[0]!.body).toMatchObject({
      code: 'CODE123',
      event: 'FINISH',
      waba_id: '222',
      phone_number_id: '111',
      business_id: '333',
      agent_id: 'ag-1',
      client_id: null,
      pin: null,
    });
  });

  it('alta cancelada en Meta: aviso y no llama a la API', async () => {
    const calls = mockApi({
      'GET /api/v1/whatsapp/accounts': () => jsonResponse([]),
      'GET /api/v1/whatsapp/config': () => jsonResponse(ENABLED),
      'GET /api/v1/agents': () => jsonResponse([{ id: 'ag-1', name: 'Turnos' }]),
    });
    window.FB = { init: vi.fn(), login: vi.fn() };
    const user = userEvent.setup();
    renderWithProviders(<WhatsAppPage />, { me: CLIENT_USER });
    const open = await screen.findByRole('button', { name: /Conectar WhatsApp/ });
    await waitFor(() => expect(open).not.toHaveAttribute('data-disabled'));
    await user.click(open);
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('textbox', { name: 'Agente que responde' }));
    await user.click(await screen.findByRole('option', { name: 'Turnos', hidden: true }));
    await user.click(within(dialog).getByRole('button', { name: /Conectar WhatsApp/ }));
    act(() => {
      window.dispatchEvent(
        new MessageEvent('message', {
          origin: 'https://www.facebook.com',
          data: JSON.stringify({
            type: 'WA_EMBEDDED_SIGNUP',
            event: 'CANCEL',
            data: { current_step: 'PHONE_NUMBER_SETUP' },
          }),
        }),
      );
    });
    expect(
      await screen.findByText(/Se canceló el alta en Meta \(paso: PHONE_NUMBER_SETUP\)/),
    ).toBeInTheDocument();
    expect(calls.filter((c) => c.method === 'POST')).toHaveLength(0);
  });
});
