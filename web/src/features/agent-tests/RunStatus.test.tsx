import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { CLIENT_USER, renderWithProviders } from '@/test/render';
import type { TestRun } from './api';
import { RunStatus } from './RunStatus';

const run = (over: Partial<TestRun>): TestRun =>
  ({
    id: 'r1',
    client_id: 'c-1',
    agent_id: 'ag-1',
    status: 'queued',
    repetitions: 5,
    variants: [{ key: 'publicada', version: 1 }],
    cases: [],
    results: null,
    done: 0,
    total: 10,
    input_tokens: 0,
    output_tokens: 0,
    error: null,
    created_at: '2026-11-20T10:00:00Z',
    started_at: null,
    finished_at: null,
    cancel_requested_at: null,
    ...over,
  }) as TestRun;

const render = (over: Partial<TestRun>) =>
  renderWithProviders(<RunStatus agentId="ag-1" run={run(over)} />, { me: CLIENT_USER });

describe('RunStatus', () => {
  it('dice el estado en castellano y cuenta las repeticiones mientras corre', () => {
    render({ status: 'running', done: 3 });
    expect(screen.getByText('Corriendo')).toBeInTheDocument();
    expect(screen.getByText('3/10 repeticiones')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeInTheDocument();
  });

  it('en cola se puede cancelar', () => {
    render({ status: 'queued' });
    expect(screen.getByText('En cola')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeInTheDocument();
  });

  it('con el pedido de cancelación dice «Cancelando…» y no ofrece cancelar otra vez', () => {
    render({ status: 'running', done: 6, cancel_requested_at: '2026-11-20T10:00:05Z' });
    expect(screen.getByText('Cancelando…')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancelar' })).not.toBeInTheDocument();
  });

  it('terminada y cancelada no cambian más: sin botón ni progreso', () => {
    const { unmount } = render({ status: 'done', done: 10 });
    expect(screen.getByText('Terminada')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancelar' })).not.toBeInTheDocument();
    expect(screen.queryByText('10/10 repeticiones')).not.toBeInTheDocument();
    unmount();
    render({ status: 'cancelled', done: 4 });
    expect(screen.getByText('Cancelada')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancelar' })).not.toBeInTheDocument();
  });

  it('una fallida muestra el error', () => {
    render({ status: 'failed', error: 'RuntimeError: proveedor caído' });
    expect(screen.getByText('Falló')).toBeInTheDocument();
    expect(screen.getByText('RuntimeError: proveedor caído')).toBeInTheDocument();
  });
});
