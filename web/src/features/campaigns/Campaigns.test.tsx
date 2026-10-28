import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Campaign, CampaignPlan, WaAccount } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { CampaignDetailPage } from './CampaignDetailPage';
import { CampaignsPage } from './CampaignsPage';
import { formatEta, formatWeekdays, csvHelp, renderTemplate } from './labels';
import { isoToLocal, localToIso } from './schedule';
import { VoiceCampaignModal } from './VoiceCampaignModal';

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
  routes: [],
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
};

const BASE = {
  client_id: 'c-1',
  client_name: 'Acme',
  agent_id: null,
  agent_name: 'Ventas',
  status_reason: null,
  in_window: true,
  rate_per_minute: 20,
  window_start: 9,
  window_end: 20,
  weekdays: null,
  timezone: 'America/Argentina/Buenos_Aires',
  starts_at: null,
  ends_at: null,
  percent: 60,
  eta_minutes: null,
  started_at: null,
  finished_at: null,
  created_at: '2026-10-07T12:00:00Z',
  updated_at: '2026-10-07T12:00:00Z',
} as const;

const WA: Campaign = {
  ...BASE,
  id: 'cmp-1',
  channel: 'whatsapp',
  name: 'Prospectos octubre',
  status: 'draft',
  account_id: 'wa-1',
  display_phone_number: '+54 351 555 0000',
  template_name: 'demo',
  template_language: 'es_AR',
  template_category: 'MARKETING',
  template_body: 'Hola {{1}}, probá la demo.',
  template_params: 1,
  total: 10,
  progress: { pending: 4, in_progress: 0, retry: 0, done: 6, failed: 0, skipped: 0 },
  results: { sent: 6, delivered: 5, read: 3, replied: 2 },
};

const VOICE: Campaign = {
  ...BASE,
  id: 'cmp-2',
  channel: 'voice',
  name: 'Cobranza octubre',
  agent_id: 'ag-2',
  agent_name: 'Cobranzas',
  status: 'running',
  weekdays: [0, 1, 2, 3, 4],
  concurrency: 3,
  max_attempts: 3,
  retry_minutes: 60,
  retry_on: ['no_answer', 'busy'],
  purpose: 'cobranza',
  total: 20,
  percent: 50,
  eta_minutes: 95,
  progress: { pending: 6, in_progress: 2, retry: 2, done: 8, failed: 2, skipped: 0 },
  results: { answered: 6, no_answer: 2, busy: 0, voicemail: 0, invalid: 1, rejected: 1, failed: 1 },
  goal: 3,
  minutes_used: 21.5,
};

const PLAN: CampaignPlan = {
  client_id: 'c-1',
  tier_name: 'Pro',
  channels: ['whatsapp', 'voice'],
  followup: false,
  max_campaigns_per_month: 5,
  campaigns_started: 1,
  max_campaign_contacts: 500,
  max_campaign_concurrency: 4,
  max_contacts: 1000,
  contacts_active: 120,
};

interface Seen {
  method: string;
  path: string;
  search: string;
  body?: unknown;
}

function mockApi(routes: Record<string, () => Response>) {
  const calls: Seen[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const url = new URL(req.url);
      const body = ['POST', 'PATCH'].includes(req.method)
        ? await req
            .clone()
            .json()
            .catch(() => undefined)
        : undefined;
      calls.push({ method: req.method, path: url.pathname, search: url.search, body });
      const route = routes[`${req.method} ${url.pathname}`];
      return route ? route() : jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return calls;
}

const listRoutes = (rows: Campaign[], plan: CampaignPlan = PLAN) => ({
  'GET /api/v1/campaigns': () => jsonResponse(rows),
  'GET /api/v1/campaigns/plan': () => jsonResponse(plan),
  'GET /api/v1/whatsapp/accounts': () => jsonResponse([ACCOUNT]),
  'GET /api/v1/contacts/optouts': () =>
    jsonResponse([
      {
        client_id: 'c-1',
        phone: '+5493515551234',
        channel: 'whatsapp',
        source: 'keyword',
        created_at: '2026-10-07T13:00:00Z',
      },
    ]),
});

afterEach(() => vi.unstubAllGlobals());

describe('campañas: helpers', () => {
  it('texto de la plantilla, ayuda del CSV, días y tiempos', () => {
    expect(renderTemplate('Hola {{1}}, {{2}}', ['Ana'])).toBe('Hola Ana, {{2}}');
    expect(csvHelp(2)).toContain('telefono,nombre');
    expect(csvHelp(0)).not.toContain('{{1}}');
    expect(formatWeekdays(null)).toBe('Todos los días');
    expect(formatWeekdays([0, 1, 2, 3, 4])).toBe('Lun a vie');
    expect(formatWeekdays([0, 2, 4])).toBe('Lun, mié y vie');
    expect(formatEta(95)).toBe('1 h 35 min');
    expect(formatEta(30)).toBe('30 min');
  });

  it('las fechas de inicio y fin se escriben en la hora de la campaña', () => {
    expect(localToIso('2026-10-20T09:30', 'America/Argentina/Buenos_Aires')).toBe('2026-10-20T12:30:00.000Z');
    expect(isoToLocal('2026-10-20T12:30:00Z', 'America/Argentina/Buenos_Aires')).toBe('2026-10-20T09:30');
    expect(localToIso('')).toBeNull();
    expect(isoToLocal(null)).toBe('');
  });
});

describe('campañas: lista', () => {
  it('cliente: WhatsApp y llamadas juntas, con canal, avance y bajas por canal', async () => {
    mockApi(listRoutes([WA, VOICE]));
    renderWithProviders(<CampaignsPage />, { me: CLIENT_USER });
    expect(await screen.findByRole('link', { name: 'Prospectos octubre' })).toHaveAttribute(
      'href',
      '/campaigns/cmp-1',
    );
    expect(screen.getByRole('link', { name: 'Cobranza octubre' })).toHaveAttribute(
      'href',
      '/campaigns/cmp-2',
    );
    expect(screen.getByText('6 / 10')).toBeInTheDocument();
    expect(screen.getByText('10 / 20')).toBeInTheDocument();
    expect(screen.getByText('Borrador')).toBeInTheDocument();
    expect(screen.getByText('En curso')).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Cliente' })).not.toBeInTheDocument();
    expect(await screen.findByText('+5493515551234')).toBeInTheDocument();
    expect(screen.getByText('Lo pidió por WhatsApp')).toBeInTheDocument();
  });

  it('filtra por canal', async () => {
    const calls = mockApi(listRoutes([VOICE]));
    renderWithProviders(<CampaignsPage />, { me: CLIENT_USER });
    await screen.findByRole('link', { name: 'Cobranza octubre' });
    await userEvent.click(screen.getByRole('radio', { name: 'Llamadas', hidden: true }));
    await waitFor(() =>
      expect(calls.some((c) => c.path === '/api/v1/campaigns' && c.search.includes('channel=voice'))).toBe(
        true,
      ),
    );
  });

  it('el plan sin un canal lo deshabilita con el motivo', async () => {
    mockApi(listRoutes([], { ...PLAN, channels: ['whatsapp'] }));
    renderWithProviders(<CampaignsPage />, { me: CLIENT_USER });
    await screen.findByText(/No hay campañas/);
    await waitFor(() => expect(screen.getByRole('button', { name: /Nueva campaña/ })).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /Nueva campaña/ }));
    expect(await screen.findByText('Tu plan (Pro) no incluye campañas por llamadas')).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /Por llamadas/, hidden: true })).toBeDisabled();
    expect(screen.getByRole('menuitem', { name: /Por WhatsApp/, hidden: true })).not.toBeDisabled();
  });

  it('sin ningún canal en el plan no deja crear', async () => {
    mockApi(listRoutes([], { ...PLAN, channels: [] }));
    renderWithProviders(<CampaignsPage />, { me: CLIENT_USER });
    expect(await screen.findByText(/no incluye campañas por llamadas/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Nueva campaña/ })).toHaveAttribute('data-disabled', 'true');
  });

  it('sin numero propio conectado no deja crear la de WhatsApp', async () => {
    mockApi({
      ...listRoutes([], { ...PLAN, channels: ['whatsapp'] }),
      'GET /api/v1/whatsapp/accounts': () => jsonResponse([{ ...ACCOUNT, has_token: false }]),
    });
    renderWithProviders(<CampaignsPage />, { me: CLIENT_USER });
    await screen.findByRole('button', { name: /Nueva campaña/ });
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Nueva campaña/ })).toHaveAttribute('data-disabled', 'true'),
    );
    await userEvent.hover(screen.getByRole('button', { name: /Nueva campaña/ }));
    expect(await screen.findByText(/Hace falta un número de WhatsApp conectado/)).toBeInTheDocument();
  });
});

function renderDetail(id: string) {
  return renderWithProviders(<CampaignDetailPage />, {
    me: CLIENT_USER,
    path: `/campaigns/${id}`,
    routes: [{ path: '/campaigns/:id', element: <CampaignDetailPage /> }],
  });
}

describe('campañas: detalle de WhatsApp', () => {
  it('muestra los totales y los contactos, e inicia el envío', async () => {
    const calls = mockApi({
      'GET /api/v1/campaigns/cmp-1': () => jsonResponse(WA),
      'GET /api/v1/campaigns/cmp-1/contacts': () =>
        jsonResponse({
          total: 1,
          items: [
            {
              id: 'r1',
              contact_id: 'k1',
              phone: '+5493515551234',
              name: 'Ana',
              vars: { params: ['Ana'] },
              status: 'done',
              result: 'replied',
              error: null,
              conversation_id: 'conv-1',
              attempts: 0,
              sent_at: '2026-10-07T13:00:00Z',
              replied_at: '2026-10-07T13:05:00Z',
            },
          ],
        }),
      'POST /api/v1/campaigns/cmp-1/start': () => jsonResponse({ ...WA, status: 'running' }),
    });
    renderDetail('cmp-1');
    expect(await screen.findByText('Hola Ana, probá la demo.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ver conversación' })).toHaveAttribute('href', '/calls/conv-1');
    expect(
      within(screen.getByRole('row', { name: /5493515551234/ })).getByText('Respondió'),
    ).toBeInTheDocument();
    expect(screen.getByText('9 a 20 h')).toBeInTheDocument();
    expect(screen.getByText('Todos los días')).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: '60 % procesado' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Iniciar envío/ }));
    await waitFor(() =>
      expect(calls.some((c) => c.method === 'POST' && c.path === '/api/v1/campaigns/cmp-1/start')).toBe(true),
    );
  });

  it('retoma una pausada con resume', async () => {
    const calls = mockApi({
      'GET /api/v1/campaigns/cmp-1': () =>
        jsonResponse({ ...WA, status: 'paused', status_reason: 'Meta pausó la plantilla' }),
      'GET /api/v1/campaigns/cmp-1/contacts': () => jsonResponse({ total: 0, items: [] }),
      'POST /api/v1/campaigns/cmp-1/resume': () => jsonResponse({ ...WA, status: 'running' }),
    });
    renderDetail('cmp-1');
    expect(await screen.findByText('Meta pausó la plantilla')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Retomar' }));
    await waitFor(() => expect(calls.some((c) => c.path.endsWith('/resume'))).toBe(true));
  });
});

const VOICE_STATS = {
  campaign_id: 'cmp-2',
  channel: 'voice',
  contacts: 20,
  attempts: 12,
  reached: 6,
  contact_rate: 50,
  goal: 3,
  goal_rate: 50,
  avg_duration_seconds: 95,
  minutes: 21.5,
  results: {},
  by_hour: [
    { hour: 9, attempts: 5, reached: 3 },
    { hour: 10, attempts: 7, reached: 3 },
  ],
  timezone: 'America/Argentina/Buenos_Aires',
};

const voiceRoutes = (c: Campaign = VOICE) => ({
  'GET /api/v1/campaigns/cmp-2': () => jsonResponse(c),
  'GET /api/v1/campaigns/cmp-2/stats': () => jsonResponse(VOICE_STATS),
  'GET /api/v1/campaigns/cmp-2/contacts': () =>
    jsonResponse({
      total: 2,
      items: [
        {
          id: 'r1',
          contact_id: 'k1',
          phone: '+5493515550001',
          name: 'Luis',
          vars: {},
          status: 'done',
          result: 'answered',
          error: null,
          conversation_id: 'conv-9',
          attempts: 1,
          last_attempt_at: '2026-10-19T13:00:00Z',
        },
        {
          id: 'r2',
          contact_id: 'k2',
          phone: '+5493515550002',
          name: null,
          vars: {},
          status: 'retry',
          result: 'no_answer',
          error: null,
          conversation_id: null,
          attempts: 2,
          next_attempt_at: '2026-10-19T15:00:00Z',
          last_attempt_at: '2026-10-19T14:00:00Z',
        },
      ],
    }),
});

describe('campañas: detalle de llamadas', () => {
  it('avance, resultados, indicadores, reporte y contactos con su intento', async () => {
    const calls = mockApi({
      ...voiceRoutes(),
      'POST /api/v1/campaigns/cmp-2/pause': () => jsonResponse({ ...VOICE, status: 'paused' }),
    });
    renderDetail('cmp-2');
    expect(await screen.findByText('Llamadas del agente Cobranzas')).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: '50 % procesado' })).toBeInTheDocument();
    expect(screen.getByText(/Faltan 1 h 35 min/)).toBeInTheDocument();
    for (const label of ['Atendió', 'No atendió', 'Ocupado', 'Contestador', 'Número inválido', 'Rechazó'])
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    expect(screen.getByText('Cumplieron el objetivo')).toBeInTheDocument();
    expect(await screen.findByText('Tasa de contacto')).toBeInTheDocument();
    expect(screen.getByRole('listitem', { name: '9 h: 3 de 5 atendidas' })).toBeInTheDocument();
    expect(screen.getByText('Lun a vie')).toBeInTheDocument();
    expect(screen.getByText('En paralelo (3 a la vez)')).toBeInTheDocument();

    expect(screen.getByRole('link', { name: /Descargar reporte/ })).toHaveAttribute(
      'href',
      '/api/v1/campaigns/cmp-2/report.csv',
    );
    const retry = await screen.findByRole('row', { name: /5493515550002/ });
    expect(within(retry).getByText('No atendió')).toBeInTheDocument();
    expect(within(retry).getByText(/Reintenta/)).toBeInTheDocument();
    expect(within(retry).getByText('2 / 3')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ver conversación' })).toHaveAttribute('href', '/calls/conv-9');

    await userEvent.click(screen.getByRole('button', { name: 'Pausar' }));
    await waitFor(() => expect(calls.some((c) => c.path.endsWith('/pause'))).toBe(true));
  });

  it('filtra los contactos por resultado', async () => {
    const calls = mockApi(voiceRoutes());
    renderDetail('cmp-2');
    await screen.findByRole('row', { name: /5493515550002/ });
    await userEvent.click(screen.getByRole('textbox', { name: 'Filtrar por estado' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Ocupado', hidden: true }));
    await waitFor(() =>
      expect(calls.some((c) => c.path.endsWith('/contacts') && c.search.includes('result=busy'))).toBe(true),
    );
  });

  it('una comercial pide confirmar el Registro No Llame antes de iniciar', async () => {
    const draft = { ...VOICE, status: 'draft', purpose: 'comercial', registry_confirmed: false } as Campaign;
    const calls = mockApi({
      ...voiceRoutes(draft),
      'POST /api/v1/campaigns/cmp-2/start': () => jsonResponse({ ...draft, status: 'running' }),
    });
    renderDetail('cmp-2');
    expect(await screen.findByText('Falta confirmar el Registro No Llame')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Iniciar campaña' }));
    const dialog = await screen.findByRole('dialog', { name: /Iniciar Cobranza octubre/ });
    const confirm = within(dialog).getByRole('button', { name: 'Iniciar campaña' });
    expect(confirm).toBeDisabled();
    expect(calls.some((c) => c.method === 'POST')).toBe(false);
    await userEvent.click(within(dialog).getByRole('checkbox'));
    await userEvent.click(confirm);
    await waitFor(() => expect(calls.some((c) => c.method === 'POST')).toBe(true));
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ no_call_registry_checked: true });
  });

  it('una programada avisa cuándo arranca', async () => {
    mockApi(voiceRoutes({ ...VOICE, status: 'scheduled', starts_at: '2026-10-21T12:00:00Z' }));
    renderDetail('cmp-2');
    expect(await screen.findByText(/Arranca sola el/)).toBeInTheDocument();
    expect(screen.getByText('Programada')).toBeInTheDocument();
  });
});

describe('campañas: alta de llamadas', () => {
  const routes = (plan: CampaignPlan = PLAN) => ({
    'GET /api/v1/campaigns/plan': () => jsonResponse(plan),
    'GET /api/v1/agents': () =>
      jsonResponse([{ id: 'ag-2', client_id: 'c-1', name: 'Cobranzas', archived: false }]),
    'GET /api/v1/phone-numbers': () =>
      jsonResponse([{ id: 'n-1', e164: '+5493515559999', label: 'Cobranzas', client_id: 'c-1' }]),
    'GET /api/v1/voices': () => jsonResponse([{ nombre: 'sofia', genero: 'mujer', wer: null, car_s: null }]),
    'GET /api/v1/whatsapp/accounts': () => jsonResponse([ACCOUNT]),
    'GET /api/v1/contacts': () =>
      jsonResponse({
        total: 1,
        items: [
          {
            id: 'k1',
            client_id: 'c-1',
            phone: '+5493515551234',
            name: 'Ana',
            email: null,
            notes: null,
            source: 'manual',
            archived_at: null,
            created_at: '2026-10-01T12:00:00Z',
            updated_at: '2026-10-01T12:00:00Z',
          },
        ],
      }),
    'POST /api/v1/campaigns': () =>
      jsonResponse({ added: 3, skipped: [], campaign: { ...VOICE, status: 'draft', id: 'cmp-9' } }, 201),
  });

  async function fillBasics(name = 'Mora octubre') {
    await userEvent.type(await screen.findByLabelText('Nombre'), name);
    await userEvent.click(screen.getByRole('textbox', { name: 'Agente que llama' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Cobranzas', hidden: true }));
    await userEvent.click(await screen.findByRole('checkbox', { name: 'Elegir Ana' }));
  }

  it('crea el borrador con los contactos elegidos, el horario y los reintentos', async () => {
    const calls = mockApi(routes());
    renderWithProviders(<VoiceCampaignModal onClose={() => {}} />, { me: CLIENT_USER });
    await fillBasics();
    await userEvent.click(screen.getByRole('button', { name: 'Guardar borrador' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'POST')).toBe(true));
    expect(calls.find((c) => c.method === 'POST')?.body).toMatchObject({
      channel: 'voice',
      name: 'Mora octubre',
      agent_id: 'ag-2',
      contact_ids: ['k1'],
      start: false,
      concurrency: 1,
      window_start: 9,
      window_end: 20,
      weekdays: [0, 1, 2, 3, 4],
      max_attempts: 3,
      retry_minutes: 60,
      retry_on: ['no_answer', 'busy', 'voicemail', 'failed'],
      followup: null,
      starts_at: null,
    });
    expect(await screen.findByText('Campaña creada')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ver campaña' })).toBeInTheDocument();
  });

  it('en paralelo, con tope del plan, inicio programado y webhook', async () => {
    const calls = mockApi(routes());
    renderWithProviders(<VoiceCampaignModal onClose={() => {}} />, { me: CLIENT_USER });
    await fillBasics();
    expect(screen.getByText(/hasta 4 llamadas a la vez/)).toBeInTheDocument();
    await userEvent.click(screen.getByText('En paralelo'));
    const n = screen.getByRole('textbox', { name: 'Llamadas a la vez' });
    expect(n).toHaveValue('2');
    await userEvent.clear(n);
    await userEvent.type(n, '4');
    await userEvent.type(screen.getByLabelText('Inicio programado'), '2099-10-20T09:30');
    await userEvent.type(screen.getByLabelText('URL del webhook'), 'https://hooks.acme.com/a');
    await userEvent.click(screen.getByRole('button', { name: 'Crear y programar' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'POST')).toBe(true));
    expect(calls.find((c) => c.method === 'POST')?.body).toMatchObject({
      concurrency: 4,
      start: true,
      starts_at: '2099-10-20T12:30:00.000Z',
      callback_url: 'https://hooks.acme.com/a',
    });
  });

  it('una comercial no se inicia sin confirmar el Registro No Llame, pero sí se guarda', async () => {
    const calls = mockApi(routes());
    renderWithProviders(<VoiceCampaignModal onClose={() => {}} />, { me: CLIENT_USER });
    await fillBasics();
    await userEvent.click(screen.getByRole('textbox', { name: 'Finalidad' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Comercial', hidden: true }));
    const start = screen.getByRole('button', { name: 'Crear e iniciar' });
    expect(start).toHaveAttribute('data-disabled', 'true');
    await userEvent.click(start);
    expect(calls.some((c) => c.method === 'POST')).toBe(false);
    await userEvent.click(screen.getByRole('checkbox', { name: /Registro No Llame/ }));
    expect(screen.getByRole('button', { name: 'Crear e iniciar' })).not.toHaveAttribute('data-disabled');
    await userEvent.click(screen.getByRole('button', { name: 'Crear e iniciar' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'POST')).toBe(true));
    expect(calls.find((c) => c.method === 'POST')?.body).toMatchObject({
      purpose: 'comercial',
      no_call_registry_checked: true,
      start: true,
    });
  });

  it('sin destinatarios no crea', async () => {
    const calls = mockApi(routes());
    renderWithProviders(<VoiceCampaignModal onClose={() => {}} />, { me: CLIENT_USER });
    await userEvent.type(await screen.findByLabelText('Nombre'), 'Vacía');
    await userEvent.click(screen.getByRole('textbox', { name: 'Agente que llama' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Cobranzas', hidden: true }));
    await userEvent.click(screen.getByRole('button', { name: 'Guardar borrador' }));
    expect(
      await screen.findByText('Elegí a quién llamar: contactos de la agenda o un CSV.'),
    ).toBeInTheDocument();
    expect(calls.some((c) => c.method === 'POST')).toBe(false);
  });

  it('el plan sin llamadas, sin seguimiento y con el mes agotado, lo deshabilita con el motivo', async () => {
    mockApi(routes({ ...PLAN, channels: ['voice'], followup: false, campaigns_started: 5 }));
    renderWithProviders(<VoiceCampaignModal onClose={() => {}} />, { me: CLIENT_USER });
    await screen.findByLabelText('Nombre');
    expect(screen.getByRole('switch', { name: /Escribirle por WhatsApp/ })).toBeDisabled();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Crear e iniciar' })).toHaveAttribute(
        'data-disabled',
        'true',
      ),
    );
    expect(screen.getByRole('button', { name: 'Guardar borrador' })).not.toBeDisabled();
  });

  it('un plan sin llamadas avisa y bloquea el formulario', async () => {
    mockApi(routes({ ...PLAN, channels: ['whatsapp'] }));
    renderWithProviders(<VoiceCampaignModal onClose={() => {}} />, { me: CLIENT_USER });
    expect(await screen.findByText(/no incluye campañas por llamadas/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Guardar borrador' })).toBeDisabled();
  });
});
