import { screen, waitFor, within } from '@testing-library/react';
import { notifications } from '@mantine/notifications';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { HandoffArea, TeamMember } from '@/api/types';
import { CATALOG } from '@/components/variables/fixtures';
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
  whatsapp_notify: false,
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
  after_hours_area_id: null,
  no_answer_area_id: null,
  no_answer_member_id: null,
  delivery: 'call',
  whatsapp: null,
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
    notified: 'Ya le avisé a {{area}}. Te van a contactar.',
    accepted: '{{persona}} recibió tu pedido y te va a contactar.',
    relay_failed: 'No pude hacerle llegar tu mensaje a {{persona}}.',
    operator_ack: 'Recibido. Estamos confirmando.',
    operator_contact: 'Contacto: {{nombre}}, {{cliente}}.',
    post_call_failed: 'No se pudo confirmar el registro.',
    tap_wait: 'Estamos confirmando.',
    tap_taken: 'Ya la tomó {{persona}}.',
    tap_closed: 'Esta solicitud ya se cerró.',
  },
  variables: ['area', 'persona', 'cliente', 'resumen', 'horario', 'nombre'],
  pre_accept_messages: ['operator_ack', 'tap_wait', 'tap_taken', 'tap_closed'],
  pre_accept_variables: ['area', 'persona', 'horario'],
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
    'GET /api/v1/variables/catalog': () => jsonResponse(CATALOG),
    'GET /api/v1/agents': () => jsonResponse([]),
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
      whatsapp_notify: false,
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
      whatsapp_notify: false,
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
      delivery: 'call',
      after_hours_area_id: null,
      no_answer_area_id: null,
      no_answer_member_id: null,
      whatsapp: null,
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

  it('los mensajes del área ofrecen las variables de derivación al tipear {{', async () => {
    mockApi();
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Ventas' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar área Ventas' });
    const transfer = within(dialog).getByLabelText('Antes de transferir');
    await userEvent.click(transfer);
    await userEvent.type(transfer, '{{{{');
    await waitFor(() => {
      const names = screen
        .queryAllByRole('option', { hidden: true })
        .map((o) => o.querySelector('p')?.textContent);
      expect(names).toContain('persona');
      expect(names).toContain('resumen');
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

// ---------- WhatsApp: personas, rutas y avisos ----------

const ACCOUNT = {
  id: 'wa1',
  client_id: 'c-1',
  agent_id: 'ag-1',
  phone_number_id: '111',
  waba_id: '222',
  display_phone_number: '+54 9 351 555-0000',
  name: 'Guardia',
  active: true,
  status: 'connected',
};

const tpl = (name: string, body: string, buttons?: { type: string; text: string }[]) => ({
  id: `t-${name}`,
  name,
  language: 'es_AR',
  category: 'UTILITY',
  status: 'APPROVED',
  components: [{ type: 'BODY', text: body }, ...(buttons ? [{ type: 'BUTTONS', buttons }] : [])],
});

const TEMPLATES = [
  tpl('equipo_rotacion', 'Hay un pedido urgente en {{1}}. Tocá Aceptar.', [
    { type: 'QUICK_REPLY', text: 'Aceptar' },
  ]),
  tpl('equipo_llamada', 'Te estamos llamando por {{1}}.'),
  tpl('equipo_consulta', 'Nuevo pedido en {{1}}. Persona: {{2}}, teléfono {{3}}.'),
  { ...tpl('en_revision', 'Texto {{1}}'), status: 'PENDING' },
];

const PLAN_WA = (enabled: boolean) => () =>
  jsonResponse({
    client_id: 'c-1',
    tier_name: 'Sucursal',
    free: false,
    features: {
      team: { enabled: true },
      whatsapp: { enabled, reason: enabled ? null : 'Está en Mostrador.' },
    },
  });

const waRoutes = () => ({
  'GET /api/v1/whatsapp/accounts': () => jsonResponse([ACCOUNT]),
  'GET /api/v1/whatsapp/accounts/wa1/templates': () => jsonResponse(TEMPLATES),
});

/** Elige una opción de un selector de Mantine por su rótulo (los dropdowns cerrados siguen en el DOM). */
async function choose(dialog: HTMLElement, label: RegExp | string, option: RegExp | string) {
  await userEvent.click(within(dialog).getByRole('textbox', { name: label }));
  const list = screen.getByRole('listbox', { name: label, hidden: true });
  await userEvent.click(await within(list).findByRole('option', { name: option, hidden: true }));
}

describe('equipo: Recibe WhatsApp', () => {
  it('sin teléfono el interruptor está deshabilitado y no se manda prendido', async () => {
    const calls = mockApi({
      'GET /api/v1/team': () => jsonResponse([ANA, { ...LUIS, user_id: 'u-2' }]),
      'GET /api/v1/team/presence': () => jsonResponse(PRESENCE),
      'PATCH /api/v1/team/m2': () => jsonResponse({ ...LUIS, whatsapp_notify: false }),
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar a Luis Gómez' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar a Luis Gómez' });
    expect(within(dialog).getByRole('switch', { name: /Recibe WhatsApp/ })).toBeDisabled();
    expect(within(dialog).getByText(/Cargá un teléfono para poder avisarle/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(sent(calls, 'PATCH', '/api/v1/team/m2')).toBeDefined());
    expect(sent(calls, 'PATCH', '/api/v1/team/m2')).toMatchObject({ whatsapp_notify: false });
  });

  it('con teléfono lo prende, se guarda, y al reabrir sigue prendido', async () => {
    let ana = ANA;
    const calls = mockApi({
      'GET /api/v1/team': () => jsonResponse([ana, LUIS]),
      'PATCH /api/v1/team/m1': () => {
        ana = { ...ANA, whatsapp_notify: true };
        return jsonResponse(ana);
      },
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar a Ana Pérez' }));
    let dialog = await screen.findByRole('dialog', { name: 'Editar a Ana Pérez' });
    const toggle = within(dialog).getByRole('switch', { name: /Recibe WhatsApp/ });
    expect(toggle).toBeEnabled();
    expect(toggle).not.toBeChecked();
    await userEvent.click(toggle);
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(sent(calls, 'PATCH', '/api/v1/team/m1')).toBeDefined());
    expect(sent(calls, 'PATCH', '/api/v1/team/m1')).toMatchObject({ whatsapp_notify: true });

    expect(await screen.findByText('Recibe WhatsApp')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Editar a Ana Pérez' }));
    dialog = await screen.findByRole('dialog', { name: 'Editar a Ana Pérez' });
    expect(within(dialog).getByRole('switch', { name: /Recibe WhatsApp/ })).toBeChecked();
  });

  it('si se borra el teléfono, el interruptor se apaga y no se manda prendido', async () => {
    const calls = mockApi({
      'GET /api/v1/team': () => jsonResponse([{ ...ANA, whatsapp_notify: true, user_id: 'u-1' }, LUIS]),
      'GET /api/v1/team/presence': () => jsonResponse(PRESENCE),
      'PATCH /api/v1/team/m1': () => jsonResponse(ANA),
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar a Ana Pérez' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar a Ana Pérez' });
    await userEvent.clear(within(dialog).getByLabelText('Teléfono'));
    expect(within(dialog).getByRole('switch', { name: /Recibe WhatsApp/ })).not.toBeChecked();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(sent(calls, 'PATCH', '/api/v1/team/m1')).toBeDefined());
    expect(sent(calls, 'PATCH', '/api/v1/team/m1')).toMatchObject({ phone: null, whatsapp_notify: false });
  });
});

describe('equipo: áreas con rutas y WhatsApp', () => {
  it('elige a qué área pasa fuera de horario y si nadie acepta, sin ofrecerse a sí misma', async () => {
    const calls = mockApi({ 'PATCH /api/v1/handoff-areas/a1': () => jsonResponse(VENTAS) });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Ventas' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar área Ventas' });
    const list = screen.getByRole('listbox', { name: /Fuera de horario, pasa a/, hidden: true });
    expect(within(list).queryByRole('option', { name: 'Ventas', hidden: true })).not.toBeInTheDocument();
    await choose(dialog, /Fuera de horario, pasa a/, 'Posventa');
    await choose(dialog, 'Si nadie atiende', 'Otra área');
    await choose(dialog, 'Área', 'Posventa');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a1')).toBeDefined());
    expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a1')).toMatchObject({
      after_hours_area_id: 'a2',
      no_answer_area_id: 'a2',
      no_answer_member_id: null,
      delivery: 'call',
      whatsapp: null,
    });
  });

  it('si nadie atiende: una persona con teléfono y fuera del área; cambiar de destino limpia el otro', async () => {
    const calls = mockApi({
      'GET /api/v1/team': () => jsonResponse([ANA, LUIS, { ...ANA, id: 'm3', name: 'Marta Sosa', phone: '+5493515550000' }]),
      'PATCH /api/v1/handoff-areas/a1': () => jsonResponse(VENTAS),
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Ventas' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar área Ventas' });
    // Por defecto vuelve el agente y no pide nada más.
    expect(within(dialog).getByRole('textbox', { name: 'Si nadie atiende' })).toHaveValue(
      'El agente toma el mensaje',
    );
    expect(within(dialog).queryByRole('textbox', { name: 'Persona' })).not.toBeInTheDocument();
    await choose(dialog, 'Si nadie atiende', 'Una persona');
    // Ana ya está en el área; Luis está inactiva y sin teléfono.
    const list = screen.getByRole('listbox', { name: 'Persona', hidden: true });
    expect(within(list).queryByRole('option', { name: /Ana/, hidden: true })).not.toBeInTheDocument();
    expect(within(list).queryByRole('option', { name: /Luis/, hidden: true })).not.toBeInTheDocument();
    await choose(dialog, 'Persona', /Marta Sosa/);
    // Sin elegir otra cosa, se manda la persona y ninguna área.
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a1')).toBeDefined());
    expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a1')).toMatchObject({
      no_answer_member_id: 'm3',
      no_answer_area_id: null,
    });
  });

  it('cambiar de «una persona» a «otra área» no manda la persona', async () => {
    const withPerson = { ...POSVENTA, no_answer_member_id: 'm1' };
    const calls = mockApi({
      'GET /api/v1/handoff-areas': () => jsonResponse([VENTAS, withPerson]),
      'PATCH /api/v1/handoff-areas/a2': () => jsonResponse(withPerson),
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Posventa' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar área Posventa' });
    expect(within(dialog).getByRole('textbox', { name: 'Persona' })).toHaveValue('Ana Pérez · +5493515551234');
    await choose(dialog, 'Si nadie atiende', 'Otra área');
    expect(within(dialog).queryByRole('textbox', { name: 'Persona' })).not.toBeInTheDocument();
    await choose(dialog, 'Área', 'Ventas');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a2')).toBeDefined());
    expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a2')).toMatchObject({
      no_answer_area_id: 'a1',
      no_answer_member_id: null,
    });
  });

  it('si la persona de «si nadie atiende» se suma al área, se limpia y hay que elegir otra', async () => {
    const withPerson = { ...POSVENTA, no_answer_member_id: 'm1' };
    const calls = mockApi({
      'GET /api/v1/handoff-areas': () => jsonResponse([VENTAS, withPerson]),
      'PATCH /api/v1/handoff-areas/a2': () => jsonResponse(withPerson),
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Posventa' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar área Posventa' });
    expect(within(dialog).getByRole('textbox', { name: 'Persona' })).toHaveValue('Ana Pérez · +5493515551234');
    await choose(dialog, 'Agregar persona al área', /Ana/);
    await waitFor(() => expect(within(dialog).getByRole('textbox', { name: 'Persona' })).toHaveValue(''));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    expect(await within(dialog).findByText(/Elegí la persona/)).toBeInTheDocument();
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false);
  });

  it('un área de aviso por WhatsApp pide número y plantilla, y manda las variables en orden', async () => {
    const calls = mockApi({
      ...waRoutes(),
      'GET /api/v1/plan/features': PLAN_WA(true),
      'POST /api/v1/handoff-areas': () => jsonResponse(VENTAS, 201),
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Crear área/ }));
    const dialog = await screen.findByRole('dialog', { name: 'Nueva área' });
    await userEvent.type(within(dialog).getByLabelText('Nombre'), 'Consultas');
    await userEvent.click(within(dialog).getByRole('radio', { name: 'Solo aviso por WhatsApp' }));
    // Sin timbre ni "Durante la llamada" en un área de aviso.
    expect(within(dialog).queryByLabelText(/Timbre por persona/)).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText(/Tecla para devolverle/)).not.toBeInTheDocument();
    // Los mensajes propios del aviso.
    expect(within(dialog).getByLabelText('Después de avisar')).toBeInTheDocument();
    expect(within(dialog).queryByLabelText('Antes de transferir')).not.toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear área' }));
    expect(
      await within(dialog).findByText(/Elegí el número de WhatsApp y la plantilla del aviso/),
    ).toBeInTheDocument();
    expect(calls.some((c) => c.method === 'POST' && c.path === '/api/v1/handoff-areas')).toBe(false);

    await choose(dialog, /Número que envía/, /555-0000/);
    await choose(dialog, /Plantilla del aviso/, /equipo_consulta/);
    // Solo las aprobadas.
    const tplList = screen.getByRole('listbox', { name: /Plantilla del aviso/, hidden: true });
    expect(
      within(tplList).queryByRole('option', { name: /en_revision/, hidden: true }),
    ).not.toBeInTheDocument();
    // En el aviso sí se ofrece el teléfono de la persona.
    await userEvent.click(within(dialog).getByRole('textbox', { name: /Valor de \{\{3\}\}/ }));
    expect(
      await within(screen.getByRole('listbox', { name: /Valor de \{\{3\}\}/, hidden: true })).findByRole(
        'option',
        {
          name: 'cliente',
          hidden: true,
        },
      ),
    ).toBeInTheDocument();

    // Error de validacion de un modal largo: avisa con una notificacion y lleva el scroll al error.
    const show = vi.spyOn(notifications, 'show');
    const scroll = vi.spyOn(window.HTMLElement.prototype, 'scrollIntoView');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear área' }));
    expect(await within(dialog).findByText(/elegí qué valor va en \{\{1\}\}/)).toBeInTheDocument();
    expect(show).toHaveBeenCalledWith(
      expect.objectContaining({ message: expect.stringMatching(/elegí qué valor va en \{\{1\}\}/) }),
    );
    await waitFor(() => expect(scroll).toHaveBeenCalled());
    show.mockRestore();
    scroll.mockRestore();
    await userEvent.type(within(dialog).getByRole('textbox', { name: /Valor de \{\{1\}\}/ }), 'area');
    await userEvent.type(within(dialog).getByRole('textbox', { name: /Valor de \{\{2\}\}/ }), 'nombre');
    await userEvent.type(within(dialog).getByRole('textbox', { name: /Valor de \{\{3\}\}/ }), 'cliente');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear área' }));

    await waitFor(() => expect(sent(calls, 'POST', '/api/v1/handoff-areas')).toBeDefined());
    expect(sent(calls, 'POST', '/api/v1/handoff-areas')).toMatchObject({
      name: 'Consultas',
      delivery: 'whatsapp',
      whatsapp: {
        account_id: 'wa1',
        template: { name: 'equipo_consulta', language: 'es_AR', params: ['area', 'nombre', 'cliente'] },
        wait_seconds: 120,
      },
    });
    expect(
      (sent(calls, 'POST', '/api/v1/handoff-areas') as { whatsapp: object }).whatsapp,
    ).not.toHaveProperty('call_template');
  });

  it('en la rotación no deja usar cliente, y guarda rotación, llamada y espera; al reabrir conserva todo', async () => {
    const saved = {
      ...VENTAS,
      whatsapp: {
        account_id: 'wa1',
        template: { name: 'equipo_rotacion', language: 'es_AR', params: ['area'] },
        call_template: { name: 'equipo_llamada', language: 'es_AR', params: ['area'] },
        wait_seconds: 90,
      },
    };
    let current: typeof VENTAS = VENTAS;
    const calls = mockApi({
      ...waRoutes(),
      'GET /api/v1/plan/features': PLAN_WA(true),
      'GET /api/v1/handoff-areas': () => jsonResponse([current, POSVENTA]),
      'PATCH /api/v1/handoff-areas/a1': () => {
        current = saved;
        return jsonResponse(saved);
      },
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Ventas' }));
    let dialog = await screen.findByRole('dialog', { name: 'Editar área Ventas' });
    await choose(dialog, /Número que envía/, /555-0000/);
    await choose(dialog, /Plantilla de rotación/, /equipo_rotacion/);
    await choose(dialog, /Plantilla de la llamada/, /equipo_llamada/);
    const rotationValue = within(dialog).getAllByRole('textbox', { name: /Valor de \{\{1\}\}/ })[0]!;
    await userEvent.click(rotationValue);
    // El teléfono de la persona no sale antes de que alguien acepte.
    const rotationList = within(
      screen.getAllByRole('listbox', { name: /Valor de \{\{1\}\}/, hidden: true })[0]!,
    );
    expect(await rotationList.findByRole('option', { name: 'resumen', hidden: true })).toBeInTheDocument();
    expect(rotationList.queryByRole('option', { name: 'cliente', hidden: true })).not.toBeInTheDocument();
    await userEvent.type(rotationValue, 'cliente');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    expect(
      await within(dialog).findByText(/el teléfono de la persona \(cliente\) no sale antes/),
    ).toBeInTheDocument();
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false);

    await userEvent.clear(rotationValue);
    await userEvent.type(rotationValue, 'area');
    await userEvent.type(within(dialog).getAllByRole('textbox', { name: /Valor de \{\{1\}\}/ })[1]!, 'area');
    const wait = within(dialog).getByLabelText(/Espera por persona/);
    await userEvent.clear(wait);
    await userEvent.type(wait, '90');
    // La rotación trae los mensajes del texto.
    expect(within(dialog).getByLabelText(/Datos del contacto/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a1')).toBeDefined());
    expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a1')).toMatchObject({
      delivery: 'call',
      whatsapp: saved.whatsapp,
    });

    // Reabrir: llega lo guardado.
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Ventas' }));
    dialog = await screen.findByRole('dialog', { name: 'Editar área Ventas' });
    await waitFor(() => expect(within(dialog).getByLabelText(/Espera por persona/)).toHaveValue('90 s'));
    expect(within(dialog).getByRole('textbox', { name: /Plantilla de rotación/ })).toHaveValue(
      'equipo_rotacion · es_AR',
    );
    expect(within(dialog).getByRole('textbox', { name: /Plantilla de la llamada/ })).toHaveValue(
      'equipo_llamada · es_AR',
    );
  });

  it('los mensajes de antes de aceptar dicen qué variables admiten; los demás no', async () => {
    mockApi({
      ...waRoutes(),
      'GET /api/v1/plan/features': PLAN_WA(true),
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Ventas' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar área Ventas' });
    await choose(dialog, /Número que envía/, /555-0000/);
    await choose(dialog, /Plantilla de rotación/, /equipo_rotacion/);
    const helpOf = (el: HTMLElement) =>
      (el.getAttribute('aria-describedby') ?? '')
        .split(' ')
        .map((id) => document.getElementById(id)?.textContent ?? '')
        .join(' ');
    const help = 'Todavía no lleva los datos de la persona: solo admite {{area}}, {{persona}}, {{horario}}.';
    for (const label of [
      /Al aceptar \(a la persona del equipo\)/,
      /Si toca Aceptar y aún se confirma/,
      /Si ya la tomó otra persona/,
      /Si la solicitud ya se cerró/,
    ]) {
      const field = within(dialog).getByLabelText(label);
      expect(helpOf(field)).toContain(help);
    }
    for (const label of [/Datos del contacto/, /Si falló el registro/, /^Antes de transferir/]) {
      const field = within(dialog).getByLabelText(label);
      expect(helpOf(field)).not.toContain('Todavía no lleva');
    }
  });

  it('la plantilla de rotación sin botón de respuesta rápida lo advierte', async () => {
    mockApi({ ...waRoutes(), 'GET /api/v1/plan/features': PLAN_WA(true) });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Ventas' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar área Ventas' });
    await choose(dialog, /Número que envía/, /555-0000/);
    await choose(dialog, /Plantilla de rotación/, /equipo_llamada/);
    expect(await within(dialog).findByText(/no tiene un botón de respuesta rápida/)).toBeInTheDocument();
  });

  it('sin WhatsApp en el plan, la sección lo dice y no pide cuentas', async () => {
    const calls = mockApi({ ...waRoutes(), 'GET /api/v1/plan/features': PLAN_WA(false) });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Ventas' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar área Ventas' });
    expect(await within(dialog).findByText(/no incluye WhatsApp/)).toBeInTheDocument();
    expect(calls.some((c) => c.path === '/api/v1/whatsapp/accounts')).toBe(false);
  });

  it('sin números conectados, la sección manda a conectar uno', async () => {
    mockApi({
      'GET /api/v1/plan/features': PLAN_WA(true),
      'GET /api/v1/whatsapp/accounts': () => jsonResponse([{ ...ACCOUNT, status: 'disconnected' }]),
    });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Ventas' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar área Ventas' });
    expect(await within(dialog).findByText(/No hay un número de WhatsApp conectado/)).toBeInTheDocument();
  });
});

// ---------- Errores de un campo: mensajes, campos ocultos y horario ----------

/** Ventas con rotación por WhatsApp de texto: se ven los mensajes de antes de aceptar. */
const ROTACION = {
  ...VENTAS,
  messages: { operator_ack: 'Hola {{persona}}', transfer: 'Ya te paso con Ventas.' },
  whatsapp: {
    account_id: 'wa1',
    template: { name: 'equipo_rotacion', language: 'es_AR', params: ['area'] },
    wait_seconds: 90,
  },
};

async function openRotacion(extra: Record<string, () => Response> = {}, defaults: object = DEFAULTS) {
  const calls = mockApi({
    ...waRoutes(),
    'GET /api/v1/plan/features': PLAN_WA(true),
    'GET /api/v1/handoff-areas': () => jsonResponse([ROTACION, POSVENTA]),
    'GET /api/v1/handoff-areas/defaults': () => jsonResponse(defaults),
    ...extra,
  });
  renderWithProviders(<TeamPage />, { me: CLIENT_USER });
  await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Ventas' }));
  const dialog = await screen.findByRole('dialog', { name: 'Editar área Ventas' });
  const ack = await within(dialog).findByLabelText(/Al aceptar \(a la persona del equipo\)/, {
    selector: 'textarea',
  });
  return { calls, dialog, ack };
}

const ALLOWED = '{{area}}, {{persona}}, {{horario}}';

describe('equipo: errores en el campo', () => {
  it('una variable de más en "Al aceptar" marca el campo con su nombre, avisa y lleva el scroll', async () => {
    const { calls, dialog, ack } = await openRotacion();
    await userEvent.clear(ack);
    await userEvent.type(ack, 'Hola {{{{cliente}}');
    const show = vi.spyOn(notifications, 'show');
    const scroll = vi.spyOn(window.HTMLElement.prototype, 'scrollIntoView');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    expect(
      await within(dialog).findByText(`Todavía no lleva los datos de la persona: solo admite ${ALLOWED}.`),
    ).toBeInTheDocument();
    expect(ack).toHaveAttribute('aria-invalid', 'true');
    expect(show).toHaveBeenCalledWith(
      expect.objectContaining({
        message: `Al aceptar (a la persona del equipo): Todavía no lleva los datos de la persona: solo admite ${ALLOWED}.`,
      }),
    );
    await waitFor(() => expect(scroll).toHaveBeenCalled());
    expect(scroll.mock.instances[0]).toBe(ack);
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false);
    // Al corregirlo, el error se va.
    await userEvent.clear(ack);
    await userEvent.type(ack, 'Hola {{{{persona}}');
    expect(ack).not.toHaveAttribute('aria-invalid', 'true');
    show.mockRestore();
    scroll.mockRestore();
  });

  it('el error del servidor (errors con messages.<clave>) marca el campo con su nombre, no la clave', async () => {
    // Sin las listas de la API el navegador no valida: lo rechaza el servidor.
    const { dialog, ack } = await openRotacion(
      {
        'PATCH /api/v1/handoff-areas/a1': () =>
          jsonResponse(
            {
              detail: `El mensaje operator_ack todavía no lleva los datos de la persona: solo admite ${ALLOWED}`,
              code: 'invalid',
              errors: [
                {
                  path: 'messages.operator_ack',
                  message: `Todavía no lleva los datos de la persona: solo admite ${ALLOWED}`,
                },
              ],
            },
            422,
          ),
      },
      { ...DEFAULTS, pre_accept_messages: [], pre_accept_variables: [] },
    );
    await userEvent.clear(ack);
    await userEvent.type(ack, 'Hola {{{{cliente}}');
    const show = vi.spyOn(notifications, 'show');
    const scroll = vi.spyOn(window.HTMLElement.prototype, 'scrollIntoView');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    expect(
      await within(dialog).findByText(`Todavía no lleva los datos de la persona: solo admite ${ALLOWED}`),
    ).toBeInTheDocument();
    expect(ack).toHaveAttribute('aria-invalid', 'true');
    const message = show.mock.calls.map((c) => c[0].message).join(' ');
    expect(message).toContain('Al aceptar (a la persona del equipo)');
    expect(message).not.toContain('operator_ack');
    await waitFor(() => expect(scroll.mock.instances[0]).toBe(ack));
    show.mockRestore();
    scroll.mockRestore();
  });

  it('un área de aviso no se bloquea por el timbre, la tecla ni un mensaje oculto inválidos, y conserva lo guardado', async () => {
    const { calls, dialog, ack } = await openRotacion({
      'PATCH /api/v1/handoff-areas/a1': () => jsonResponse(ROTACION),
    });
    // Lo oculto, mal escrito: la variable de más, el timbre vacío y la tecla *.
    await userEvent.clear(ack);
    await userEvent.type(ack, 'Hola {{{{cliente}}');
    const ring = within(dialog).getByLabelText(/Timbre por persona/);
    await userEvent.clear(ring);
    const digits = within(dialog).getByLabelText(/Tecla para devolverle la llamada a la IA/);
    await userEvent.clear(digits);
    await userEvent.type(digits, '*');
    await userEvent.click(within(dialog).getByRole('radio', { name: 'Solo aviso por WhatsApp' }));
    expect(within(dialog).queryByLabelText(/Al aceptar/, { selector: 'textarea' })).not.toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a1')).toBeDefined());
    // Se manda lo que ya tenía el área, no lo inválido; los mensajes guardados siguen.
    expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a1')).toMatchObject({
      delivery: 'whatsapp',
      ring_seconds: 20,
      return_digits: '2',
      messages: { operator_ack: 'Hola {{persona}}', transfer: 'Ya te paso con Ventas.' },
    });
  });

  it('lo oculto que está bien se guarda, y al volver a "Se llama" lo escrito sigue', async () => {
    const { calls, dialog, ack } = await openRotacion({
      'PATCH /api/v1/handoff-areas/a1': () => jsonResponse(ROTACION),
    });
    await userEvent.clear(ack);
    await userEvent.type(ack, 'Recibido {{{{area}}');
    await userEvent.click(within(dialog).getByRole('radio', { name: 'Solo aviso por WhatsApp' }));
    await userEvent.click(within(dialog).getByRole('radio', { name: 'Se llama' }));
    expect(await within(dialog).findByLabelText(/Al aceptar/, { selector: 'textarea' })).toHaveValue(
      'Recibido {{area}}',
    );
    await userEvent.click(within(dialog).getByRole('radio', { name: 'Solo aviso por WhatsApp' }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a1')).toBeDefined());
    expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a1')).toMatchObject({
      messages: { operator_ack: 'Recibido {{area}}' },
    });
  });

  it('un área que llama sigue validando el timbre y la tecla', async () => {
    const { calls, dialog } = await openRotacion();
    const ring = within(dialog).getByLabelText(/Timbre por persona/);
    await userEvent.clear(ring);
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    expect(await within(dialog).findByText('Entre 5 y 60 segundos')).toBeInTheDocument();
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false);
  });

  it('el error del horario lleva el scroll al campo', async () => {
    const calls = mockApi();
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar el área Ventas' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar área Ventas' });
    await userEvent.click(within(dialog).getByRole('button', { name: 'Quitar franja 1 del lunes' }));
    const scroll = vi.spyOn(window.HTMLElement.prototype, 'scrollIntoView');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    const error = await within(dialog).findByText(/Cargá al menos una franja/);
    await waitFor(() => expect(scroll.mock.instances[0]).toBe(error));
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false);
    scroll.mockRestore();
  });
});
