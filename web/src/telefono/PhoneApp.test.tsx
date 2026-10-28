import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Contact } from '@/api/types';
import { leave } from '@/features/auth/switch';
import { CallProvider } from '@/features/phone/CallProvider';
import { FakeRoom, mockApi, PLAN_FREE, PLAN_OK, stubMediaDevices } from '@/features/phone/testing';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { PhoneApp } from './PhoneApp';

vi.mock('livekit-client', async () => (await import('@/features/phone/testing')).fakeLivekit());
vi.mock('@/features/phone/ringtone', () => ({
  playRingtone: vi.fn(),
  playRingback: vi.fn(),
  RINGBACK_REPEAT_MS: 5000,
}));

const base: Contact = {
  id: 'k1',
  client_id: 'c-1',
  phone: '+5493515551234',
  name: 'Ana Pérez',
  email: null,
  notes: 'Prefiere a la tarde',
  source: 'manual',
  archived_at: null,
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
};
const ANA = base;
const LUIS: Contact = { ...base, id: 'k2', phone: '+5493515550002', name: 'Luis Gómez', notes: null };

const NUMBER = {
  id: 'n1',
  e164: '+541155550000',
  label: 'Ventas',
  provider: 'anura',
  client_id: 'c-1',
  agent_id: null,
  assigned_at: null,
  created_at: '2026-10-01T12:00:00Z',
  answer_mode: 'team',
  ring_first: 'phone',
  ring_seconds: 20,
  team_fallback: 'voicemail',
  team_fallback_message: '',
};

const CALL = {
  id: 'conv-9',
  client_id: 'c-1',
  client_name: 'Acme',
  agent_id: null,
  agent_name: null,
  agent_version: null,
  workflow_status: 'active',
  created_at: new Date().toISOString(),
  contact_name: null,
  contact_id: null,
  company: null,
  outcome: null,
  goal: false,
  captured: 0,
  required: 0,
  mode: 'directa',
  phone: '+5491144440000',
  status: 'finalizada',
  duration_seconds: 95,
  ended_reason: 'customer_hangup',
  latency_avg: null,
  user_id: 'u-client',
  user_name: 'Ana',
  answered_by: null,
  opted_out_confirmed: false,
};

function routes(plan = PLAN_OK, extra: Record<string, (body: unknown) => Response> = {}) {
  return {
    'GET /api/v1/plan/features': () => jsonResponse(plan),
    'GET /api/v1/phone-numbers': () => jsonResponse([NUMBER]),
    'GET /api/v1/contacts': () => jsonResponse({ items: [LUIS, ANA], total: 2 }),
    'GET /api/v1/contacts/k1': () => jsonResponse(ANA),
    'GET /api/v1/contacts/optouts': () => jsonResponse([]),
    'GET /api/v1/blocked-numbers': () => jsonResponse([]),
    'GET /api/v1/calls': () => jsonResponse({ items: [CALL], total: 1 }),
    'POST /api/v1/direct-calls': () =>
      jsonResponse(
        { conversation_id: 'conv-1', room: 'r', status: 'pendiente', livekit_url: 'wss://lk.test', token: 't' },
        201,
      ),
    'POST /api/v1/calls/conv-1/hangup': () => jsonResponse({}),
    ...extra,
  };
}

function renderApp() {
  return renderWithProviders(<></>, {
    me: CLIENT_USER,
    routes: [
      {
        path: '*',
        element: (
          <CallProvider>
            <PhoneApp />
          </CallProvider>
        ),
      },
    ],
  });
}

const directCall = (seen: ReturnType<typeof mockApi>) =>
  seen.find((s) => s.method === 'POST' && s.path === '/api/v1/direct-calls')?.body;

describe('PhoneApp', () => {
  beforeEach(() => {
    FakeRoom.all = [];
    stubMediaDevices();
    sessionStorage.clear();
    localStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  it('recientes: las del usuario, agrupadas por día, y se vuelve a llamar desde la fila', async () => {
    const seen = mockApi(routes());
    renderApp();
    const today = await screen.findByRole('region', { name: 'Hoy' });
    expect(within(today).getByText('+5491144440000')).toBeInTheDocument();
    expect(seen.some((s) => s.path === '/api/v1/calls' && s.search.includes('user_id=u-client'))).toBe(true);

    await userEvent.click(within(today).getByRole('button', { name: 'Llamar a +5491144440000' }));
    await waitFor(() => expect(FakeRoom.all).toHaveLength(1));
    expect(directCall(seen)).toEqual(
      expect.objectContaining({ contact_id: null, phone: '+5491144440000', from_number_id: 'n1' }),
    );
    // La llamada ocupa la pantalla; Cortar la termina.
    const call = screen.getByRole('dialog', { name: 'Llamada' });
    expect(within(call).getByText('Desde Ventas · +541155550000')).toBeInTheDocument();
    await userEvent.click(within(call).getByRole('button', { name: 'Cortar' }));
    expect(await screen.findByText('Cortaste la llamada')).toBeInTheDocument();
  });

  it('contactos por letra, la ficha con favorito y llamar desde favoritos', async () => {
    const seen = mockApi(routes());
    renderApp();
    await userEvent.click(await screen.findByRole('button', { name: 'Contactos' }));
    const list = await screen.findByRole('list', { name: 'Contactos' });
    const names = within(list)
      .getAllByRole('listitem')
      .map((r) => within(r).getAllByRole('button')[0]!.getAttribute('aria-label'));
    expect(names).toEqual(['Ver Ana Pérez', 'Ver Luis Gómez']);
    expect(within(list).getByRole('heading', { name: 'A' })).toBeInTheDocument();

    await userEvent.click(within(list).getByRole('button', { name: 'Ver Ana Pérez' }));
    expect(await screen.findByText('Prefiere a la tarde')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Agregar a favoritos' }));
    expect(JSON.parse(localStorage.getItem('atentina.phone.favorites.u-client')!)).toEqual([
      { id: 'k1', name: 'Ana Pérez', phone: ANA.phone },
    ]);
    await userEvent.click(screen.getByRole('button', { name: 'Volver' }));
    await userEvent.click(screen.getByRole('button', { name: 'Favoritos' }));
    await userEvent.click(screen.getByRole('button', { name: 'Llamar a Ana Pérez' }));
    await waitFor(() => expect(directCall(seen)).toEqual(expect.objectContaining({ contact_id: 'k1' })));
  });

  it('el teclado pide el código de país y marca con + manteniendo el 0', async () => {
    const seen = mockApi(routes());
    renderApp();
    await userEvent.click(await screen.findByRole('button', { name: 'Abrir el teclado' }));
    const pad = screen.getByRole('dialog', { name: 'Teclado' });
    for (const k of '3515559999') await userEvent.click(within(pad).getByRole('button', { name: k }));
    await userEvent.click(within(pad).getByRole('button', { name: 'Llamar' }));
    expect(await within(pad).findByRole('alert')).toHaveTextContent('código de país');
    expect(directCall(seen)).toBeUndefined();

    await userEvent.click(within(pad).getByRole('button', { name: 'Más' }));
    expect(within(pad).getByRole('textbox', { name: 'Número' })).toHaveValue('+3515559999');
    await userEvent.click(within(pad).getByRole('button', { name: 'Llamar' }));
    await waitFor(() => expect(directCall(seen)).toEqual(expect.objectContaining({ phone: '+3515559999' })));
  });

  it('una entrante con Disponible: pantalla completa con Atender y Rechazar', async () => {
    sessionStorage.setItem('atentina.phone.available', '1');
    const seen = mockApi(
      routes(PLAN_OK, {
        'PUT /api/v1/me/presence': () => jsonResponse({ available: true, until: null }),
        'GET /api/v1/me/ringing': () =>
          jsonResponse([
            {
              conversation_id: 'conv-in',
              phone: LUIS.phone,
              contact_id: 'k2',
              contact_name: 'Luis Gómez',
              number_e164: '+541155550000',
              number_label: 'Ventas',
              started_at: new Date().toISOString(),
            },
          ]),
        'POST /api/v1/direct-calls/conv-in/decline': () => new Response(null, { status: 204 }),
      }),
    );
    renderApp();
    const incoming = await screen.findByRole('dialog', { name: 'Llamada entrante' });
    expect(within(incoming).getByText('Llamada entrante a Ventas')).toBeInTheDocument();
    expect(within(incoming).getByRole('heading', { name: 'Luis Gómez' })).toBeInTheDocument();
    await userEvent.click(within(incoming).getByRole('button', { name: 'Rechazar' }));
    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: 'Llamada entrante' })).not.toBeInTheDocument(),
    );
    expect(seen.some((s) => s.path === '/api/v1/direct-calls/conv-in/decline')).toBe(true);
  });

  it('Volver al panel abre el Teléfono del equipo con la misma sesión', async () => {
    const assign = vi.spyOn(leave, 'assign').mockImplementation(() => undefined);
    const seen = mockApi(
      routes(PLAN_OK, {
        'POST /api/v1/auth/switch': () => jsonResponse({ url: 'https://app.test/telefono#sesion=t' }),
      }),
    );
    renderApp();
    await userEvent.click(await screen.findByRole('button', { name: 'Tu cuenta' }));
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Volver al panel' }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith('https://app.test/telefono#sesion=t'));
    expect(seen.find((s) => s.path === '/api/v1/auth/switch')?.body).toEqual({ target: 'panel' });
  });

  it('sin la función en el plan: la pantalla bloqueada', async () => {
    mockApi(routes(PLAN_FREE));
    renderApp();
    expect(await screen.findByText('Tu plan no incluye las llamadas del equipo')).toBeInTheDocument();
  });
});
