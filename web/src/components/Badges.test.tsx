import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MantineProvider } from '@mantine/core';
import { isUnanswered } from '@/lib/labels';
import { CallStatusBadge } from './Badges';

const view = (ui: React.ReactElement) => render(<MantineProvider>{ui}</MantineProvider>);

describe('CallStatusBadge', () => {
  it('una fallida que no atendieron o dio ocupado se marca "No atendida"', () => {
    view(<CallStatusBadge status="fallida" endedReason="no_answer" />);
    expect(screen.getByText('No atendida')).toBeInTheDocument();
    expect(isUnanswered({ status: 'fallida', ended_reason: 'busy' })).toBe(true);
  });

  it('otra fallida sigue siendo "Fallida"; una finalizada no se marca', () => {
    view(<CallStatusBadge status="fallida" endedReason="sip_call_failed" />);
    expect(screen.getByText('Fallida')).toBeInTheDocument();
    expect(isUnanswered({ status: 'finalizada', ended_reason: 'no_answer' })).toBe(false);
  });

  it('una finalizada dice quién cortó: el cliente, el equipo, el agente o el sistema', () => {
    const cases = [
      ['customer_hangup', 'Finalizada por el cliente'],
      ['person_hangup', 'Finalizada por el equipo'],
      ['hangup_by_user', 'Finalizada por el equipo'],
      ['completed', 'Finalizada por el agente'],
      ['off_topic', 'Finalizada por el agente'],
      ['max_duration', 'Finalizada por el sistema'],
    ] as const;
    for (const [reason, label] of cases) {
      const { unmount } = view(<CallStatusBadge status="finalizada" endedReason={reason} />);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });

  it('una finalizada sin motivo conocido (llamadas viejas) sigue siendo "Finalizada"', () => {
    view(<CallStatusBadge status="finalizada" endedReason="" />);
    expect(screen.getByText('Finalizada')).toBeInTheDocument();
  });
});
