import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ADMIN, jsonResponse, renderWithProviders } from '@/test/render';
import { TiersPage } from './TiersPage';

const TIER = {
  id: 't1',
  name: 'Free',
  description: '',
  max_concurrent_calls: 2,
  max_calls_per_hour: 20,
  max_calls_per_day: 20,
  max_calls_per_month: null,
  inbound_minutes: null,
  outbound_minutes: null,
  max_phone_numbers: 1,
  api_llm_input_tokens: 0,
  api_llm_output_tokens: 0,
  api_tts_minutes: 0,
  api_stt_minutes: 0,
  api_rate_limit: 60,
  campaign_channels: ['whatsapp', 'voice'],
  max_campaigns_per_month: 5,
  max_campaign_contacts: 500,
  max_campaign_concurrency: null,
  max_contacts: 1000,
  campaign_followup: true,
  created_at: '2026-10-01T00:00:00Z',
  clients_count: 0,
};

function mockApi() {
  const created: Record<string, unknown>[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(String(input));
      if (req.method === 'POST') {
        const body = await req.json();
        created.push(body);
        return jsonResponse({ ...TIER, ...body, id: 't2' }, 201);
      }
      return jsonResponse([TIER]);
    }),
  );
  return created;
}

describe('TiersPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('lista los límites de llamadas por hora, día y mes', async () => {
    mockApi();
    renderWithProviders(<TiersPage />, { me: ADMIN });
    expect(await screen.findByText('Free')).toBeInTheDocument();
    expect(screen.getByText('20 / 20 / Ilimitado')).toBeInTheDocument();
  });

  it('crea un tier con los límites de llamadas y los de la API por defecto', async () => {
    const created = mockApi();
    renderWithProviders(<TiersPage />, { me: ADMIN });
    await userEvent.click(await screen.findByRole('button', { name: /Nuevo tier/ }));
    await userEvent.type(screen.getByLabelText(/Nombre/), 'Pro');
    await userEvent.type(screen.getByLabelText('Por hora'), '50');
    await userEvent.type(screen.getByLabelText('Personas del equipo'), '3');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toMatchObject({
      name: 'Pro',
      max_calls_per_hour: 50,
      max_calls_per_day: null,
      max_calls_per_month: null,
      max_concurrent_calls: null,
      api_llm_input_tokens: 0,
      api_rate_limit: 60,
      max_team_members: 3,
      max_call_links: null,
    });
  });

  it('lista los canales de campañas, sus topes y la agenda', async () => {
    mockApi();
    renderWithProviders(<TiersPage />, { me: ADMIN });
    await screen.findByText('Free');
    expect(screen.getByText('WhatsApp y llamadas')).toBeInTheDocument();
    expect(screen.getByText('con seguimiento')).toBeInTheDocument();
    expect(screen.getByText('5 / 500 / Ilimitado')).toBeInTheDocument();
    expect(screen.getByText('1.000')).toBeInTheDocument();
  });

  it('llamadas directas: apagadas en un tier nuevo y se mandan al prenderlas', async () => {
    const created = mockApi();
    renderWithProviders(<TiersPage />, { me: ADMIN });
    await userEvent.click(await screen.findByRole('button', { name: /Nuevo tier/ }));
    await userEvent.type(screen.getByLabelText(/Nombre/), 'Pro');
    const direct = screen.getByRole('switch', { name: /Llamadas directas \(teléfono del equipo\)/ });
    expect(direct).not.toBeChecked();
    await userEvent.click(direct);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toMatchObject({ direct_calls: true });
  });

  it('muestra "con llamadas directas" en el tier que las incluye', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse([{ ...TIER, direct_calls: true }])),
    );
    renderWithProviders(<TiersPage />, { me: ADMIN });
    expect(await screen.findByText('con llamadas directas')).toBeInTheDocument();
  });

  it('un tier nuevo no incluye campañas; se habilitan por canal con sus topes', async () => {
    const created = mockApi();
    renderWithProviders(<TiersPage />, { me: ADMIN });
    await userEvent.click(await screen.findByRole('button', { name: /Nuevo tier/ }));
    await userEvent.type(screen.getByLabelText(/Nombre/), 'Pro');
    expect(screen.getByRole('checkbox', { name: 'WhatsApp' })).not.toBeChecked();
    await userEvent.click(screen.getByRole('checkbox', { name: 'Llamadas' }));
    await userEvent.type(screen.getByLabelText('Campañas por mes'), '10');
    await userEvent.type(screen.getByLabelText('Llamadas simultáneas por campaña'), '4');
    await userEvent.click(screen.getByRole('switch', { name: /Seguimiento por WhatsApp/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0]).toMatchObject({
      campaign_channels: ['voice'],
      max_campaigns_per_month: 10,
      max_campaign_contacts: null,
      max_campaign_concurrency: 4,
      max_contacts: null,
      campaign_followup: true,
    });
  });
});
