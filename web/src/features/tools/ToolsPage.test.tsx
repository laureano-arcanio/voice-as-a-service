import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ClientTool } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { type ParamRow, rowsToSchema } from './draft';
import { ParamsEditor } from './ParamsEditor';
import { ToolsPage } from './ToolsPage';

const TOOL: ClientTool = {
  id: 't-1',
  slug: 'consultar_turnos',
  type: 'http',
  definition: {
    description: 'Busca turnos libres.',
    http: { method: 'GET', url: 'https://api.x.com/turnos' },
  },
  revision: 2,
  secrets: ['CRM_TOKEN'],
  llm_tool: null,
  used_by: [{ id: 'a-1', slug: 'turnos', name: 'Turnos' }],
  last_test_at: '2026-10-26T12:00:00Z',
  last_test_ok: true,
  last_test_detail: '',
  created_at: '2026-10-26T10:00:00Z',
  updated_at: '2026-10-26T10:00:00Z',
};

function mockApi(features: Record<string, { enabled: boolean; reason: string | null }>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const path = new URL(req.url).pathname;
      if (path === '/api/v1/clients/c-1/tools')
        return jsonResponse([
          TOOL,
          { ...TOOL, id: 't-2', slug: 'deuda', type: 'code', used_by: [], last_test_at: null },
        ]);
      if (path === '/api/v1/plan/features')
        return jsonResponse({ client_id: 'c-1', tier_name: 'Sucursal', free: false, features });
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('ToolsPage', () => {
  it('lista las herramientas con tipo, agentes y última prueba; el código bloqueado por el plan', async () => {
    mockApi({
      custom_tools: { enabled: true, reason: null },
      code_tools: { enabled: false, reason: 'Disponible en el plan Central' },
    });
    renderWithProviders(<ToolsPage />, { me: CLIENT_USER });
    const row = (await screen.findByRole('link', { name: 'consultar_turnos' })).closest('tr')!;
    expect(within(row).getByText('API')).toBeInTheDocument();
    expect(within(row).getByRole('link', { name: 'Turnos' })).toHaveAttribute('href', '/agents/a-1');
    expect(within(row).getByText('Funcionó')).toBeInTheDocument();
    const code = screen.getByRole('link', { name: 'deuda' }).closest('tr')!;
    expect(within(code).getByText('Código')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /Nueva herramienta/ }));
    expect(await screen.findByRole('menuitem', { name: /Llamar a una API/ })).toBeEnabled();
    expect(screen.getByText('Escribir código').closest('button')).toBeDisabled();
  });

  it('sin herramientas en el plan, el aviso de Mejorar mi plan', async () => {
    mockApi({
      custom_tools: { enabled: false, reason: 'Disponible en el plan Central' },
      code_tools: { enabled: false, reason: 'Disponible en el plan Central' },
    });
    renderWithProviders(<ToolsPage />, { me: CLIENT_USER });
    expect(await screen.findByText(/no incluye herramientas para tus agentes/)).toBeInTheDocument();
  });
});

describe('ParamsEditor', () => {
  let last: ParamRow[] = [];
  function Harness() {
    const [rows, setRows] = useState<ParamRow[]>([]);
    return (
      <ParamsEditor
        rows={rows}
        onChange={(r) => {
          last = r;
          setRows(r);
        }}
      />
    );
  }

  it('una fila del agente y una fija dan el JSON Schema', async () => {
    renderWithProviders(<Harness />);
    await userEvent.click(screen.getByRole('button', { name: 'Agregar parámetro' }));
    await userEvent.type(screen.getByRole('textbox', { name: 'Nombre del parámetro 1' }), 'dni');
    await userEvent.type(screen.getByRole('textbox', { name: 'Descripción de dni' }), 'DNI sin puntos');
    await userEvent.click(screen.getByRole('checkbox', { name: 'Obligatorio' }));

    await userEvent.click(screen.getByRole('button', { name: 'Agregar parámetro' }));
    await userEvent.type(screen.getByRole('textbox', { name: 'Nombre del parámetro 2' }), 'canal');
    await userEvent.click(screen.getAllByRole('radio', { name: 'Valor fijo' })[1]!);
    await userEvent.type(screen.getByRole('textbox', { name: 'Valor de canal' }), 'atentina');

    await waitFor(() =>
      expect(rowsToSchema(last)).toEqual({
        type: 'object',
        properties: {
          dni: { type: 'string', description: 'DNI sin puntos' },
          canal: { type: 'string', value: 'atentina' },
        },
        required: ['dni'],
      }),
    );
  });
});
