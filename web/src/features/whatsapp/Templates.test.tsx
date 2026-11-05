import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { WaAccount } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { TemplatesCard } from './Templates';

const ACCOUNT = {
  id: 'wa-1',
  display_phone_number: '+54 9 351 555-0000',
  name: 'Guardia',
  status: 'connected',
} as WaAccount;

function mockApi() {
  const posted: unknown[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      if (req.method === 'POST') {
        posted.push(await req.clone().json());
        return jsonResponse({ id: 't-1', status: 'PENDING' }, 201);
      }
      return jsonResponse([]);
    }),
  );
  return posted;
}

afterEach(() => vi.unstubAllGlobals());

async function fillBase() {
  await userEvent.click(await screen.findByRole('button', { name: /Nueva plantilla/ }));
  const dialog = await screen.findByRole('dialog');
  await userEvent.type(within(dialog).getByLabelText(/^Nombre/), 'equipo_rotacion');
  await userEvent.type(within(dialog).getByLabelText('Cuerpo'), 'Pedido urgente en {{{{1}}.');
  await userEvent.type(within(dialog).getByLabelText('Ejemplo de {{1}}'), 'Guardia');
  return dialog;
}

describe('plantillas: botón de respuesta rápida', () => {
  it('manda el rótulo libre como QUICK_REPLY', async () => {
    const posted = mockApi();
    renderWithProviders(<TemplatesCard accounts={[ACCOUNT]} accountId="wa-1" onSelect={() => {}} />, {
      me: CLIENT_USER,
    });
    const dialog = await fillBase();
    await userEvent.type(within(dialog).getByLabelText(/Botón de respuesta rápida/), 'Aceptar');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear' }));
    await waitFor(() => expect(posted).toHaveLength(1));
    expect(posted[0]).toMatchObject({
      name: 'equipo_rotacion',
      buttons: [{ type: 'QUICK_REPLY', text: 'Aceptar' }],
    });
  });

  it('sin rótulo no manda botones, y «No me interesa» no se repite', async () => {
    const posted = mockApi();
    renderWithProviders(<TemplatesCard accounts={[ACCOUNT]} accountId="wa-1" onSelect={() => {}} />, {
      me: CLIENT_USER,
    });
    let dialog = await fillBase();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear' }));
    await waitFor(() => expect(posted).toHaveLength(1));
    expect(posted[0]).toMatchObject({ buttons: [] });

    await userEvent.click(await screen.findByRole('button', { name: /Nueva plantilla/ }));
    dialog = await screen.findByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/^Nombre/), 'baja');
    await userEvent.type(within(dialog).getByLabelText('Cuerpo'), 'Hola');
    await userEvent.type(within(dialog).getByLabelText(/Botón de respuesta rápida/), 'No me interesa');
    await userEvent.click(within(dialog).getByRole('checkbox', { name: /No me interesa/ }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear' }));
    await waitFor(() => expect(posted).toHaveLength(2));
    expect(posted[1]).toMatchObject({ buttons: [{ type: 'QUICK_REPLY', text: 'No me interesa' }] });
  });
});
