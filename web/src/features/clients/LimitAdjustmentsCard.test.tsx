import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ADMIN, jsonResponse, renderWithProviders } from '@/test/render';
import { LimitAdjustmentsCard } from './LimitAdjustmentsCard';
import { endOfThisMonth } from './limits';

const ROW = (field: string, tier: number | null, effective: number | null) => ({ field, tier, effective });

const LIMITS = {
  tier_name: 'Pyme',
  limits: [ROW('inbound_minutes', 100, 110), ROW('outbound_minutes', null, null), ROW('max_phone_numbers', 1, 1)],
  adjustments: [
    {
      id: 'a1',
      field: 'inbound_minutes',
      mode: 'add',
      value: 10,
      starts_on: null,
      ends_on: '2026-10-31',
      note: 'promo octubre',
      status: 'active',
      created_at: '2026-10-09T12:00:00Z',
      created_by_email: 'admin@atentina.com.ar',
    },
  ],
};

function mockApi(initial = LIMITS) {
  const posted: Record<string, unknown>[] = [];
  const deleted: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(String(input));
      if (req.method === 'POST') {
        posted.push(await req.json());
        return jsonResponse(initial, 201);
      }
      if (req.method === 'DELETE') {
        deleted.push(new URL(req.url).pathname.split('/').pop()!);
        return jsonResponse({ ...initial, adjustments: [] });
      }
      return jsonResponse(initial);
    }),
  );
  return { posted, deleted };
}

describe('LimitAdjustmentsCard', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('lista los ajustes con cantidad, motivo y vigencia', async () => {
    mockApi();
    renderWithProviders(<LimitAdjustmentsCard clientId="c-1" />, { me: ADMIN });
    expect(await screen.findByText('Minutos entrantes por mes')).toBeInTheDocument();
    expect(screen.getByText('+10 min')).toBeInTheDocument();
    expect(screen.getByText('promo octubre')).toBeInTheDocument();
    expect(screen.getByText('Vigente')).toBeInTheDocument();
  });

  it('sin ajustes dice que rige el tier', async () => {
    mockApi({ ...LIMITS, adjustments: [] });
    renderWithProviders(<LimitAdjustmentsCard clientId="c-1" />, { me: ADMIN });
    expect(await screen.findByText(/rigen los límites del tier Pyme/)).toBeInTheDocument();
  });

  it('carga un ajuste de minutos con vigencia de este mes y muestra cómo queda', async () => {
    const { posted } = mockApi();
    renderWithProviders(<LimitAdjustmentsCard clientId="c-1" />, { me: ADMIN });
    await userEvent.click(await screen.findByRole('button', { name: /Nuevo ajuste/ }));
    const dialog = await screen.findByRole('dialog');
    // Minutos entrantes es el campo por defecto: hoy 110 (tier 100 + el ajuste vigente).
    await userEvent.type(within(dialog).getByLabelText(/Cantidad a sumar/), '15');
    expect(within(dialog).getByText('Hoy: 110 min → 125 min')).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('textbox', { name: 'Vigencia' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Solo este mes', hidden: true }));
    await userEvent.type(within(dialog).getByLabelText(/Motivo/), 'compensación');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cargar ajuste' }));
    await waitFor(() => expect(posted).toHaveLength(1));
    expect(posted[0]).toEqual({
      field: 'inbound_minutes',
      mode: 'add',
      value: 15,
      ends_on: endOfThisMonth(),
      note: 'compensación',
    });
  });

  it('pide confirmación para quitar un ajuste', async () => {
    const { deleted } = mockApi();
    renderWithProviders(<LimitAdjustmentsCard clientId="c-1" />, { me: ADMIN });
    await userEvent.click(await screen.findByRole('button', { name: /Quitar ajuste de Minutos entrantes/ }));
    await userEvent.click(await screen.findByRole('button', { name: 'Quitar' }));
    await waitFor(() => expect(deleted).toEqual(['a1']));
  });
});

describe('endOfThisMonth', () => {
  it('es el último día del mes en curso', () => {
    expect(endOfThisMonth(new Date(2026, 1, 10))).toBe('2026-02-28');
    expect(endOfThisMonth(new Date(2026, 11, 31))).toBe('2026-12-31');
  });
});
