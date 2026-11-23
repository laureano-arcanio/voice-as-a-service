import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { notifications } from '@mantine/notifications';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { WaAccount, WaTemplate } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { TemplatesCard } from './Templates';

const ACCOUNT = {
  id: 'wa-1',
  display_phone_number: '+54 9 351 555-0000',
  name: 'Guardia',
  status: 'connected',
} as WaAccount;

/** Aprobada de texto, con ejemplo y botón: la pantalla la edita. */
const APPROVED: WaTemplate = {
  id: '1001',
  name: 'equipo_rotacion',
  language: 'es_AR',
  category: 'UTILITY',
  status: 'APPROVED',
  rejected_reason: null,
  components: [
    { type: 'BODY', text: 'Pedido urgente en {{1}}.', example: { body_text: [['Guardia']] } },
    { type: 'BUTTONS', buttons: [{ type: 'QUICK_REPLY', text: 'Aceptar' }] },
  ],
};

/** Rechazada: se edita sin tope y con la categoría editable. */
const REJECTED: WaTemplate = {
  id: '1005',
  name: 'recordatorio_viejo',
  language: 'es_AR',
  category: 'MARKETING',
  status: 'REJECTED',
  rejected_reason: 'El contenido promociona productos',
  components: [{ type: 'BODY', text: 'Hola {{1}}, promo' }],
};

const TEMPLATES = '/api/v1/whatsapp/accounts/wa-1/templates';

function routes(list: WaTemplate[] = []) {
  return {
    [`GET ${TEMPLATES}`]: () => jsonResponse(list),
    [`POST ${TEMPLATES}`]: () => jsonResponse({ id: 't-new', status: 'PENDING' }, 201),
  };
}

interface Seen {
  method: string;
  path: string;
  search: string;
  body?: unknown;
}

function mockApi(handlers: Record<string, () => Response> = {}) {
  const posted: unknown[] = [];
  const calls: Seen[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const url = new URL(req.url);
      const body = req.method === 'GET' ? undefined : await req.clone().json().catch(() => undefined);
      if (req.method === 'POST') posted.push(body);
      calls.push({ method: req.method, path: url.pathname, search: url.search, body });
      const route = handlers[`${req.method} ${url.pathname}`];
      return route ? route() : jsonResponse([]);
    }),
  );
  return { posted, calls };
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
    const { posted } = mockApi(routes());
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
    const { posted } = mockApi(routes());
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

describe('plantillas: editar y borrar', () => {
  it('editar manda PUT a la plantilla, sin name ni language, con prefill y lista refrescada', async () => {
    const { calls } = mockApi({
      ...routes([APPROVED]),
      [`PUT ${TEMPLATES}/1001`]: () => new Response(null, { status: 204 }),
    });
    renderWithProviders(<TemplatesCard accounts={[ACCOUNT]} accountId="wa-1" onSelect={() => {}} />, {
      me: CLIENT_USER,
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar equipo_rotacion' }));
    const dialog = await screen.findByRole('dialog');
    // Prefill desde los componentes de Meta.
    expect(within(dialog).getByLabelText('Cuerpo')).toHaveValue('Pedido urgente en {{1}}.');
    expect(within(dialog).getByLabelText('Ejemplo de {{1}}')).toHaveValue('Guardia');
    expect(within(dialog).getByLabelText(/Botón de respuesta rápida/)).toHaveValue('Aceptar');
    // Inmutables al editar: nombre, idioma y (aprobada) la categoría.
    expect(within(dialog).getByLabelText(/^Nombre/)).toBeDisabled();
    expect(within(dialog).getByLabelText('Idioma')).toBeDisabled();
    expect(within(dialog).getByLabelText('Categoría')).toBeDisabled();
    await userEvent.clear(within(dialog).getByLabelText('Cuerpo'));
    await userEvent.type(within(dialog).getByLabelText('Cuerpo'), 'Cambio {{{{1}}');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    const put = await waitFor(() => {
      const found = calls.find((c) => c.method === 'PUT');
      if (!found) throw new Error('sin PUT');
      return found;
    });
    expect(put.path).toBe(`${TEMPLATES}/1001`);
    expect(put.body).not.toHaveProperty('name');
    expect(put.body).not.toHaveProperty('language');
    expect(put.body).toEqual({
      category: null, // aprobada: Meta rechaza el cambio de categoría
      body: 'Cambio {{1}}',
      examples: ['Guardia'],
      header_text: null,
      footer_text: null,
      buttons: [{ type: 'QUICK_REPLY', text: 'Aceptar' }],
    });
    // Tras guardar se vuelve a leer la lista de Meta.
    await waitFor(() =>
      expect(calls.filter((c) => c.method === 'GET' && c.path === TEMPLATES).length).toBeGreaterThanOrEqual(2),
    );
  });

  it('una rechazada edita con la categoría y muestra el motivo del rechazo', async () => {
    const { calls } = mockApi({
      ...routes([REJECTED]),
      [`PUT ${TEMPLATES}/1005`]: () => new Response(null, { status: 204 }),
    });
    renderWithProviders(<TemplatesCard accounts={[ACCOUNT]} accountId="wa-1" onSelect={() => {}} />, {
      me: CLIENT_USER,
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar recordatorio_viejo' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText(/Motivo del rechazo/)).toHaveTextContent('El contenido promociona productos');
    expect(within(dialog).getByLabelText('Categoría')).toBeEnabled();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    const put = await waitFor(() => {
      const found = calls.find((c) => c.method === 'PUT');
      if (!found) throw new Error('sin PUT');
      return found;
    });
    expect(put.body).toMatchObject({ category: 'MARKETING' });
  });

  it('no se edita lo que Meta no deja, ni lo que la pantalla no sabe cargar; DESHABILITADA no se borra', async () => {
    const pending: WaTemplate = {
      id: '1002',
      name: 'alta_pendiente',
      language: 'es_AR',
      category: 'MARKETING',
      status: 'PENDING',
      rejected_reason: null,
      components: [{ type: 'BODY', text: 'Hola' }],
    };
    const withImage: WaTemplate = {
      id: '1003',
      name: 'con_imagen',
      language: 'es_AR',
      category: 'MARKETING',
      status: 'APPROVED',
      rejected_reason: null,
      components: [
        { type: 'HEADER', format: 'IMAGE', example: { header_handle: ['x'] } },
        { type: 'BODY', text: 'Nueva promo {{1}}' },
      ],
    };
    const disabled: WaTemplate = {
      id: '1004',
      name: 'apagada',
      language: 'es_AR',
      category: 'UTILITY',
      status: 'DISABLED',
      rejected_reason: null,
      components: [{ type: 'BODY', text: 'x' }],
    };
    mockApi(routes([pending, withImage, disabled]));
    renderWithProviders(<TemplatesCard accounts={[ACCOUNT]} accountId="wa-1" onSelect={() => {}} />, {
      me: CLIENT_USER,
    });
    expect(await screen.findByRole('button', { name: 'Editar alta_pendiente' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Editar con_imagen' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Editar apagada' })).toBeDisabled();
    // En revisión sí se puede borrar; una deshabilitada no (Meta la rechaza).
    expect(screen.getByRole('button', { name: 'Borrar alta_pendiente' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Borrar apagada' })).toBeDisabled();
  });

  it('borrar pide confirmación (30 días del nombre si es aprobada) y manda DELETE sin force', async () => {
    const { calls } = mockApi({
      ...routes([APPROVED]),
      [`DELETE ${TEMPLATES}/1001`]: () => new Response(null, { status: 204 }),
    });
    renderWithProviders(<TemplatesCard accounts={[ACCOUNT]} accountId="wa-1" onSelect={() => {}} />, {
      me: CLIENT_USER,
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Borrar equipo_rotacion' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText(/30 días/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Borrar' }));
    const del = await waitFor(() => {
      const found = calls.find((c) => c.method === 'DELETE');
      if (!found) throw new Error('sin DELETE');
      return found;
    });
    expect(del.path).toBe(`${TEMPLATES}/1001`);
    expect(del.search).toBe('');
    // Borrada: el modal se cierra y la lista se vuelve a leer.
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await waitFor(() =>
      expect(calls.filter((c) => c.method === 'GET' && c.path === TEMPLATES).length).toBeGreaterThanOrEqual(2),
    );
  });

  it('el 409 de plantilla en uso muestra los usos y «borrar igual» manda force', async () => {
    let forced = false;
    const { calls } = mockApi({
      ...routes([APPROVED]),
      [`DELETE ${TEMPLATES}/1001`]: () =>
        forced
          ? new Response(null, { status: 204 })
          : jsonResponse(
              {
                detail: 'La usa: campaña Turnos, área Guardia',
                code: 'template_in_use',
                errors: [
                  { kind: 'campaign', id: 'c-1', name: 'Turnos' },
                  { kind: 'area', id: 'a-1', name: 'Guardia' },
                ],
              },
              409,
            ),
    });
    renderWithProviders(<TemplatesCard accounts={[ACCOUNT]} accountId="wa-1" onSelect={() => {}} />, {
      me: CLIENT_USER,
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Borrar equipo_rotacion' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Borrar' }));
    // Los usos del 409, por nombre (la clase y el nombre van en nodos distintos).
    expect(await within(dialog).findByText('la campaña')).toBeInTheDocument();
    expect(within(dialog).getByText('Turnos')).toBeInTheDocument();
    expect(within(dialog).getByText('el área')).toBeInTheDocument();
    expect(within(dialog).getByText('Guardia')).toBeInTheDocument();
    forced = true;
    await userEvent.click(within(dialog).getByRole('button', { name: 'Borrar igual' }));
    const second = await waitFor(() => {
      const found = calls.filter((c) => c.method === 'DELETE');
      if (found.length < 2) throw new Error('sin segundo DELETE');
      return found[1];
    });
    expect(second.search).toBe('?force=true');
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
  });

  it('un error de Meta con mensaje se ve en la notificación', async () => {
    const show = vi.spyOn(notifications, 'show');
    mockApi({
      ...routes([APPROVED]),
      [`PUT ${TEMPLATES}/1001`]: () =>
        jsonResponse({ detail: 'Meta: contenido no permitido en el cuerpo', code: 'meta_error', errors: [] }, 502),
    });
    renderWithProviders(<TemplatesCard accounts={[ACCOUNT]} accountId="wa-1" onSelect={() => {}} />, {
      me: CLIENT_USER,
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar equipo_rotacion' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    await waitFor(() =>
      expect(show).toHaveBeenCalledWith(
        expect.objectContaining({ color: 'red', message: expect.stringMatching(/contenido no permitido/) }),
      ),
    );
    // El modal queda abierto: la edición no se guardó.
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
