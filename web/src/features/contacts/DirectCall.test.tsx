import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Contact } from '@/api/types';
import { CallProvider } from '@/features/phone/CallProvider';
import { FakeRoom, mockApi, PLAN_FREE, PLAN_OK, stubMediaDevices } from '@/features/phone/testing';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { ContactDetailPage } from './ContactDetailPage';
import { ContactsPage } from './ContactsPage';

// Llamar a un contacto desde la agenda y su ficha (docs/LLAMADAS_DIRECTAS_PLAN.md, sección 8).

vi.mock('livekit-client', async () => (await import('@/features/phone/testing')).fakeLivekit());
vi.mock('@/features/phone/ringtone', () => ({ playRingtone: vi.fn() }));

const ANA: Contact = {
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
const LUIS: Contact = { ...ANA, id: 'k2', phone: '+5493515550002', name: 'Luis Gómez' };
const MARTA: Contact = { ...ANA, id: 'k3', phone: '+5493515550003', name: 'Marta Ruiz' };

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
  created_at: '2026-10-27T14:00:00Z',
  contact_name: null,
  company: null,
  outcome: null,
  goal: false,
  captured: 0,
  required: 0,
  mode: 'directa',
  phone: LUIS.phone,
  status: 'finalizada',
  duration_seconds: 95,
  ended_reason: 'person_hangup',
  latency_avg: null,
  user_id: 'u-client',
  user_name: 'Ana',
  answered_by: null,
  opted_out_confirmed: true,
};
const AGENT_CALL = {
  ...CALL,
  id: 'conv-8',
  agent_id: 'ag-1',
  agent_name: 'Cobranzas',
  mode: 'saliente',
  user_id: null,
  user_name: null,
  opted_out_confirmed: false,
};
const WHATSAPP = { ...CALL, id: 'conv-7', mode: 'whatsapp', phone: '5493516775617', user_id: null };

function routes(plan = PLAN_OK) {
  return {
    'GET /api/v1/plan/features': () => jsonResponse(plan),
    'GET /api/v1/campaigns/plan': () => jsonResponse({ client_id: 'c-1', max_contacts: null }),
    'GET /api/v1/phone-numbers': () => jsonResponse([NUMBER]),
    'GET /api/v1/contacts': () => jsonResponse({ items: [ANA, LUIS, MARTA], total: 3 }),
    'GET /api/v1/contacts/k2': () => jsonResponse(LUIS),
    'GET /api/v1/contacts/k2/campaigns': () => jsonResponse([]),
    'GET /api/v1/contacts/optouts': () =>
      jsonResponse([
        {
          client_id: 'c-1',
          phone: LUIS.phone,
          channel: 'voice',
          source: 'manual',
          created_at: '2026-10-12T12:00:00Z',
        },
      ]),
    'GET /api/v1/blocked-numbers': () =>
      jsonResponse([{ client_id: 'c-1', phone: MARTA.phone, note: '', created_at: '2026-10-12T12:00:00Z' }]),
    // La API filtra por contact_id (llamadas y WhatsApp del contacto).
    'GET /api/v1/calls': () => jsonResponse({ items: [CALL, WHATSAPP, AGENT_CALL], total: 3 }),
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

function renderIn(ui: React.ReactElement, me = CLIENT_USER, path = '/') {
  return renderWithProviders(<></>, {
    me,
    path,
    routes: [{ path: '*', element: <CallProvider>{ui}</CallProvider> }],
  });
}

describe('contactos: llamar', () => {
  beforeEach(() => {
    FakeRoom.all = [];
    stubMediaDevices();
    sessionStorage.clear();
    localStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  it('la agenda llama desde el número de la cuenta y apaga el botón de un bloqueado', async () => {
    const seen = mockApi(routes());
    renderIn(<ContactsPage />);
    const ana = await screen.findByRole('button', { name: 'Llamar a Ana Pérez' });
    // Mientras carga el bloqueo y el número, no se sabe aún; esperar a que quede lista.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Llamar a Marta Ruiz' })).toHaveAttribute('data-disabled'),
    );
    expect(ana).not.toHaveAttribute('data-disabled');

    await userEvent.click(ana);
    await waitFor(() => expect(FakeRoom.all).toHaveLength(1));
    expect(seen.find((s) => s.method === 'POST' && s.path === '/api/v1/direct-calls')?.body).toEqual(
      expect.objectContaining({ contact_id: 'k1', from_number_id: 'n1' }),
    );

    // Con una llamada en curso no se puede empezar otra.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Llamar a Luis Gómez' })).toHaveAttribute('data-disabled'),
    );
  });

  it('sin la función en el plan, el botón queda apagado y no llama', async () => {
    const seen = mockApi(routes(PLAN_FREE));
    renderIn(<ContactsPage />);
    const ana = await screen.findByRole('button', { name: 'Llamar a Ana Pérez' });
    await waitFor(() => expect(ana).toHaveAttribute('data-disabled'));
    await userEvent.click(ana);
    expect(seen.some((s) => s.path === '/api/v1/direct-calls')).toBe(false);
  });

  it('un admin entrando como el cliente (soporte) no puede llamar', async () => {
    const seen = mockApi(routes());
    renderIn(<ContactsPage />, { ...CLIENT_USER, support: true });
    const ana = await screen.findByRole('button', { name: 'Llamar a Ana Pérez' });
    await waitFor(() => expect(ana).toHaveAttribute('data-disabled'));
    await userEvent.hover(ana);
    expect(await screen.findByText(/no se puede llamar ni atender/)).toBeInTheDocument();
    await userEvent.click(ana);
    expect(seen.some((s) => s.path === '/api/v1/direct-calls')).toBe(false);
  });
});

describe('ficha del contacto', () => {
  beforeEach(() => {
    FakeRoom.all = [];
    stubMediaDevices();
    sessionStorage.clear();
    localStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  it('llama, avisa la baja y lista las llamadas del contacto con quién llamó', async () => {
    const seen = mockApi(routes());
    renderWithProviders(<></>, {
      me: CLIENT_USER,
      path: '/contacts/k2',
      routes: [
        {
          path: '/contacts/:id',
          element: (
            <CallProvider>
              <ContactDetailPage />
            </CallProvider>
          ),
        },
      ],
    });
    expect(await screen.findByText(/Pidió no recibir llamadas/)).toBeInTheDocument();

    // Historial: la directa dice quién llamó; la del agente, el agente; la de WhatsApp no está.
    const history = (await screen.findByText('Historial de llamadas')).closest(
      '.mantine-Card-root',
    ) as HTMLElement;
    expect(await within(history).findByText('Llamó: Ana')).toBeInTheDocument();
    expect(within(history).getByText('Cobranzas')).toBeInTheDocument();
    expect(within(history).getByText('Había pedido no recibir llamadas')).toBeInTheDocument();
    expect(within(history).getAllByRole('link', { name: 'Ver conversación' })).toHaveLength(2);
    expect(within(history).getByText('Directa')).toBeInTheDocument();
    expect(seen.some((s) => s.path === '/api/v1/calls' && s.search.includes('contact_id=k2'))).toBe(true);

    const button = screen.getByRole('button', { name: 'Llamar a Luis Gómez' });
    await waitFor(() => expect(button).not.toHaveAttribute('data-disabled'));
    await userEvent.click(button);
    await waitFor(() =>
      expect(seen.find((s) => s.method === 'POST' && s.path === '/api/v1/direct-calls')?.body).toEqual(
        expect.objectContaining({ contact_id: 'k2', from_number_id: 'n1' }),
      ),
    );
  });
});
