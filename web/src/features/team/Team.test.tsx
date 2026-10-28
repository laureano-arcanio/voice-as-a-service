import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { HandoffArea, TeamMember } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { scheduleError, toDraft, toSchedule } from './schedule';
import { TeamPage } from './TeamPage';

const ANA: TeamMember = {
  id: 'm1',
  client_id: 'c-1',
  name: 'Ana Pérez',
  phone: '+5493515551234',
  user_id: null,
  active: true,
  created_at: '2026-10-20T12:00:00Z',
};
const LUIS: TeamMember = {
  ...ANA,
  id: 'm2',
  name: 'Luis Gómez',
  phone: null,
  active: false,
};

const VENTAS: HandoffArea = {
  id: 'a1',
  client_id: 'c-1',
  name: 'Ventas',
  description: 'Precios y presupuestos',
  active: true,
  member_ids: ['m1'],
  strategy: 'sequential',
  ring_seconds: 20,
  schedule: { tz: 'America/Argentina/Buenos_Aires', week: { mon: [['09:00', '18:00']] }, closed: [] },
  schedule_text: 'los lunes de 09:00 a 18:00',
  open_now: false,
  fallback: 'take_message',
  on_person_hangup: 'resume',
  return_digits: '2',
  messages: { transfer: 'Ya te paso con Ventas.' },
  created_at: '2026-10-20T12:00:00Z',
};
const POSVENTA: HandoffArea = {
  ...VENTAS,
  id: 'a2',
  name: 'Posventa',
  description: '',
  member_ids: [],
  schedule: null,
  schedule_text: 'todos los días a toda hora',
  open_now: true,
  messages: {},
};

const DEFAULTS = {
  messages: {
    transfer: 'Te paso con {{area}}, un momento por favor.',
    whisper: 'Derivación de {{area}}: {{resumen}}. Marcá 1 para atender.',
    no_answer: 'No pude comunicarte con {{area}} en este momento.',
    busy: 'En este momento {{area}} está ocupado.',
    after_hours: '{{area}} atiende {{horario}}. Te tomo el mensaje y te contactan.',
    resume: '¿Te puedo ayudar con algo más?',
    goodbye: 'Gracias por comunicarte, que tengas un buen día.',
  },
  variables: ['area', 'persona', 'cliente', 'resumen', 'horario'],
};

interface Seen {
  method: string;
  path: string;
  search: string;
  body?: unknown;
}

function mockApi(extra: Record<string, () => Response> = {}) {
  const routes: Record<string, () => Response> = {
    'GET /api/v1/team': () => jsonResponse([ANA, LUIS]),
    'GET /api/v1/handoff-areas': () => jsonResponse([VENTAS, POSVENTA]),
    'GET /api/v1/handoff-areas/defaults': () => jsonResponse(DEFAULTS),
    'GET /api/v1/clients': () => jsonResponse([{ id: 'c-1', name: 'Acme' }]),
    ...extra,
  };
  const calls: Seen[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const url = new URL(req.url);
      const body =
        req.method === 'GET'
          ? undefined
          : await req
              .clone()
              .json()
              .catch(() => undefined);
      calls.push({ method: req.method, path: url.pathname, search: url.search, body });
      const route = routes[`${req.method} ${url.pathname}`];
      return route ? route() : jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return calls;
}

const sent = (calls: Seen[], method: string, path: string) =>
  calls.find((c) => c.method === method && c.path === path)?.body;

afterEach(() => vi.unstubAllGlobals());

describe('equipo: horario', () => {
  it('sin horario atiende siempre y manda null', () => {
    const d = toDraft(null);
    expect(d.always).toBe(true);
    expect(toSchedule(d)).toBeNull();
    expect(toSchedule({ ...d, always: false })).toEqual({
      tz: 'America/Argentina/Buenos_Aires',
      week: {
        mon: [['09:00', '18:00']],
        tue: [['09:00', '18:00']],
        wed: [['09:00', '18:00']],
        thu: [['09:00', '18:00']],
        fri: [['09:00', '18:00']],
      },
      closed: [],
    });
  });

  it('valida franjas incompletas, al revés y superpuestas', () => {
    const d = { ...toDraft(null), always: false };
    expect(scheduleError(d)).toBeNull();
    expect(scheduleError({ ...d, week: { ...d.week, mon: [['18:00', '09:00']] } })).toMatch(
      /18:00 tiene que ser antes que 09:00/,
    );
    expect(
      scheduleError({
        ...d,
        week: {
          ...d.week,
          mon: [
            ['09:00', '13:00'],
            ['12:00', '18:00'],
          ],
        },
      }),
    ).toMatch(/superpuestas/);
    expect(scheduleError({ ...d, week: { ...d.week, tue: [['09:00', '']] } })).toMatch(/Completá/);
    const empty = Object.fromEntries(Object.keys(d.week).map((k) => [k, []])) as unknown as typeof d.week;
    expect(scheduleError({ ...d, week: empty })).toMatch(/al menos una franja/);
  });
});

const PRESENCE = [
  { user_id: 'u-1', team_member_id: 'm1', name: 'Ana Pérez', available: true, busy: false },
  { user_id: 'u-2', team_member_id: null, name: 'Marcos', available: false, busy: false },
  { user_id: 'u-3', team_member_id: 'm2', name: 'Luis Gómez', available: true, busy: true },
];

describe('equipo: pantalla', () => {
  it('muestra si cada persona con usuario del panel está disponible', async () => {
    mockApi({
      'GET /api/v1/plan/features': () =>
        jsonResponse({
          client_id: 'c-1',
          tier_name: 'Sucursal',
          free: false,
          features: { team: { enabled: true }, direct_calls: { enabled: true } },
        }),
      'GET /api/v1/team': () =>
        jsonResponse([
          { ...ANA, user_id: 'u-1' },
          { ...LUIS, user_id: 'u-3' },
          { ...ANA, id: 'm3', name: 'Marta Ruiz', user_id: 'u-4' },
          { ...ANA, id: 'm4', name: 'Sin Usuario', user_id: null },
        ]),
      'GET /api/v1/team/presence': () =>
        jsonResponse([
          ...PRESENCE,
          { user_id: 'u-4', team_member_id: 'm3', name: 'Marta Ruiz', available: false, busy: false },
        ]),
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    const ana = await screen.findByRole('row', { name: /^Ana Pérez/ });
    expect(await within(ana).findByText('Disponible')).toBeInTheDocument();
    expect(
      within(screen.getByRole('row', { name: /^Luis Gómez/ })).getByText('En una llamada'),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole('row', { name: /^Marta Ruiz/ })).getByText('No disponible'),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole('row', { name: /^Sin Usuario/ })).queryByText(/Disponible/),
    ).not.toBeInTheDocument();
  });

  it('sin llamadas directas en el plan no pide la presencia ni muestra la columna', async () => {
    const calls = mockApi({
      'GET /api/v1/plan/features': () =>
        jsonResponse({
          client_id: 'c-1',
          tier_name: 'Free',
          free: true,
          features: {
            team: { enabled: true, reason: null },
            direct_calls: { enabled: false, reason: 'Está en los planes Mostrador, Sucursal y Red.' },
          },
        }),
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await screen.findByRole('row', { name: /^Ana Pérez/ });
    expect(screen.queryByRole('columnheader', { name: 'En el panel' })).not.toBeInTheDocument();
    expect(calls.some((c) => c.path === '/api/v1/team/presence')).toBe(false);
  });

  it('cliente: personas y áreas con su horario y estado', async () => {
    mockApi();
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    const ana = await screen.findByRole('row', { name: /^Ana Pérez/ });
    expect(within(ana).getByText('Activa')).toBeInTheDocument();
    const luis = screen.getByRole('row', { name: /^Luis Gómez/ });
    expect(within(luis).getByText('Inactiva')).toBeInTheDocument();
    const ventas = await screen.findByRole('row', { name: /Ventas/ });
    expect(within(ventas).getByText('Los lunes de 09:00 a 18:00')).toBeInTheDocument();
    expect(within(ventas).getByText('Fuera de horario')).toBeInTheDocument();
    expect(within(ventas).getByText('Ana Pérez')).toBeInTheDocument();
    const posventa = screen.getByRole('row', { name: /Posventa/ });
    expect(within(posventa).getByText('Atiende ahora')).toBeInTheDocument();
    expect(within(posventa).getByText('Todos los días a toda hora')).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Cliente' })).not.toBeInTheDocument();
  });

  it('vacío: explica qué cargar', async () => {
    mockApi({
      'GET /api/v1/team': () => jsonResponse([]),
      'GET /api/v1/handoff-areas': () => jsonResponse([]),
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    expect(await screen.findByText(/Todavía no hay personas en el equipo/)).toBeInTheDocument();
    expect(await screen.findByText(/Todavía no hay áreas/)).toBeInTheDocument();
  });
});

describe('equipo: personas', () => {
  it('pide teléfono o usuario del panel y crea', async () => {
    const calls = mockApi({ 'POST /api/v1/team': () => jsonResponse(ANA, 201) });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Agregar persona/ }));
    const dialog = await screen.findByRole('dialog', { name: 'Nueva persona del equipo' });
    await userEvent.type(within(dialog).getByLabelText('Nombre'), 'Ana Pérez');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Agregar persona' }));
    expect(await within(dialog).findByText('Cargá un teléfono o un usuario del panel')).toBeInTheDocument();
    await userEvent.type(within(dialog).getByLabelText('Teléfono'), '351 555-1234');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Agregar persona' }));
    await waitFor(() => expect(sent(calls, 'POST', '/api/v1/team')).toBeDefined());
    expect(sent(calls, 'POST', '/api/v1/team')).toEqual({
      name: 'Ana Pérez',
      phone: '351 555-1234',
      user_id: null,
      active: true,
    });
  });

  it('acepta una persona con solo el usuario del panel y ofrece los usuarios libres', async () => {
    const calls = mockApi({
      'GET /api/v1/team/presence': () => jsonResponse(PRESENCE),
      'POST /api/v1/team': () => jsonResponse({ ...ANA, user_id: 'u-2' }, 201),
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Agregar persona/ }));
    const dialog = await screen.findByRole('dialog', { name: 'Nueva persona del equipo' });
    await userEvent.type(within(dialog).getByLabelText('Nombre'), 'Marcos');
    const user = within(dialog).getByRole('textbox', { name: /Usuario del panel/ });
    await userEvent.click(user);
    // Ana ya es una persona del equipo: solo queda el usuario libre.
    expect(screen.queryByRole('option', { name: 'Ana Pérez', hidden: true })).not.toBeInTheDocument();
    await userEvent.click(await screen.findByRole('option', { name: 'Marcos', hidden: true }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Agregar persona' }));
    await waitFor(() => expect(sent(calls, 'POST', '/api/v1/team')).toBeDefined());
    expect(sent(calls, 'POST', '/api/v1/team')).toEqual({
      name: 'Marcos',
      phone: null,
      user_id: 'u-2',
      active: true,
    });
  });

  it('al editar, el usuario de la persona sigue elegido y se conserva', async () => {
    const calls = mockApi({
      'GET /api/v1/team': () => jsonResponse([{ ...ANA, user_id: 'u-1' }, LUIS]),
      'GET /api/v1/team/presence': () => jsonResponse(PRESENCE),
      'PATCH /api/v1/team/m1': () => jsonResponse(ANA),
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar a Ana Pérez' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar a Ana Pérez' });
    await waitFor(() =>
      expect(within(dialog).getByRole('textbox', { name: /Usuario del panel/ })).toHaveValue('Ana Pérez'),
    );
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(sent(calls, 'PATCH', '/api/v1/team/m1')).toBeDefined());
    expect(sent(calls, 'PATCH', '/api/v1/team/m1')).toMatchObject({ user_id: 'u-1' });
  });

  it('borra con confirmación y avisa de qué áreas sale', async () => {
    const calls = mockApi({ 'DELETE /api/v1/team/m1': () => new Response(null, { status: 204 }) });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Borrar a Ana Pérez' }));
    const dialog = await screen.findByRole('dialog', { name: /Borrar a Ana Pérez/ });
    expect(within(dialog).getByText(/Sale del área Ventas/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Borrar' }));
    await waitFor(() =>
      expect(calls.some((c) => c.method === 'DELETE' && c.path === '/api/v1/team/m1')).toBe(true),
    );
  });
});

describe('equipo: áreas', () => {
  it('crea un área con personas en orden, horario y un mensaje propio', async () => {
    const calls = mockApi({ 'POST /api/v1/handoff-areas': () => jsonResponse(VENTAS, 201) });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Crear área/ }));
    const dialog = await screen.findByRole('dialog', { name: 'Nueva área' });
    await userEvent.type(within(dialog).getByLabelText('Nombre'), 'Ventas');
    await userEvent.type(within(dialog).getByLabelText(/Qué atiende/), 'Precios');

    const add = within(dialog).getByRole('textbox', { name: 'Agregar persona al área' });
    await userEvent.click(add);
    await userEvent.click(await screen.findByRole('option', { name: 'Ana Pérez', hidden: true }));
    await userEvent.click(add);
    await userEvent.click(await screen.findByRole('option', { name: 'Luis Gómez', hidden: true }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Subir a Luis Gómez' }));
    expect(within(dialog).getByText('Sin teléfono')).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole('switch', { name: /Atiende siempre/ }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Quitar franja 1 del viernes' }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Agregar franja el sábado' }));

    const transfer = within(dialog).getByLabelText('Antes de transferir');
    expect(transfer).toHaveAttribute('placeholder', DEFAULTS.messages.transfer);
    await userEvent.type(transfer, 'Ya te paso.');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear área' }));

    await waitFor(() => expect(sent(calls, 'POST', '/api/v1/handoff-areas')).toBeDefined());
    expect(sent(calls, 'POST', '/api/v1/handoff-areas')).toEqual({
      name: 'Ventas',
      description: 'Precios',
      active: true,
      member_ids: ['m2', 'm1'],
      strategy: 'sequential',
      ring_seconds: 20,
      schedule: {
        tz: 'America/Argentina/Buenos_Aires',
        week: {
          mon: [['09:00', '18:00']],
          tue: [['09:00', '18:00']],
          wed: [['09:00', '18:00']],
          thu: [['09:00', '18:00']],
          sat: [['09:00', '18:00']],
        },
        closed: [],
      },
      on_person_hangup: 'resume',
      return_digits: '2',
      messages: { transfer: 'Ya te paso.' },
    });
  });

  it('edita: vuelve un mensaje al default, atiende siempre y se despide al cortar', async () => {
    const calls = mockApi({ 'PATCH /api/v1/handoff-areas/a1': () => jsonResponse(VENTAS) });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Ventas' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar área Ventas' });
    expect(within(dialog).getByLabelText('Antes de transferir')).toHaveValue('Ya te paso con Ventas.');
    await userEvent.click(
      within(dialog).getByRole('button', { name: 'Volver al default: Antes de transferir' }),
    );
    expect(within(dialog).getByLabelText('Antes de transferir')).toHaveValue('');
    await userEvent.click(within(dialog).getByRole('switch', { name: /Atiende siempre/ }));
    await userEvent.click(within(dialog).getByRole('radio', { name: 'Se despide y corta' }));
    expect(within(dialog).getByLabelText(/Despedida/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a1')).toBeDefined());
    expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a1')).toMatchObject({
      schedule: null,
      on_person_hangup: 'end',
      messages: {},
      member_ids: ['m1'],
    });
  });

  it('la tecla de vuelta no puede ser 1 ni llevar *', async () => {
    const calls = mockApi();
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Posventa' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar área Posventa' });
    const digits = within(dialog).getByLabelText(/Tecla para devolverle la llamada a la IA/);
    await userEvent.clear(digits);
    await userEvent.type(digits, '1');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    expect(await within(dialog).findByText(/El 1 es para atender/)).toBeInTheDocument();
    await userEvent.clear(digits);
    await userEvent.type(digits, '*2');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    expect(await within(dialog).findByText(/sin \*/)).toBeInTheDocument();
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false);
  });

  it('borra un área con confirmación', async () => {
    const calls = mockApi({ 'DELETE /api/v1/handoff-areas/a2': () => new Response(null, { status: 204 }) });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Borrar el área Posventa' }));
    const dialog = await screen.findByRole('dialog', { name: /Borrar el área Posventa/ });
    await userEvent.click(within(dialog).getByRole('button', { name: 'Borrar' }));
    await waitFor(() =>
      expect(calls.some((c) => c.method === 'DELETE' && c.path === '/api/v1/handoff-areas/a2')).toBe(true),
    );
  });
});
