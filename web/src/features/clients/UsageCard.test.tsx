import { render, screen } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { describe, expect, it } from 'vitest';
import type { Usage } from '@/api/types';
import { theme } from '@/theme';
import { UsageMeter, UsageMeters } from './UsageCard';

const wrap = (ui: React.ReactElement) => render(<MantineProvider theme={theme}>{ui}</MantineProvider>);

describe('UsageMeter', () => {
  it('sin límite muestra Ilimitado y no porcentaje', () => {
    wrap(<UsageMeter label="Minutos entrantes" used={12.5} limit={null} unit=" min" />);
    expect(screen.getByText(/Ilimitado/)).toBeInTheDocument();
    expect(screen.queryByText(/%$/)).not.toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: 'Minutos entrantes: ilimitado' })).toBeInTheDocument();
  });

  it('con límite muestra usado / límite y el %', () => {
    wrap(<UsageMeter label="Minutos salientes" used={95} limit={100} unit=" min" />);
    expect(screen.getByText('95%')).toBeInTheDocument();
    expect(screen.getByText(/100 min/)).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: 'Minutos salientes: 95% usado' })).toBeInTheDocument();
  });

  it('muestra las barras del consumo, con números', () => {
    const usage: Usage = {
      month: '2026-09',
      period_start: '2026-09-01T03:00:00Z',
      period_end: '2026-10-01T03:00:00Z',
      active_calls: 2,
      max_concurrent_calls: 4,
      inbound: { used_seconds: 600, used_minutes: 10, limit_minutes: null, remaining_minutes: null },
      outbound: { used_seconds: 1800, used_minutes: 30, limit_minutes: 40, remaining_minutes: 10 },
      phone_numbers: { used: 3, limit: 3 },
    };
    wrap(<UsageMeters usage={usage} />);
    expect(screen.getByText('Llamadas simultáneas')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('Quedan 10 min.')).toBeInTheDocument();
    expect(screen.getByText('Sin límite en el tier.')).toBeInTheDocument();
    expect(screen.getByText('100%')).toBeInTheDocument();
    expect(screen.getByText('Quedan 0 por asignar.')).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: 'Números: 100% usado' })).toBeInTheDocument();
  });
});
