import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Me, WaAccount, WaConfig } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
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
  routes: [],
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
};

const SUPPORT: Me = { ...CLIENT_USER, support: true };

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

/**
 * Abre el menú de acciones de la cuenta y devuelve el ítem. En jsdom no hay layout: según cuándo calcula Floating UI
 * la posición, el menú puede quedar con `display: none` (la cuenta da el botón por "oculto", hideDetached) aunque
 * esté abierto, así que el ítem se busca también entre los ocultos.
 */
async function actionItem(user: { click: (el: Element) => Promise<void> }, item: RegExp) {
  await user.click(await screen.findByRole('button', { name: /Acciones de \+54 351 555 0000/ }));
  return screen.findByRole('menuitem', { name: item, hidden: true });
}

describe('WhatsAppPage', () => {
  it('cliente: sin alta manual ni Embedded Signup apagado (oculto); conectar con mi app de Meta', async () => {
    mockApi({
      'GET /api/v1/whatsapp/accounts': () => jsonResponse([ACCOUNT]),
      'GET /api/v1/whatsapp/config': () =>
        jsonResponse({ ...ENABLED, enabled: false, reason: 'Falta configurar WA_CONFIG_ID en el servidor' }),
      'GET /api/v1/agents': () => jsonResponse([]),
    });
    renderWithProviders(<WhatsAppPage />, { me: CLIENT_USER });

    expect(await screen.findByText('+54 351 555 0000')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Conectar con mi app de Meta/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Conectar WhatsApp/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/Falta configurar WA_CONFIG_ID/)).not.toBeInTheDocument();
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
    expect(await actionItem(userEvent, /Desactivar/)).toBeInTheDocument();
    expect(
      screen.queryByRole('menuitem', { name: /Reintentar registro/, hidden: true }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: /Releer datos/, hidden: true })).not.toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: /Plantillas/, hidden: true })).not.toBeInTheDocument();
    expect(calls.some((c) => c.path.endsWith('/templates'))).toBe(false);
  });

  it('soporte: ve token y alta manual, sin columna de cliente', async () => {
    mockApi({
      'GET /api/v1/whatsapp/accounts': () => jsonResponse([{ ...ACCOUNT, status: 'connected' }]),
      'GET /api/v1/whatsapp/config': () => jsonResponse(ENABLED),
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
    renderWithProviders(<WhatsAppPage />, { me: SUPPORT });
    expect(await screen.findByRole('columnheader', { name: 'Token' })).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Cliente' })).not.toBeInTheDocument();
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
  it('app propia: guia, alta con los datos y paso final con el webhook', async () => {
    const calls = mockApi({
      'GET /api/v1/whatsapp/accounts': () => jsonResponse([]),
      'GET /api/v1/whatsapp/config': () => jsonResponse({ ...ENABLED, enabled: false }),
      'GET /api/v1/agents': () => jsonResponse([{ id: 'ag-1', name: 'Turnos' }]),
      'POST /api/v1/whatsapp/accounts/own-app': () =>
        jsonResponse(
          {
            ...ACCOUNT,
            status: 'connected',
            status_reason: null,
            source: 'own_app',
            webhook_url: 'https://wa.atentina.com.ar/wa/webhook/abc123',
            verify_token: 'verif-xyz',
          },
          201,
        ),
    });
    const user = userEvent.setup();
    renderWithProviders(<WhatsAppPage />, { me: CLIENT_USER });
    await user.click(await screen.findByRole('button', { name: /Conectar con mi app de Meta/ }));
    const dialog = await screen.findByRole('dialog');
    expect(
      within(dialog).getByText(/crear una app de tipo Business|creá una app de tipo Business/),
    ).toBeInTheDocument();

    await user.click(within(dialog).getByRole('button', { name: 'Conectar' }));
    expect(within(dialog).getByText('Elegí el agente')).toBeInTheDocument();
    expect(calls.filter((c) => c.method === 'POST')).toHaveLength(0);

    await user.click(within(dialog).getByRole('textbox', { name: 'Agente que responde' }));
    await user.click(await screen.findByRole('option', { name: 'Turnos', hidden: true }));
    await user.type(within(dialog).getByRole('textbox', { name: /Identificador del número/ }), '111');
    await user.type(within(dialog).getByRole('textbox', { name: /Identificador de la cuenta/ }), '222');
    await user.type(within(dialog).getByLabelText(/Token permanente/), 'EAAtoken');
    await user.type(within(dialog).getByLabelText(/Clave secreta de la app/), 'secreto');
    await user.click(within(dialog).getByRole('button', { name: 'Conectar' }));

    expect(await screen.findByText('Número conectado')).toBeInTheDocument();
    expect(within(dialog).getByText('https://wa.atentina.com.ar/wa/webhook/abc123')).toBeInTheDocument();
    expect(within(dialog).getByText('verif-xyz')).toBeInTheDocument();
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      agent_id: 'ag-1',
      phone_number_id: '111',
      waba_id: '222',
      access_token: 'EAAtoken',
      app_secret: 'secreto',
    });
  });

  it('app propia: el 409 y signup_mismatch se explican en el modal', async () => {
    let n = 0;
    mockApi({
      'GET /api/v1/whatsapp/accounts': () => jsonResponse([]),
      'GET /api/v1/whatsapp/config': () => jsonResponse({ ...ENABLED, enabled: false }),
      'GET /api/v1/agents': () => jsonResponse([{ id: 'ag-1', name: 'Turnos' }]),
      'POST /api/v1/whatsapp/accounts/own-app': () =>
        n++ === 0
          ? jsonResponse({ detail: 'ocupado' }, 409)
          : jsonResponse({ detail: 'x', code: 'signup_mismatch' }, 400),
    });
    const user = userEvent.setup();
    renderWithProviders(<WhatsAppPage />, { me: CLIENT_USER });
    await user.click(await screen.findByRole('button', { name: /Conectar con mi app de Meta/ }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('textbox', { name: 'Agente que responde' }));
    await user.click(await screen.findByRole('option', { name: 'Turnos', hidden: true }));
    await user.type(within(dialog).getByRole('textbox', { name: /Identificador del número/ }), '111');
    await user.type(within(dialog).getByRole('textbox', { name: /Identificador de la cuenta/ }), '222');
    await user.type(within(dialog).getByLabelText(/Token permanente/), 'EAAtoken');
    await user.type(within(dialog).getByLabelText(/Clave secreta de la app/), 'secreto');
    await user.click(within(dialog).getByRole('button', { name: 'Conectar' }));
    expect(await within(dialog).findByText(/ya está conectado en otra cuenta/)).toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Conectar' }));
    expect(
      await within(dialog).findByText(/no pertenece a esa cuenta de WhatsApp Business/),
    ).toBeInTheDocument();
  });

  it('cuenta con app propia: badge, datos del webhook y actualizar token', async () => {
    mockApi({
      'GET /api/v1/whatsapp/accounts': () =>
        jsonResponse([
          {
            ...ACCOUNT,
            status: 'connected',
            source: 'own_app',
            has_app_secret: true,
            webhook_url: 'https://wa.atentina.com.ar/wa/webhook/abc123',
            verify_token: 'verif-xyz',
          },
        ]),
      'GET /api/v1/whatsapp/config': () => jsonResponse({ ...ENABLED, enabled: false }),
      'GET /api/v1/agents': () => jsonResponse([{ id: 'ag-1', name: 'Turnos' }]),
      'GET /api/v1/whatsapp/accounts/wa-1/templates': () => jsonResponse([]),
    });
    const user = userEvent.setup();
    renderWithProviders(<WhatsAppPage />, { me: CLIENT_USER });
    expect(await screen.findByText('App propia')).toBeInTheDocument();

    await user.click(await actionItem(user, /Datos del webhook/));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('verif-xyz')).toBeInTheDocument();
  });

  it('cuenta con app propia: actualizar token precarga los identificadores', async () => {
    mockApi({
      'GET /api/v1/whatsapp/accounts': () =>
        jsonResponse([
          {
            ...ACCOUNT,
            status: 'connected',
            source: 'own_app',
            webhook_url: 'https://wa.atentina.com.ar/wa/webhook/abc123',
            verify_token: 'verif-xyz',
          },
        ]),
      'GET /api/v1/whatsapp/config': () => jsonResponse({ ...ENABLED, enabled: false }),
      'GET /api/v1/agents': () => jsonResponse([{ id: 'ag-1', name: 'Turnos' }]),
      'GET /api/v1/whatsapp/accounts/wa-1/templates': () => jsonResponse([]),
    });
    const user = userEvent.setup();
    renderWithProviders(<WhatsAppPage />, { me: CLIENT_USER });
    await user.click(await actionItem(user, /Actualizar token/));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByRole('textbox', { name: /Identificador del número/ })).toHaveValue('111');
    expect(within(dialog).getByRole('textbox', { name: /Identificador de la cuenta/ })).toHaveValue('222');
  });

  it('ruteo por contacto: muestra las reglas y guarda los cambios', async () => {
    const calls = mockApi({
      'GET /api/v1/whatsapp/accounts': () =>
        jsonResponse([
          {
            ...ACCOUNT,
            status: 'connected',
            has_token: false,
            source: 'manual',
            routes: [{ agent_id: 'ag-2', agent_name: 'Soporte', contacts: ['5491155551234'] }],
          },
        ]),
      'GET /api/v1/whatsapp/config': () => jsonResponse(ENABLED),
      'GET /api/v1/agents': () =>
        jsonResponse([
          { id: 'ag-1', name: 'Turnos' },
          { id: 'ag-2', name: 'Soporte' },
        ]),
      'PUT /api/v1/whatsapp/accounts/wa-1/routes': () =>
        jsonResponse([
          { agent_id: 'ag-2', agent_name: 'Soporte', contacts: ['5491155551234', '5491155559999'] },
        ]),
    });
    const user = userEvent.setup();
    renderWithProviders(<WhatsAppPage />, { me: CLIENT_USER });

    expect(await screen.findByText('1 regla por contacto')).toBeInTheDocument();
    await user.click(await actionItem(user, /Ruteo por contacto/));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('5491155551234')).toBeInTheDocument();
    await user.type(
      within(dialog).getByRole('textbox', { name: 'Contactos que atiende' }),
      '5491155559999{Enter}',
    );
    await user.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'PUT')?.body).toEqual([
        { agent_id: 'ag-2', contacts: ['5491155551234', '5491155559999'] },
      ]),
    );
  });
});
