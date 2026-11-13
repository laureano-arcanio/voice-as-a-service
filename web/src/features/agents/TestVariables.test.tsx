import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Definition } from '@/api/types';
import { CATALOG } from '@/components/variables/fixtures';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { TestVariables } from './TestVariables';
import { testRows, testVariableNames, testVariables, useTestVariables } from './testVariables';

const DEF = {
  agent: { name: 'Sofía', language: 'es-AR' },
  prompt: 'Saludá con {{saludo}}. La deuda es {{deuda}} y hoy es {{today}}.',
  first_message: '{{saludo}}',
  variables: [{ name: 'deuda', default: '1000', description: 'Lo que debe' }],
  analysis: { summary: true, instructions: '', fields: [], outcomes: [] },
} as Definition;

const CAT = CATALOG;

describe('nombres y filas', () => {
  it('declaradas en orden y las usadas sin declarar; sin las del sistema', () => {
    expect(testVariableNames(DEF, CAT).map((v) => v.name)).toEqual(['deuda', 'saludo']);
    expect(testVariableNames(DEF, CAT)[0]).toMatchObject({ default: '1000', description: 'Lo que debe' });
    expect(testVariableNames({}, CAT)).toEqual([]);
  });

  it('prellena con el default y respeta lo guardado; agrega las que vienen de afuera', () => {
    const names = testVariableNames(DEF, CAT);
    expect(testRows(names, [])).toEqual([
      { name: 'deuda', value: '1000' },
      { name: 'saludo', value: '' },
    ]);
    // Lo que el usuario cambió gana sobre el default.
    expect(testRows(names, [{ name: 'deuda', value: '5000' }])[0]).toEqual({
      name: 'deuda',
      value: '5000',
    });
    // Lo que se agregó a mano se conserva.
    const rows = testRows(names, [{ name: 'otra', value: 'x' }]);
    expect(rows.at(-1)).toEqual({ name: 'otra', value: 'x' });
    // Una que siempre está (T10: motivo).
    expect(testRows(names, [], [{ name: 'motivo' }]).at(-1)).toEqual({ name: 'motivo', value: '' });
    expect(testVariables([...rows, { name: '  ', value: 'no' }])).toEqual({
      deuda: '1000',
      saludo: '',
      otra: 'x',
    });
  });
});

function Harness({ id = 'ag-1', def = DEF }: { id?: string; def?: Definition }) {
  const test = useTestVariables(id, def);
  return (
    <>
      <TestVariables rows={test.rows} onChange={test.setRows} fixedNames={test.names.map((n) => n.name)} />
      <pre data-testid="vars">{JSON.stringify(test.variables)}</pre>
    </>
  );
}

function mockApi() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL((input instanceof Request ? input : new Request(input)).url);
      if (url.pathname === '/api/v1/variables/catalog') return jsonResponse(CATALOG);
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
}

beforeEach(() => window.sessionStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe('TestVariables', () => {
  it('prellena los defaults y los manda como variables', async () => {
    mockApi();
    renderWithProviders(<Harness />, { me: CLIENT_USER });
    expect(await screen.findByLabelText('Valor de deuda')).toHaveValue('1000');
    expect(screen.getByLabelText('Valor de saludo')).toHaveValue('');
    // El catálogo llega después del primer render: {{today}} deja de ser una variable del usuario.
    await waitFor(() =>
      expect(screen.getByTestId('vars').textContent).toBe(JSON.stringify({ deuda: '1000', saludo: '' })),
    );
  });

  it('lo editado se recuerda por agente en sessionStorage', async () => {
    mockApi();
    const first = renderWithProviders(<Harness />, { me: CLIENT_USER });
    const value = await screen.findByLabelText('Valor de deuda');
    await userEvent.clear(value);
    await userEvent.type(value, '5000');
    await waitFor(() => expect(screen.getByTestId('vars').textContent).toContain('"5000"'));
    first.unmount();
    renderWithProviders(<Harness />, { me: CLIENT_USER });
    expect(await screen.findByLabelText('Valor de deuda')).toHaveValue('5000');
    // Otro agente no lo ve.
    renderWithProviders(<Harness id="ag-2" />, { me: CLIENT_USER });
    expect((await screen.findAllByLabelText('Valor de deuda'))[1]).toHaveValue('1000');
  });

  it('agregar una variable propia y plegar la tabla', async () => {
    mockApi();
    renderWithProviders(<Harness />, { me: CLIENT_USER });
    await screen.findByLabelText('Valor de deuda');
    await userEvent.click(screen.getByRole('button', { name: 'Agregar' }));
    // La última fila es la que se agregó (las del catálogo pueden cambiar el total).
    const name = screen.getAllByLabelText(/Variable de prueba/).at(-1)!;
    await userEvent.type(name, 'motivo');
    const value = await screen.findByLabelText('Valor de motivo');
    await userEvent.type(value, 'Pidió presupuesto');
    await waitFor(() =>
      expect(screen.getByTestId('vars').textContent).toContain('"motivo":"Pidió presupuesto"'),
    );
    const header = screen.getByRole('button', { name: /Valores de prueba/ });
    expect(header).toHaveAttribute('aria-expanded', 'true');
    await userEvent.click(header);
    expect(screen.getByRole('button', { name: /Valores de prueba/ })).toHaveAttribute(
      'aria-expanded',
      'false',
    );
  });
});
