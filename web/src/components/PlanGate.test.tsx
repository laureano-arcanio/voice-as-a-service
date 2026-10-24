import { Button } from '@mantine/core';
import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { PlanFeatures } from '@/api/types';
import { planFeaturesKey } from '@/features/billing/features';
import { ADMIN, CLIENT_USER, renderWithProviders } from '@/test/render';
import { PlanGate } from './PlanGate';

const on = { enabled: true, reason: null };
const off = {
  enabled: false,
  reason: 'Disponible en los planes Mostrador y Sucursal, con números asignados.',
};

const FREE: PlanFeatures = {
  client_id: 'c-1',
  tier_name: 'Free',
  free: true,
  features: {
    outbound_calls: off,
    campaigns_voice: off,
    campaigns_whatsapp: off,
    whatsapp: off,
    contacts: off,
    team: off,
    call_links: on,
  },
};

function renderGate(plan: PlanFeatures | null, me = CLIENT_USER) {
  const r = renderWithProviders(
    <PlanGate feature="outbound_calls" what="llamadas salientes" hint="Probalo desde el agente.">
      <Button>Llamar</Button>
    </PlanGate>,
    { me },
  );
  if (plan) r.queryClient.setQueryData(planFeaturesKey, plan);
  return r;
}

describe('PlanGate', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('sin la función en el plan: aviso con el motivo y el contenido deshabilitado', async () => {
    renderGate(FREE);
    expect(await screen.findByText('Tu plan Free no incluye llamadas salientes.')).toBeInTheDocument();
    expect(screen.getByText(off.reason, { exact: false })).toBeInTheDocument();
    expect(screen.getByText('Probalo desde el agente.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Mejorar mi plan' })).toHaveAttribute('href', '/plan');
    expect(screen.getByRole('button', { name: 'Llamar' })).toBeDisabled();
  });

  it('con la función en el plan: solo el contenido', async () => {
    renderGate({ ...FREE, free: false, features: { ...FREE.features, outbound_calls: on } });
    expect(await screen.findByRole('button', { name: 'Llamar' })).toBeEnabled();
    expect(screen.queryByText(/no incluye/)).not.toBeInTheDocument();
  });

  it('el admin no tiene plan: no bloquea', async () => {
    vi.stubGlobal('fetch', vi.fn());
    renderGate(null, ADMIN);
    expect(await screen.findByRole('button', { name: 'Llamar' })).toBeEnabled();
    expect(fetch).not.toHaveBeenCalled();
  });
});
