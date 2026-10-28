import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CallDetail, CallSummary } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { CallDetailPage } from './CallDetailPage';
import { ConversationsPage } from './ConversationsPage';

// Conversaciones con llamadas directas (docs/features/EQUIPO_TELEFONIA.md).

const BASE: CallSummary = {
  id: 'cv-1',
  client_id: 'c-1',
  client_name: 'Acme',
  agent_id: 'ag-1',
  agent_name: 'Ventas',
  agent_version: 1,
  workflow_status: 'completed',
  created_at: '2026-10-27T12:00:00Z',
  contact_name: null,
  company: null,
  outcome: null,
  goal: false,
  captured: 2,
  required: 3,
  mode: 'entrante',
  phone: '+5493515551234',
  status: 'finalizada',
  duration_seconds: 65,
  ended_reason: 'customer_hangup',
  latency_avg: null,
  user_id: null,
  user_name: null,
  answered_by: 'agent',
  opted_out_confirmed: false,
};
const AGENT_CALL: CallSummary = { ...BASE };
const DIRECT: CallSummary = {
  ...BASE,
  id: 'cv-2',
  agent_id: null,
  agent_name: null,
  agent_version: null,
  workflow_status: 'active',
  captured: 0,
  required: 0,
  mode: 'directa',
  user_id: 'u-1',
  user_name: 'Ana',
  answered_by: null,
};
const TEAM: CallSummary = {
  ...DIRECT,
  id: 'cv-3',
  mode: 'entrante',
  user_id: 'u-2',
  user_name: 'Pedro',
  answered_by: 'team',
};

const PLAN_DIRECT = {
  client_id: 'c-1',
  tier_name: 'Sucursal',
  free: false,
  features: { direct_calls: { enabled: true, reason: null } },
};
const PLAN_FREE = {
  client_id: 'c-1',
  tier_name: 'Free',
  free: true,
  features: { direct_calls: { enabled: false, reason: 'Está en los planes Mostrador, Sucursal y Red.' } },
};

function mockApi(routes: Record<string, () => Response>) {
  const urls: URL[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const url = new URL(req.url);
      urls.push(url);
      const route = routes[`${req.method} ${url.pathname}`];
      return route ? route() : jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return urls;
}

const listRoutes = (plan: object = PLAN_DIRECT) => ({
  'GET /api/v1/plan/features': () => jsonResponse(plan),
  'GET /api/v1/calls': () => jsonResponse({ items: [AGENT_CALL, DIRECT, TEAM], total: 3 }),
  'GET /api/v1/agents': () => jsonResponse([]),
  'GET /api/v1/campaigns': () => jsonResponse([]),
  'GET /api/v1/team/presence': () =>
    jsonResponse([
      { user_id: 'u-1', team_member_id: null, name: 'Ana', available: true, busy: false },
      { user_id: 'u-2', team_member_id: null, name: 'Pedro', available: false, busy: false },
    ]),
});

afterEach(() => vi.unstubAllGlobals());

describe('conversaciones: llamadas directas', () => {
  it('la tabla dice el tipo y quién llamó o atendió', async () => {
    mockApi(listRoutes());
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });
    expect(await screen.findByText('Llamó: Ana')).toBeInTheDocument();
    expect(screen.getByText('Atendió: Pedro')).toBeInTheDocument();
    expect(screen.getByText('Entrante del equipo')).toBeInTheDocument();
    const row = (name: RegExp) => screen.getByRole('row', { name });
    // La directa no tiene datos que obtener: raya en vez de 0/0.
    expect(within(row(/Llamó: Ana/)).getByText('Directa')).toBeInTheDocument();
    expect(within(row(/Llamó: Ana/)).queryByText('0/0')).not.toBeInTheDocument();
    // La del agente sigue igual.
    expect(within(row(/Ventas/)).getByText('2/3')).toBeInTheDocument();
  });

  it('filtra por quién atendió y por usuario con los params de la API', async () => {
    const urls = mockApi(listRoutes());
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });
    await screen.findByText('Llamó: Ana');

    await userEvent.click(screen.getByRole('textbox', { name: 'Atendió' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Atendió: Equipo', hidden: true }));
    await waitFor(() =>
      expect(urls.some((u) => u.pathname === '/api/v1/calls' && u.search.includes('answered_by=team'))).toBe(
        true,
      ),
    );

    await userEvent.click(screen.getByRole('textbox', { name: 'Usuario' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Pedro', hidden: true }));
    await waitFor(() =>
      expect(urls.some((u) => u.pathname === '/api/v1/calls' && u.search.includes('user_id=u-2'))).toBe(true),
    );

    await userEvent.click(screen.getByRole('textbox', { name: 'Origen' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Directa', hidden: true }));
    await waitFor(() =>
      expect(urls.some((u) => u.pathname === '/api/v1/calls' && u.search.includes('mode=directa'))).toBe(
        true,
      ),
    );
  });

  it('sin llamadas directas en el plan no hay filtros de equipo', async () => {
    mockApi(listRoutes(PLAN_FREE));
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });
    await screen.findByRole('textbox', { name: 'Origen' });
    await waitFor(() => expect(screen.queryByRole('textbox', { name: 'Atendió' })).not.toBeInTheDocument());
    expect(screen.queryByRole('textbox', { name: 'Usuario' })).not.toBeInTheDocument();
  });
});

const DETAIL: CallDetail = {
  id: 'cv-2',
  client_id: 'c-1',
  client_name: 'Acme',
  agent_id: null,
  agent_name: null,
  agent_version: null,
  created_at: '2026-10-27T12:00:00Z',
  workflow_status: 'active',
  fields: [],
  outcome: null,
  messages: [
    { role: 'assistant', text: 'Hola, te llamo por el turno.', person: 'Ana', recording: 0 },
    { role: 'user', text: 'Hola, sí, decime.', recording: 1 },
  ],
  context: null,
  recordings: [0, 1],
  call: {
    mode: 'directa',
    phone: '+5493515551234',
    status: 'finalizada',
    client_number: '+541155550000',
    ended_reason: 'person_hangup',
    error: '',
    duration_seconds: 95,
    latency: null,
    created_at: '2026-10-27T12:00:00Z',
    started_at: '2026-10-27T12:00:05Z',
    ended_at: '2026-10-27T12:01:40Z',
    user_id: 'u-1',
    user_name: 'Ana',
    answered_by: null,
    opted_out_confirmed: true,
  },
  whatsapp: null,
};

function renderDetail(detail: CallDetail) {
  mockApi({ 'GET /api/v1/calls/cv-2': () => jsonResponse(detail) });
  return renderWithProviders(<></>, {
    me: CLIENT_USER,
    path: '/calls/cv-2',
    routes: [{ path: '/calls/:id', element: <CallDetailPage /> }],
  });
}

describe('detalle de una llamada directa', () => {
  it('dice quién llamó, avisa la baja confirmada y rotula el chat sin agente', async () => {
    renderDetail(DETAIL);
    expect(await screen.findByText('Llamó')).toBeInTheDocument();
    expect(screen.getAllByText('Ana').length).toBeGreaterThan(0);
    expect(screen.getByText('Directa')).toBeInTheDocument();
    expect(screen.getByText('Contacto que pidió no recibir llamadas')).toBeInTheDocument();
    expect(screen.getByText(/lo confirmó Ana/)).toBeInTheDocument();
    // Sin agente no hay datos, resultado ni "Incompleto".
    expect(screen.queryByText('Agente')).not.toBeInTheDocument();
    expect(screen.queryByText('Datos obtenidos')).not.toBeInTheDocument();
    expect(screen.queryByText('Incompleto')).not.toBeInTheDocument();
    // El otro lado es el contacto, no "Interesado".
    expect(screen.getByText('Ana (equipo)')).toBeInTheDocument();
    expect(screen.getByText('Contacto', { selector: '.who' })).toBeInTheDocument();
    expect(screen.queryByText('Interesado')).not.toBeInTheDocument();
  });

  it('entrante que atendió el equipo: "Atendió" y "Quien llamó"', async () => {
    renderDetail({
      ...DETAIL,
      call: {
        ...DETAIL.call!,
        mode: 'entrante',
        answered_by: 'team',
        user_name: 'Pedro',
        opted_out_confirmed: false,
      },
    });
    expect(await screen.findByText('Atendió')).toBeInTheDocument();
    expect(screen.getByText('Pedro')).toBeInTheDocument();
    expect(screen.getByText('Entrante del equipo')).toBeInTheDocument();
    expect(screen.getByText('Quien llamó', { selector: '.who' })).toBeInTheDocument();
    expect(screen.queryByText('Contacto que pidió no recibir llamadas')).not.toBeInTheDocument();
  });

  it('entrante del equipo que nadie atendió: "Nadie atendió", el respaldo y el contacto de la agenda', async () => {
    renderDetail({
      ...DETAIL,
      call: {
        ...DETAIL.call!,
        mode: 'entrante',
        answered_by: 'team',
        user_id: null,
        user_name: null,
        opted_out_confirmed: false,
        ended_reason: 'team_no_answer',
        contact_id: 'k2',
        contact_name: 'Luis Gómez',
        team: { answered: false, person: null, fallback: 'voicemail' },
      },
    });
    expect(await screen.findByText('Nadie atendió')).toBeInTheDocument();
    expect(screen.getByText('Tomó un mensaje')).toBeInTheDocument();
    expect(screen.queryByText('Atendió')).not.toBeInTheDocument();
    expect(screen.getByText('Luis Gómez')).toBeInTheDocument();
  });

  it('respaldo al agente: el agente y "Nadie atendió"', async () => {
    renderDetail({
      ...DETAIL,
      agent_id: 'ag-1',
      agent_name: 'Recepción',
      agent_version: 2,
      call: {
        ...DETAIL.call!,
        mode: 'entrante',
        answered_by: 'agent',
        user_id: null,
        user_name: null,
        opted_out_confirmed: false,
        team: { answered: false, person: null, fallback: 'agent' },
      },
    });
    expect(await screen.findByText('Nadie atendió')).toBeInTheDocument();
    expect(screen.getByText('Pasó al agente')).toBeInTheDocument();
    expect(screen.getByText('Recepción')).toBeInTheDocument();
  });

  it('entrante que atendió alguien en su celular sin usuario del panel', async () => {
    renderDetail({
      ...DETAIL,
      call: {
        ...DETAIL.call!,
        mode: 'entrante',
        answered_by: 'team',
        user_id: null,
        user_name: null,
        opted_out_confirmed: false,
        team: { answered: true, person: 'Juan', fallback: null },
      },
    });
    expect(await screen.findByText('Atendió')).toBeInTheDocument();
    expect(screen.getByText('Juan')).toBeInTheDocument();
  });

  it('una llamada con agente sigue como antes', async () => {
    renderDetail({
      ...DETAIL,
      agent_id: 'ag-1',
      agent_name: 'Ventas',
      agent_version: 2,
      workflow_status: 'completed',
      call: { ...DETAIL.call!, mode: 'entrante', answered_by: 'agent', user_id: null, user_name: null },
      messages: [{ role: 'user', text: 'Hola' }],
    });
    expect(await screen.findByText('Datos obtenidos')).toBeInTheDocument();
    expect(screen.getByText('Ventas')).toBeInTheDocument();
    expect(screen.getByText('Interesado')).toBeInTheDocument();
  });
});
