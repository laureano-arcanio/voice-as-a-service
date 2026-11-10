import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '@/test/render';
import { ProbarRedirect } from '@/features/agents/ProbarRedirect';

const routes = [
  { path: '/probar', element: <ProbarRedirect /> },
  { path: '/agents', element: <p>Lista de agentes</p> },
  { path: '/agents/:id', element: <p>Detalle del agente</p> },
];

describe('/probar', () => {
  it('con ?agent= abre la pestaña Probar de ese agente', async () => {
    const { router } = renderWithProviders(<></>, { path: '/probar?agent=ag-1', routes });
    expect(await screen.findByText('Detalle del agente')).toBeInTheDocument();
    expect(router.state.location.pathname + router.state.location.search).toBe('/agents/ag-1?tab=probar');
  });

  it('sin agente va a la lista', async () => {
    renderWithProviders(<></>, { path: '/probar', routes });
    expect(await screen.findByText('Lista de agentes')).toBeInTheDocument();
  });
});
