import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CallDetail } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { notifyError, notifyInfo, notifySuccess } from '@/lib/notify';
import { CallDetailPage } from './CallDetailPage';

// Volver a correr el análisis en el detalle (POST /calls/{id}/analyze, docs/GUIA_UI.md).

vi.mock('@/lib/notify', () => ({
  notifyError: vi.fn(),
  notifySuccess: vi.fn(),
  notifyInfo: vi.fn(),
}));

const DETAIL: CallDetail = {
  id: 'cv-1',
  client_id: 'c-1',
  client_name: 'Acme',
  agent_id: 'ag-1',
  agent_name: 'Ventas',
  agent_version: 1,
  created_at: '2026-11-20T12:00:00Z',
  workflow_status: 'completed',
  fields: [{ name: 'acuerdo', label: 'Acuerdo', description: '', value: 'viernes' }],
  outcome: null,
  messages: [{ role: 'assistant', text: 'Hola, te llamo de Ventas.' }],
  summary: 'Resumen viejo.',
  has_analysis: true,
  call: {
    mode: 'saliente',
    phone: '+5491155551234',
    status: 'finalizada',
    client_number: '+541155550000',
    ended_reason: 'completed',
    error: '',
    duration_seconds: 65,
    latency: null,
    created_at: '2026-11-20T12:00:00Z',
    started_at: '2026-11-20T12:00:05Z',
    ended_at: '2026-11-20T12:01:10Z',
    user_id: null,
    user_name: null,
    answered_by: 'agent',
    opted_out_confirmed: false,
  },
};

function renderDetail(detail: CallDetail, analyze?: () => Response) {
  const calls: { method: string; path: string }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const path = new URL(req.url).pathname;
      calls.push({ method: req.method, path });
      if (path === '/api/v1/calls/cv-1' && req.method === 'GET') return jsonResponse(detail);
      if (path === '/api/v1/calls/cv-1/analyze' && req.method === 'POST')
        return analyze ? analyze() : jsonResponse({ pending: false });
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  const rendered = renderWithProviders(<></>, {
    me: CLIENT_USER,
    path: '/calls/cv-1',
    routes: [{ path: '/calls/:id', element: <CallDetailPage /> }],
  });
  return { ...rendered, calls };
}

afterEach(() => vi.unstubAllGlobals());

describe('detalle: volver a correr el análisis', () => {
  it('aparece con análisis y llamada terminada; sin análisis o siendo Usuario, no', async () => {
    const first = renderDetail(DETAIL);
    expect(await screen.findByText('Resumen viejo.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Volver a correr el análisis' })).toBeInTheDocument();
    first.unmount();

    renderDetail({ ...DETAIL, has_analysis: false });
    await screen.findByText('Resumen viejo.');
    expect(screen.queryByRole('button', { name: 'Volver a correr el análisis' })).not.toBeInTheDocument();
  });

  it('un Usuario del cliente no lo ve', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse(DETAIL)));
    renderWithProviders(<></>, {
      me: { ...CLIENT_USER, client_role: 'user' },
      path: '/calls/cv-1',
      routes: [{ path: '/calls/:id', element: <CallDetailPage /> }],
    });
    await screen.findByText('Resumen viejo.');
    expect(screen.queryByRole('button', { name: 'Volver a correr el análisis' })).not.toBeInTheDocument();
  });

  it('confirma, corre el POST y refresca el detalle', async () => {
    const { calls } = renderDetail(DETAIL);
    const detailGets = () => calls.filter((c) => c.method === 'GET' && c.path === '/api/v1/calls/cv-1').length;
    await screen.findByText('Resumen viejo.');
    const before = detailGets();

    await userEvent.click(screen.getByRole('button', { name: 'Volver a correr el análisis' }));
    const dialog = await screen.findByRole('dialog', { name: 'Volver a correr el análisis' });
    expect(within(dialog).getByText(/pisan los actuales/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Volver a correr' }));

    await waitFor(() =>
      expect(calls.some((c) => c.method === 'POST' && c.path === '/api/v1/calls/cv-1/analyze')).toBe(true),
    );
    await waitFor(() => expect(detailGets()).toBeGreaterThan(before));
    expect(notifySuccess).toHaveBeenCalledWith('Análisis vuelto a correr.');
  });

  it('pending: avisa que sigue corriendo en el fondo', async () => {
    renderDetail(DETAIL, () => jsonResponse({ pending: true }));
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
    renderDetail(DETAIL, () =>
      jsonResponse({ detail: 'La conversación no tiene análisis', code: 'no_analysis' }, 409),
    );
    await userEvent.click(await screen.findByRole('button', { name: 'Volver a correr el análisis' }));
    await userEvent.click(
      within(await screen.findByRole('dialog')).getByRole('button', { name: 'Volver a correr' }),
    );
    await waitFor(() => expect(notifyError).toHaveBeenCalled());
    const [err, title] = vi.mocked(notifyError).mock.calls[0];
    expect((err as Error).message).toBe('La conversación no tiene análisis');
    expect(title).toBe('No se pudo volver a correr el análisis');
  });
});
