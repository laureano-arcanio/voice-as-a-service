import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { PlanFeatures } from '@/api/types';
import { ADMIN, CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { ReportsPage } from './ReportsPage';
import type { SummaryKpis, SummaryReport } from './types';

const KPIS: SummaryKpis = {
  conversations: 12,
  by_channel: { voice: 8, whatsapp: 4, web: 0 },
  conversion_pct: 50,
  goal_pct: 25,
  transfers: 3,
  transfers_answered: 2,
  transfer_pct: 25,
  minutes: 40.5,
  avg_duration: 95,
  rejected_by_limit: 1,
  wa_messages: 30,
};

const SUMMARY: SummaryReport = {
  period: { date_from: '2026-09-28', date_to: '2026-10-27' },
  kpis: KPIS,
  previous: { ...KPIS, conversations: 6 },
  plan: {
    inbound_minutes_used: 40,
    inbound_minutes_quota: 100,
    outbound_minutes_used: 0,
    outbound_minutes_quota: 0,
    projected_inbound_minutes: 120,
    period_start: '2026-10-01T03:00:00Z',
    period_end: '2026-11-01T03:00:00Z',
  },
  daily: [
    { date: '2026-10-26', voice: 5, whatsapp: 1, web: 0, transfers: 2, transfers_answered: 1 },
    { date: '2026-10-27', voice: 3, whatsapp: 3, web: 0, transfers: 1, transfers_answered: 1 },
  ],
};

const plan = (advanced: boolean): PlanFeatures => ({
  client_id: 'c-1',
  tier_name: advanced ? 'Sucursal' : 'Free',
  free: !advanced,
  features: {
    advanced_reports: advanced
      ? { enabled: true, reason: null }
      : { enabled: false, reason: 'Disponible en los planes Mostrador y Sucursal' },
  },
});

/** fetch falso: devuelve por path y anota los pedidos. */
function mockApi(routes: Record<string, unknown>) {
  const urls: URL[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input));
      urls.push(url);
      const body = routes[url.pathname];
      return body === undefined ? jsonResponse({ detail: 'no mockeado' }, 404) : jsonResponse(body);
    }),
  );
  return urls;
}

describe('ReportsPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('Resumen: consultas por día, KPIs con la variación y el consumo del plan', async () => {
    const urls = mockApi({
      '/api/v1/plan/features': plan(true),
      '/api/v1/agents': [],
      '/api/v1/reports/summary': SUMMARY,
    });
    renderWithProviders(<ReportsPage />, { me: CLIENT_USER, path: '/reports' });
    expect(await screen.findByRole('heading', { name: 'Reportes' })).toBeInTheDocument();
    expect(await screen.findByText('Consultas por día')).toBeInTheDocument();
    expect(screen.getByText('Consumo del plan')).toBeInTheDocument();
    // 12 contra 6 del periodo anterior.
    expect(screen.getByText('+100 % vs. período anterior')).toBeInTheDocument();
    expect(screen.getByText(/vas a usar unos 120 minutos entrantes/)).toBeInTheDocument();
    // El cliente no ve las pestañas internas.
    expect(screen.queryByRole('tab', { name: /Técnico/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /Plataforma/ })).not.toBeInTheDocument();

    const req = urls.find((u) => u.pathname === '/api/v1/reports/summary')!;
    expect(req.searchParams.get('date_from')).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(req.searchParams.get('include_tests')).toBeNull();
    expect(req.searchParams.get('tz')).toBeTruthy();
  });

  it('sin advanced_reports: la pestaña muestra el aviso del plan y no pide el reporte', async () => {
    const urls = mockApi({
      '/api/v1/plan/features': plan(false),
      '/api/v1/agents': [],
    });
    renderWithProviders(<ReportsPage />, { me: CLIENT_USER, path: '/reports?tab=outcomes' });
    expect(await screen.findByText('Tu plan Free no incluye el reporte de resultados.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Mejorar mi plan' })).toHaveAttribute('href', '/plan');
    expect(urls.some((u) => u.pathname === '/api/v1/reports/outcomes')).toBe(false);
  });

  it('Descargar CSV exporta los datos del gráfico', async () => {
    mockApi({
      '/api/v1/plan/features': plan(true),
      '/api/v1/agents': [],
      '/api/v1/reports/summary': SUMMARY,
    });
    let blob: Blob | null = null;
    // jsdom no trae createObjectURL: se agrega para la prueba y se saca al final.
    Object.assign(URL, {
      createObjectURL: (b: Blob) => {
        blob = b;
        return 'blob:csv';
      },
      revokeObjectURL: () => {},
    });
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    renderWithProviders(<ReportsPage />, { me: CLIENT_USER, path: '/reports' });
    await screen.findByText('Consultas por día');
    fireEvent.click(screen.getAllByRole('button', { name: 'Descargar CSV' })[0]!);
    expect(click).toHaveBeenCalled();
    const text = await (blob as unknown as Blob).text();
    expect(text).toContain('Fecha,Teléfono,WhatsApp,Web,Transferencias pedidas,Transferencias atendidas');
    expect(text).toContain('2026-10-26,5,1,0,2,1');
    click.mockRestore();
    delete (URL as Partial<typeof URL>).createObjectURL;
    delete (URL as Partial<typeof URL>).revokeObjectURL;
  });

  it('admin con "Todos": pestañas Técnico y Plataforma', async () => {
    mockApi({
      '/api/v1/clients': [],
      '/api/v1/agents': [],
      '/api/v1/reports/summary': { ...SUMMARY, plan: null },
    });
    renderWithProviders(<ReportsPage />, { me: ADMIN, path: '/reports' });
    expect(await screen.findByRole('tab', { name: /Técnico/ })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Plataforma/ })).toBeInTheDocument();
    await screen.findByText('Consultas por día');
    // Sin cliente elegido no hay plan.
    await waitFor(() => expect(screen.queryByText('Consumo del plan')).not.toBeInTheDocument());
  });
});

// Una fila por bloque: alcanza para ver que cada pestaña arma sus tablas y gráficos sin romperse.
const FIXTURES: Record<string, [unknown, string]> = {
  calls: [
    {
      daily: [{ date: '2026-10-27', entrante: 3, saliente: 1, web: 0, prueba: 0 }],
      heatmap: [{ weekday: 0, hour: 10, count: 3 }],
      by_line: [
        { phone_number_id: 'n-1', number: '+541100000000', calls: 3, minutes: 5, conversion_pct: 50 },
      ],
      by_agent: [
        {
          agent_id: 'a-1',
          agent_name: 'Turnos',
          calls: 4,
          minutes: 6,
          avg_duration: 90,
          conversion_pct: 50,
          goal_pct: 25,
        },
      ],
      durations: [{ bucket: '1-3m', count: 4 }],
      ended: [{ reason: 'customer_hangup', count: 4 }],
      early_hangups: 1,
      callers: {
        new: 3,
        returning: 1,
        top: [{ phone: '+5491100000001', count: 2, last_at: '2026-10-27T13:00:00Z' }],
      },
    },
    'Cortó el cliente',
  ],
  outcomes: [
    {
      conversion_daily: [{ date: '2026-10-27', complete: 1, partial: 1, empty: 1 }],
      by_agent: [
        { agent_id: 'a-1', agent_name: 'Turnos', total: 3, complete: 1, partial: 1, empty: 1, goal: 1 },
      ],
      outcomes: [
        {
          agent_id: 'a-1',
          agent_name: 'Turnos',
          outcome: 'turno',
          label: 'Turno dado',
          goal: true,
          count: 1,
        },
      ],
      funnel: { conversations: 3, with_data: 2, complete: 1, goal: 1 },
      fields: [
        {
          agent_id: 'a-1',
          agent_name: 'Turnos',
          field: 'nombre',
          label: 'Nombre',
          captured: 2,
          total: 3,
          pct: 66.7,
        },
      ],
      by_version: [
        { agent_id: 'a-1', agent_name: 'Turnos', version: 3, total: 3, conversion_pct: 33.3, goal_pct: 33.3 },
      ],
    },
    'Turno dado',
  ],
  messages: [
    {
      daily: [
        {
          date: '2026-10-27',
          inbound: 5,
          outbound: 4,
          inbound_audio: 1,
          outbound_audio: 0,
          conversations: 2,
        },
      ],
      heatmap: [{ weekday: 1, hour: 20, count: 5 }],
      delivery: { sent: 4, delivered: 4, read: 3, failed: 0 },
      failures: [{ code: 131026, message: 'Message undeliverable', count: 1 }],
      per_conversation_avg: 4.5,
      conversion: { complete: 1, partial: 0, empty: 1 },
      accounts: [
        {
          account_id: 'w-1',
          display_phone_number: '+54 11 0000-0000',
          status: 'CONNECTED',
          quality_rating: 'GREEN',
          messaging_limit: 'TIER_1K',
          history: [],
        },
      ],
    },
    'Message undeliverable',
  ],
  transfers: [
    {
      kpis: {
        requested: 2,
        answered: 1,
        not_answered: 1,
        unavailable: 0,
        answer_pct: 50,
        avg_answer_seconds: 12,
        minutes: 3,
      },
      daily: [{ date: '2026-10-27', requested: 2, answered: 1 }],
      by_area: [
        { area_id: 'ar-1', name: 'Ventas', requested: 2, answered: 1, not_answered: 1, unavailable: 0 },
      ],
      by_member: [
        {
          team_member_id: 'm-1',
          name: 'Juana',
          attempts: 2,
          answered: 1,
          not_answered: 1,
          avg_answer_seconds: 12,
          minutes: 3,
        },
      ],
      whatsapp: { assigned: 0, first_reply: 0, avg_first_reply_seconds: null, reassigned: 0 },
    },
    'Juana',
  ],
  campaigns: [
    {
      campaigns: [
        {
          campaign_id: 'cp-1',
          name: 'Recordatorio',
          channel: 'voice',
          status: 'done',
          contacts: 10,
          attempts: 12,
          reached: 6,
          complete: 3,
          goal: 2,
          optouts: 1,
          minutes: 8,
        },
      ],
      no_contact: [{ reason: 'busy', count: 2 }],
      best_hours: [{ weekday: 2, hour: 11, attempts: 4, reached: 3 }],
    },
    'Recordatorio',
  ],
  technical: [
    {
      latency_daily: [
        { date: '2026-10-27', p50: 900, p95: 1800, stt_p50: 80, eou_p50: 300, llm_p50: 400, tts_p50: 150 },
      ],
      by_provider: [{ provider: 'propio', model: 'gemma', turns: 20, avg_ms: 400, errors: 0 }],
      tools: [
        {
          tool_id: 't-1',
          slug: 'buscar_turno',
          type: 'http',
          runs: 5,
          errors: 1,
          error_pct: 20,
          p50_ms: 300,
          p95_ms: 900,
          last_error: 'HTTP 500',
          last_error_at: '2026-10-27T12:00:00Z',
        },
      ],
      turns_avg: 6,
      errors: [{ reason: 'timeout', count: 1 }],
      failed_summary_emails: 0,
      tokens: { input: 1000, output: 200, by_day: [{ date: '2026-10-27', input: 1000, output: 200 }] },
    },
    'buscar_turno',
  ],
};

describe('ReportsPage, pestañas con datos', () => {
  afterEach(() => vi.unstubAllGlobals());

  it.each(Object.keys(FIXTURES))('%s', async (tab) => {
    const [body, text] = FIXTURES[tab]!;
    mockApi({
      '/api/v1/clients': [{ id: 'c-1', name: 'Acme' }],
      '/api/v1/agents': [],
      [`/api/v1/reports/${tab}`]: body,
    });
    renderWithProviders(<ReportsPage />, { me: ADMIN, path: `/reports?client=c-1&tab=${tab}` });
    expect(await screen.findByText(text)).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Descargar CSV' }).length).toBeGreaterThan(0);
  });

  it('plataforma: tabla de clientes y alertas', async () => {
    mockApi({
      '/api/v1/clients': [],
      '/api/v1/agents': [],
      '/api/v1/reports/platform': {
        clients: [
          {
            client_id: 'c-1',
            name: 'Acme',
            tier: 'Sucursal',
            conversations: 10,
            minutes: 85,
            quota_pct: 85,
            conversion_pct: 40,
            errors: 0,
            last_activity_at: '2026-10-27T12:00:00Z',
            delta_pct: 10,
          },
        ],
        alerts: [{ client_id: 'c-1', name: 'Acme', kind: 'near_quota', detail: '85 % de los minutos' }],
        business: {
          clients_by_tier: [{ tier: 'Sucursal', count: 1 }],
          signups: [],
          mrr_ars: 29000,
          payments_month_ars: 29000,
          past_due: 0,
          free_to_paid: 1,
        },
        operation: { peak_concurrency: [], failures: [], rejected: [] },
      },
    });
    renderWithProviders(<ReportsPage />, { me: ADMIN, path: '/reports?tab=platform' });
    expect(await screen.findByText('Cerca del cupo')).toBeInTheDocument();
    expect(screen.getAllByText('$ 29.000', { selector: 'p' })).toHaveLength(2);
  });
});
