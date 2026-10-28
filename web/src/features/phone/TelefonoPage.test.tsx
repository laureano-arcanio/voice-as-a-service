import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Contact } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { leave } from '@/features/auth/switch';
import { CallProvider } from './CallProvider';
import { TelefonoPage } from './TelefonoPage';
import { FakeRoom, mockApi, PLAN_FREE, PLAN_OK, stubMediaDevices } from './testing';

vi.mock('livekit-client', async () => (await import('./testing')).fakeLivekit());
vi.mock('./ringtone', () => ({
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
  notes: null,
  source: 'manual',
  archived_at: null,
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
};
const ANA = base;
const LUIS: Contact = { ...base, id: 'k2', phone: '+5493515550002', name: 'Luis Gómez' };
const MARTA: Contact = { ...base, id: 'k3', phone: '+5493515550003', name: 'Marta Ruiz' };

const NUMBER = (id: string, e164: string, label: string) => ({
  id,
  e164,
  label,
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
});

const MY_CALL = {
  id: 'conv-9',
  client_id: 'c-1',
  client_name: 'Acme',
  agent_id: null,
  agent_name: null,
  agent_version: null,
  workflow_status: 'active',
  created_at: '2026-10-27T14:00:00Z',
  contact_name: 'Luis Gómez',
  company: null,
  outcome: null,
  goal: false,
  captured: 0,
  required: 0,
  mode: 'directa',
  phone: '+5493515550002',
  status: 'finalizada',
  duration_seconds: 95,
  ended_reason: 'customer_hangup',
  latency_avg: null,
  user_id: 'u-client',
  user_name: 'Ana',
  answered_by: null,
  opted_out_confirmed: false,
};

function routes(
  plan = PLAN_OK,
  numbers = [NUMBER('n1', '+541155550000', 'Ventas'), NUMBER('n2', '+541155550001', 'Cobranzas')],
) {
  return {
    'GET /api/v1/plan/features': () => jsonResponse(plan),
    'GET /api/v1/phone-numbers': () => jsonResponse(numbers),
    'GET /api/v1/contacts': () => jsonResponse({ items: [ANA, LUIS, MARTA], total: 3 }),
    'GET /api/v1/contacts/optouts': () =>
      jsonResponse([
        {
          client_id: 'c-1',
          phone: LUIS.phone,
          channel: 'voice',
          source: 'manual',
          created_at: '2026-10-12T12:00:00Z',
        },
        {
          client_id: 'c-1',
          phone: ANA.phone,
          channel: 'whatsapp',
          source: 'keyword',
          created_at: '2026-10-12T12:00:00Z',
        },
      ]),
    'GET /api/v1/blocked-numbers': () =>
      jsonResponse([{ client_id: 'c-1', phone: MARTA.phone, note: '', created_at: '2026-10-12T12:00:00Z' }]),
    'GET /api/v1/calls': () => jsonResponse({ items: [MY_CALL], total: 1 }),
    'POST /api/v1/direct-calls': () =>
      jsonResponse(
        {
          conversation_id: 'conv-1',
          room: 'r',
          status: 'pendiente',
          livekit_url: 'wss://lk.test',
          token: 't',
        },
        201,
      ),
  };
}

function renderPage() {
  return renderWithProviders(<></>, {
    me: CLIENT_USER,
    routes: [
      {
        path: '*',
        element: (
          <CallProvider>
            <TelefonoPage />
          </CallProvider>
        ),
      },
    ],
  });
}

describe('TelefonoPage', () => {
  beforeEach(() => {
    FakeRoom.all = [];
    stubMediaDevices();
    sessionStorage.clear();
    localStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  it('lista la agenda con las bajas y los bloqueados, y llama desde el número elegido', async () => {
    const seen = mockApi(routes());
    renderPage();
    const list = await screen.findByRole('list', { name: 'Contactos' });
    const rows = within(list).getAllByRole('listitem');
    expect(rows).toHaveLength(3);
    // La baja de WhatsApp no cuenta para llamar; la de voz sí.
    expect(within(rows[0]).queryByText('No quiere llamadas')).not.toBeInTheDocument();
    expect(within(rows[1]).getByText('No quiere llamadas')).toBeInTheDocument();
    expect(within(rows[2]).getByText('Bloqueado')).toBeInTheDocument();
    expect(within(rows[2]).getByRole('button', { name: 'Llamar a Marta Ruiz' })).toHaveAttribute(
      'data-disabled',
    );

    // Sale desde: dos números, se elige el segundo y se recuerda.
    await userEvent.click(screen.getByRole('textbox', { name: 'Sale desde' }));
    await userEvent.click(
      await screen.findByRole('option', { name: '+541155550001 · Cobranzas', hidden: true }),
    );
    expect(localStorage.getItem('atentina.phone.from.u-client')).toBe('n2');

    await userEvent.click(within(rows[0]).getByRole('button', { name: 'Llamar a Ana Pérez' }));
    await waitFor(() => expect(FakeRoom.all).toHaveLength(1));
    expect(seen.find((s) => s.method === 'POST' && s.path === '/api/v1/direct-calls')?.body).toEqual(
      expect.objectContaining({ contact_id: 'k1', from_number_id: 'n2' }),
    );

    // Mis últimas llamadas: las del usuario.
    expect(seen.some((s) => s.path === '/api/v1/calls' && s.search.includes('user_id=u-client'))).toBe(true);
    expect(await screen.findByText('Saliente · Ana')).toBeInTheDocument();
  });

  it('el panel del contacto avisa la baja y muestra sus llamadas', async () => {
    mockApi(routes());
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Ver Luis Gómez' }));
    expect(await screen.findByText(/Pidió no recibir llamadas/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ver la ficha' })).toHaveAttribute('href', '/contacts/k2');
    await waitFor(() => expect(screen.getAllByText('Saliente · Ana').length).toBeGreaterThan(1));
  });

  it('marcar un número valida el formato', async () => {
    const seen = mockApi(routes(PLAN_OK, [NUMBER('n1', '+541155550000', 'Ventas')]));
    renderPage();
    // Con un solo número, no hay selector.
    await screen.findByRole('list', { name: 'Contactos' });
    expect(screen.queryByRole('textbox', { name: 'Sale desde' })).not.toBeInTheDocument();

    const input = screen.getByRole('textbox', { name: 'O marcá un número' });
    await userEvent.type(input, '351 555');
    await userEvent.click(screen.getByRole('button', { name: 'Llamar' }));
    expect(await screen.findByText(/Formato internacional/)).toBeInTheDocument();
    expect(seen.some((s) => s.path === '/api/v1/direct-calls')).toBe(false);

    await userEvent.clear(input);
    await userEvent.type(input, '+54 9 351 555-9999');
    await userEvent.click(screen.getByRole('button', { name: 'Llamar' }));
    await waitFor(() =>
      expect(seen.find((s) => s.method === 'POST' && s.path === '/api/v1/direct-calls')?.body).toEqual(
        expect.objectContaining({ contact_id: null, phone: '+5493515559999', from_number_id: 'n1' }),
      ),
    );
  });

  it('Abrir aplicación Teléfono lleva a la app con la misma sesión', async () => {
    const assign = vi.spyOn(leave, 'assign').mockImplementation(() => undefined);
    mockApi({
      ...routes(),
      'POST /api/v1/auth/switch': () => jsonResponse({ url: 'https://tel.test/#sesion=t' }),
    });
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: 'Abrir aplicación Teléfono' }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith('https://tel.test/#sesion=t'));
    assign.mockRestore();
  });

  it('sin la función en el plan: el aviso y la pantalla bloqueada', async () => {
    mockApi(routes(PLAN_FREE));
    renderPage();
    expect(await screen.findByText('Tu plan Free no incluye llamadas directas.')).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'No incluido en tu plan: llamadas directas' })).toBeDisabled();
  });
});
