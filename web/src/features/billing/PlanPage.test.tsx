import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Billing } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { planFeatures } from './format';
import { PlanPage } from './PlanPage';

const PLAN = {
  id: 't-suc',
  name: 'Sucursal',
  description: '',
  price_ars: 99000,
  max_concurrent_calls: 3,
  inbound_minutes: 1200,
  outbound_minutes: null,
  max_phone_numbers: 3,
  api_rate_limit: 0,
};

const FREE: Billing = {
  tier: { id: 't-free', name: 'Free' },
  tier_price_ars: 0,
  subscription: null,
  plans: [PLAN],
  methods: ['transfer'],
  mp_public_key: null,
  fiscal: { legal_name: 'Acme SA', tax_id: '30712345678', tax_condition: 'ri' },
  bank: [
    { label: 'Titular', value: 'Atentina' },
    { label: 'Alias', value: 'atentina.pagos' },
  ],
  support_email: 'hola@atentina.com.ar',
  payments: [],
  suspended_numbers: [],
};

const PENDING: Billing = {
  ...FREE,
  subscription: {
    id: 's-1',
    tier: { id: 't-suc', name: 'Sucursal' },
    pending_tier: null,
    method: 'transfer',
    status: 'pending',
    current_period_end: null,
    grace_until: null,
    cancel_at_period_end: false,
    amount_due: 99000,
    created_at: '2026-10-09T12:00:00Z',
  },
};

function mockApi(billing: Billing, after: Billing = billing) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(String(input));
      const path = new URL(req.url).pathname;
      calls.push({ method: req.method, path, body: req.method === 'GET' ? null : await req.clone().json() });
      return jsonResponse(req.method === 'GET' ? billing : after);
    }),
  );
  return calls;
}

describe('PlanPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('pide un plan por transferencia y muestra los datos para pagar', async () => {
    const calls = mockApi(FREE, PENDING);
    renderWithProviders(<PlanPage />, { me: CLIENT_USER });
    expect(await screen.findByText('Gratis')).toBeInTheDocument();
    expect(screen.getByText('$ 99.000')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Elegir este plan' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Pedir el plan' }));
    expect(await within(dialog).findByText('atentina.pagos')).toBeInTheDocument();
    expect(calls.find((c) => c.method === 'POST')).toEqual({
      method: 'POST',
      path: '/api/v1/clients/c-1/billing/subscribe',
      body: { tier_id: 't-suc', method: 'transfer', card_token_id: null },
    });
  });

  it('sin datos fiscales los pide antes del plan', async () => {
    mockApi({ ...FREE, fiscal: { legal_name: '', tax_id: '', tax_condition: '' } });
    renderWithProviders(<PlanPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Elegir este plan' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByRole('button', { name: 'Continuar' })).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Continuar' }));
    expect(await within(dialog).findByText('El CUIT tiene 11 números')).toBeInTheDocument();
  });

  it('con Mercado Pago ofrece pagar con tarjeta o por transferencia', async () => {
    mockApi({ ...FREE, methods: ['mercadopago', 'transfer'], mp_public_key: 'TEST-pk' });
    renderWithProviders(<PlanPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Elegir este plan' }));
    const dialog = await screen.findByRole('dialog');
    expect(
      within(dialog).getByRole('button', { name: 'Pagar con tarjeta (débito automático)' }),
    ).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Pagar por transferencia' }));
    expect(within(dialog).getByRole('button', { name: 'Pedir el plan' })).toBeInTheDocument();
  });

  it('con débito automático activo muestra el próximo débito y cambia de plan sin tarjeta', async () => {
    const calls = mockApi({
      ...FREE,
      tier: { id: 't-mos', name: 'Mostrador' },
      tier_price_ars: 29000,
      methods: ['mercadopago', 'transfer'],
      mp_public_key: 'TEST-pk',
      subscription: {
        ...PENDING.subscription!,
        tier: { id: 't-mos', name: 'Mostrador' },
        method: 'mercadopago',
        status: 'active',
        current_period_end: '2026-11-10',
        amount_due: 29000,
      },
    });
    renderWithProviders(<PlanPage />, { me: CLIENT_USER });
    expect(await screen.findByText(/Débito automático con tarjeta/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Elegir este plan' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cambiar de plan' }));
    await vi.waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
        tier_id: 't-suc',
        method: 'mercadopago',
        card_token_id: null,
      }),
    );
  });

  it('con un pedido pendiente muestra cómo pagarlo', async () => {
    mockApi(PENDING);
    renderWithProviders(<PlanPage />, { me: CLIENT_USER });
    expect(await screen.findByText('Pediste el plan Sucursal')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Pedido' })).toBeDisabled();
  });
});

describe('planFeatures', () => {
  it('dice sin límite y omite lo que el plan no incluye', () => {
    expect(planFeatures(PLAN)).toEqual([
      '1.200 minutos entrantes por mes',
      'Minutos salientes sin límite',
      '3 llamadas a la vez',
      '3 números de teléfono',
    ]);
    expect(
      planFeatures({
        ...PLAN,
        outbound_minutes: 0,
        max_phone_numbers: 0,
        max_concurrent_calls: 1,
        api_rate_limit: 10,
      }),
    ).toEqual(['1.200 minutos entrantes por mes', '1 llamada a la vez', 'Acceso a la API']);
  });
});
