import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CallSummary } from '@/api/types';
import { ADMIN, CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { notifyError, notifyInfo, notifySuccess } from '@/lib/notify';
import { ConversationsPage } from './ConversationsPage';

vi.mock('@/lib/notify', () => ({
  notifyError: vi.fn(),
  notifySuccess: vi.fn(),
  notifyInfo: vi.fn(),
}));

const CALL: CallSummary = {
  id: 'cv-1',
  client_id: 'c-1',
  client_name: 'Acme',
  agent_id: 'ag-1',
  agent_name: 'Ventas',
  agent_version: 1,
  workflow_status: 'completed',
  created_at: '2026-10-12T12:00:00Z',
  contact_name: 'Ana',
  company: 'Acme SA',
  outcome: 'Fuera de tema',
  captured: 3,
  total: 3,
  mode: 'saliente',
  phone: '+5491155551234',
  status: 'finalizada',
  duration_seconds: 65,
  ended_reason: 'completed',
  latency_avg: 1.2,
};

function mockApi(routes: Record<string, () => Response>) {
  const calls: { method: string; path: string; body?: unknown }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const path = new URL(req.url).pathname;
      // Un POST sin cuerpo (el analyze) no lleva JSON: queda en undefined.
      const body = req.method === 'POST' ? await req.clone().json().catch(() => undefined) : undefined;
      calls.push({ method: req.method, path, body });
      const route = routes[`${req.method} ${path}`];
      return route ? route() : jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return calls;
}

const listRoutes = (items: CallSummary[], deleted = 1) => ({
  'GET /api/v1/calls': () => jsonResponse({ items, total: items.length }),
  'GET /api/v1/agents': () => jsonResponse([]),
  'GET /api/v1/clients': () => jsonResponse([]),
  'POST /api/v1/calls/bulk-delete': () => jsonResponse({ deleted }),
});

afterEach(() => vi.unstubAllGlobals());

describe('conversaciones', () => {
  it('admin: selecciona y borra en bulk, confirmando antes', async () => {
    const calls = mockApi(listRoutes([CALL]));
    renderWithProviders(<ConversationsPage />, { me: ADMIN });

    const row = await screen.findByRole('checkbox', { name: /Seleccionar conversación/ });
    await userEvent.click(row);
    expect(screen.getByText('1 seleccionada')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Borrar seleccionadas' }));
    const dialog = await screen.findByRole('dialog', { name: 'Borrar conversación' });
    expect(within(dialog).getByText(/No se puede deshacer/)).toBeInTheDocument();
    // Cancelar no borra nada.
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }));
    expect(calls.some((c) => c.method === 'POST')).toBe(false);

    await userEvent.click(screen.getByRole('button', { name: 'Borrar seleccionadas' }));
    const again = await screen.findByRole('dialog', { name: 'Borrar conversación' });
    await userEvent.click(within(again).getByRole('button', { name: 'Borrar' }));
    await waitFor(() =>
      expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/bulk-delete'))).toBe(true),
    );
    const post = calls.find((c) => c.method === 'POST');
    expect(post?.body).toEqual({ ids: ['cv-1'] });
  });

  it('admin: el icono de la fila borra esa conversación, con confirmación', async () => {
    const calls = mockApi(listRoutes([CALL]));
    renderWithProviders(<ConversationsPage />, { me: ADMIN });

    await userEvent.click(await screen.findByRole('button', { name: 'Borrar conversación' }));
    const dialog = await screen.findByRole('dialog', { name: 'Borrar conversación' });
    expect(within(dialog).getByText(/Se borra la conversación/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Borrar' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'POST')).toBe(true));
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ ids: ['cv-1'] });
  });

  it('cliente: sin selección ni borrado', async () => {
    mockApi(listRoutes([CALL]));
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });

    expect(await screen.findByRole('link', { name: /Ver conversación del/ })).toHaveAttribute('href', '/calls/cv-1');
    expect(screen.queryByRole('tab')).not.toBeInTheDocument();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Borrar conversación' })).not.toBeInTheDocument();
  });

  it('admin: cliente y empresa en sus columnas, con los datos extraídos', async () => {
    mockApi(listRoutes([CALL]));
    renderWithProviders(<ConversationsPage />, { me: ADMIN });

    const row = await screen.findByRole('row', { name: /Acme SA/ });
    const table = screen.getByRole('table');
    expect(screen.getByRole('columnheader', { name: 'Cliente' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Empresa' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Atendió' })).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Atendió y cliente' })).not.toBeInTheDocument();
    expect(within(row).getByText('Acme')).toBeInTheDocument();
    expect(within(row).getByText('Acme SA')).toBeInTheDocument();
    expect(within(row).getByText('1:05')).toBeInTheDocument();
    // Estado: 3/3 datos con el punto verde; el resultado y el estado de la llamada ya no están.
    expect(within(row).getByText('3/3')).toBeInTheDocument();
    expect(within(row).getByRole('img', { name: 'Todos los datos extraídos' })).toBeInTheDocument();
    expect(within(table).queryByText('Fuera de tema')).not.toBeInTheDocument();
    expect(within(table).queryByText('Finalizada')).not.toBeInTheDocument();
  });

  it('cliente: sin Cliente ni Empresa, con la fecha, la duración y los datos extraídos', async () => {
    mockApi(listRoutes([CALL]));
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });

    await screen.findByRole('link', { name: /Ver conversación del/ });
    expect(screen.getByRole('columnheader', { name: 'Atendió' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Estado' })).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Cliente' })).not.toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Empresa' })).not.toBeInTheDocument();
    expect(screen.queryByText('Acme')).not.toBeInTheDocument();
    expect(screen.queryByText('Acme SA')).not.toBeInTheDocument();
    expect(screen.getByText('1:05')).toBeInTheDocument();
    expect(screen.getByText('3/3')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Todos los datos extraídos' })).toBeInTheDocument();
  });

  it('el punto del estado va con los datos extraídos y no aparece si no hay datos que extraer', async () => {
    mockApi(
      listRoutes([
        { ...CALL, id: 'cv-full', contact_name: 'Ana', captured: 3, total: 3 },
        { ...CALL, id: 'cv-some', contact_name: 'Beto', captured: 1, total: 3 },
        { ...CALL, id: 'cv-none', contact_name: 'Caro', captured: 0, total: 3 },
        { ...CALL, id: 'cv-empty', contact_name: 'Dani', captured: 0, total: 0 },
      ]),
    );
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });

    const row = (contact: string) => screen.getByRole('row', { name: new RegExp(contact) });
    await screen.findByText('3/3');
    expect(within(row('Ana')).getByText('3/3')).toBeInTheDocument();
    expect(within(row('Ana')).getByRole('img', { name: 'Todos los datos extraídos' })).toBeInTheDocument();
    expect(within(row('Beto')).getByText('1/3')).toBeInTheDocument();
    expect(within(row('Beto')).getByRole('img', { name: 'Faltan datos por extraer' })).toBeInTheDocument();
    expect(within(row('Caro')).getByText('0/3')).toBeInTheDocument();
    expect(within(row('Caro')).getByRole('img', { name: 'No se extrajo ningún dato' })).toBeInTheDocument();
    // Sin campos de análisis (total 0): raya y ningún círculo.
    expect(within(row('Dani')).queryByText('0/0')).not.toBeInTheDocument();
    expect(within(row('Dani')).queryByRole('img')).not.toBeInTheDocument();
    expect(within(row('Dani')).getByText('–')).toBeInTheDocument();
  });

  it('una llamada en curso muestra En vivo al lado de la duración', async () => {
    mockApi(listRoutes([{ ...CALL, status: 'en_curso' }]));
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });

    const row = await screen.findByRole('row', { name: /En vivo/ });
    expect(within(row).getByText('1:05')).toBeInTheDocument();
    expect(within(row).getByText('En vivo')).toBeInTheDocument();
  });

  it('una llamada en curso sin duración muestra solo En vivo, sin raya', async () => {
    mockApi(listRoutes([{ ...CALL, status: 'en_curso', duration_seconds: 0 }]));
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });

    const row = await screen.findByRole('row', { name: /En vivo/ });
    expect(within(row).getByText('En vivo')).toBeInTheDocument();
    // Ni raya ni 0:00 en la duración; el resto de las celdas de esta fila tienen dato.
    expect(within(row).queryByText('–')).not.toBeInTheDocument();
    expect(within(row).queryByText('0:00')).not.toBeInTheDocument();
  });

  it('admin: cada solapa pide sus orígenes', async () => {
    const urls: URL[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const req = input instanceof Request ? input : new Request(input);
        const url = new URL(req.url);
        if (url.pathname === '/api/v1/calls') urls.push(url);
        return url.pathname === '/api/v1/calls' ? jsonResponse({ items: [CALL], total: 1 }) : jsonResponse([]);
      }),
    );
    renderWithProviders(<ConversationsPage />, { me: ADMIN });

    const lastCall = () => {
      const q = urls[urls.length - 1].searchParams;
      return { mode: q.getAll('mode'), landing: q.get('landing') };
    };
    await waitFor(() => expect(lastCall()).toEqual({ mode: ['entrante'], landing: null }));
    for (const [name, expected] of [
      ['Salientes', { mode: ['saliente', 'directa'], landing: null }],
      ['Pruebas de clientes', { mode: ['prueba', 'celular'], landing: 'false' }],
      ['Link web', { mode: ['web'], landing: null }],
      ['Landing', { mode: ['prueba'], landing: 'true' }],
      ['WhatsApp y otras', { mode: ['whatsapp', 'api', 'loadtest'], landing: null }],
    ] as const) {
      await userEvent.click(screen.getByRole('tab', { name }));
      await waitFor(() => expect(lastCall()).toEqual(expected));
    }
  });

  it('la fila abre el detalle, salvo los controles', async () => {
    mockApi(listRoutes([CALL]));
    renderWithProviders(
      <Routes>
        <Route path="/" element={<ConversationsPage />} />
        <Route path="/admin/calls/:id" element={<div>detalle</div>} />
      </Routes>,
      { me: ADMIN },
    );

    await userEvent.click(await screen.findByRole('checkbox', { name: /Seleccionar conversación/ }));
    expect(screen.queryByText('detalle')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Borrar conversación' }));
    await userEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Cancelar' }));
    expect(screen.queryByText('detalle')).not.toBeInTheDocument();

    await userEvent.click(screen.getByText('Ana'));
    expect(await screen.findByText('detalle')).toBeInTheDocument();
  });

  it('filtra por campaña: las llamadas que hizo y las que abrió', async () => {
    const urls: string[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const req = input instanceof Request ? input : new Request(input);
        const url = new URL(req.url);
        urls.push(`${url.pathname}${url.search}`);
        if (url.pathname === '/api/v1/calls') return jsonResponse({ items: [CALL], total: 1 });
        if (url.pathname === '/api/v1/campaigns')
          return jsonResponse([{ id: 'cmp-9', name: 'Cobranza octubre', channel: 'voice' }]);
        return jsonResponse([]);
      }),
    );
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('textbox', { name: 'Campaña' }));
    await userEvent.click(
      await screen.findByRole('option', { name: 'Cobranza octubre · Llamadas', hidden: true }),
    );
    await waitFor(() =>
      expect(urls.some((u) => u.startsWith('/api/v1/calls') && u.includes('campaign_id=cmp-9'))).toBe(true),
    );
  });
});

describe('volver a correr el análisis', () => {
  it('solo con análisis y llamada terminada; un Usuario del cliente no lo ve', async () => {
    mockApi(
      listRoutes([
        { ...CALL, id: 'cv-si', contact_name: 'Ana', has_analysis: true },
        { ...CALL, id: 'cv-no', contact_name: 'Beto' },
        { ...CALL, id: 'cv-live', contact_name: 'Caro', has_analysis: true, status: 'en_curso' },
      ]),
    );
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });
    const row = (contact: string) => screen.getByRole('row', { name: new RegExp(contact) });
    await screen.findAllByRole('link', { name: /Ver conversación del/ });
    expect(
      within(row('Ana')).getByRole('button', { name: 'Volver a correr el análisis' }),
    ).toBeInTheDocument();
    // Sin análisis (o agente borrado) y con la llamada en vivo, no aparece.
    expect(
      within(row('Beto')).queryByRole('button', { name: 'Volver a correr el análisis' }),
    ).not.toBeInTheDocument();
    expect(
      within(row('Caro')).queryByRole('button', { name: 'Volver a correr el análisis' }),
    ).not.toBeInTheDocument();
  });

  it('un Usuario del cliente sin el rol de admin tampoco lo ve', async () => {
    mockApi(listRoutes([{ ...CALL, has_analysis: true }]));
    renderWithProviders(<ConversationsPage />, { me: { ...CLIENT_USER, client_role: 'user' } });
    await screen.findByRole('link', { name: /Ver conversación del/ });
    expect(screen.queryByRole('button', { name: 'Volver a correr el análisis' })).not.toBeInTheDocument();
  });

  it('confirma que pisa los datos, corre el POST y refresca la lista', async () => {
    const calls = mockApi({
      ...listRoutes([{ ...CALL, has_analysis: true }]),
      'POST /api/v1/calls/cv-1/analyze': () => jsonResponse({ pending: false }),
    });
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });
    const listGets = () => calls.filter((c) => c.method === 'GET' && c.path === '/api/v1/calls').length;
    await screen.findByRole('link', { name: /Ver conversación del/ });
    const before = listGets();

    await userEvent.click(screen.getByRole('button', { name: 'Volver a correr el análisis' }));
    const dialog = await screen.findByRole('dialog', { name: 'Volver a correr el análisis' });
    expect(within(dialog).getByText(/pisan los actuales/)).toBeInTheDocument();
    // Cancelar no manda nada.
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }));
    expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/analyze'))).toBe(false);

    await userEvent.click(screen.getByRole('button', { name: 'Volver a correr el análisis' }));
    await userEvent.click(
      within(await screen.findByRole('dialog')).getByRole('button', { name: 'Volver a correr' }),
    );
    await waitFor(() =>
      expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/analyze'))).toBe(true),
    );
    // El POST no lleva cuerpo y al terminar se invalida la lista.
    expect(calls.find((c) => c.method === 'POST' && c.path.endsWith('/analyze'))?.body).toBeUndefined();
    await waitFor(() => expect(listGets()).toBeGreaterThan(before));
    expect(notifySuccess).toHaveBeenCalledWith('Análisis vuelto a correr.');
  });

  it('pending: avisa que sigue corriendo en el fondo', async () => {
    mockApi({
      ...listRoutes([{ ...CALL, has_analysis: true }]),
      'POST /api/v1/calls/cv-1/analyze': () => jsonResponse({ pending: true }),
    });
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Volver a correr el análisis' }));
    await userEvent.click(
      within(await screen.findByRole('dialog')).getByRole('button', { name: 'Volver a correr' }),
    );
    await waitFor(() =>
      expect(notifyInfo).toHaveBeenCalledWith(
        'El análisis sigue corriendo en el fondo; los datos aparecen al terminar.',
      ),
    );
  });

  it('un 409 de la API llega como toast de error', async () => {
    mockApi({
      ...listRoutes([{ ...CALL, has_analysis: true }]),
      'POST /api/v1/calls/cv-1/analyze': () =>
        jsonResponse({ detail: 'La llamada sigue en curso', code: 'call_in_progress' }, 409),
    });
    renderWithProviders(<ConversationsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Volver a correr el análisis' }));
    await userEvent.click(
      within(await screen.findByRole('dialog')).getByRole('button', { name: 'Volver a correr' }),
    );
    await waitFor(() => expect(notifyError).toHaveBeenCalled());
    const [err, title] = vi.mocked(notifyError).mock.calls[0];
    expect((err as Error).message).toBe('La llamada sigue en curso');
    expect(title).toBe('No se pudo volver a correr el análisis');
  });
});
