import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/api/errors';
import type { PhoneNumber, TeamMember } from '@/api/types';
import { NumbersSection } from '@/features/clients/NumbersSection';
import { toDraft } from '@/features/team/schedule';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { toAnsweringBody, toAnsweringDraft } from './answering';
import { answeringErrorField } from './errors';

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
const LUIS: TeamMember = { ...ANA, id: 'm2', name: 'Luis Gómez', phone: null, user_id: 'u-2' };

const base = {
  provider: 'anura',
  client_id: 'c-1',
  client_name: 'Acme',
  assigned_at: '2026-10-01T12:00:00Z',
  created_at: '2026-10-01T12:00:00Z',
  strategy: 'sequential',
  ring_first: 'phone',
  ring_seconds: 20,
  team_connect_on_answer: false,
  team_hold_music: true,
  team_retry_seconds: 0,
  team_retry_interval_seconds: 30,
  team_retry_message: '',
  record_full_call: false,
  schedule: null,
  team_fallback: 'voicemail',
  team_fallback_message: '',
} as const;

const TEAM_NUMBER = {
  ...base,
  id: 'n1',
  e164: '+541155550001',
  label: 'Ventas',
  agent_id: null,
  agent_name: null,
  answer_mode: 'team',
  ring_first: 'panel',
  members: [
    { id: 'm1', name: 'Ana Pérez', phone: ANA.phone, user_id: 'u-1' },
    { id: 'm2', name: 'Luis Gómez', phone: null, user_id: 'u-2' },
  ],
} as PhoneNumber;
const EMPTY_NUMBER = {
  ...base,
  id: 'n2',
  e164: '+541155550002',
  label: 'Soporte',
  agent_id: null,
  agent_name: null,
  answer_mode: 'team',
  members: [],
} as PhoneNumber;
const EMPTY_WITH_AGENT = {
  ...EMPTY_NUMBER,
  id: 'n3',
  e164: '+541155550003',
  label: 'Cobranzas',
  agent_id: 'ag1',
  agent_name: 'Comercial',
} as PhoneNumber;
const AGENT_NUMBER = {
  ...base,
  id: 'n4',
  e164: '+541155550004',
  label: 'Landing',
  agent_id: 'ag1',
  agent_name: 'Comercial',
  answer_mode: 'agent',
  members: [],
} as PhoneNumber;

const AGENTS = [
  { id: 'ag1', name: 'Comercial' },
  { id: 'ag2', name: 'Soporte' },
];

const PLAN = (direct: boolean) => ({
  client_id: 'c-1',
  tier_name: direct ? 'Sucursal' : 'Free',
  free: !direct,
  features: {
    direct_calls: {
      enabled: direct,
      reason: direct ? null : 'Está en los planes Mostrador, Sucursal y Red.',
    },
  },
});

interface Seen {
  method: string;
  path: string;
  body?: unknown;
}

function mockApi(numbers: PhoneNumber[], extra: Record<string, () => Response> = {}, direct = true) {
  const routes: Record<string, () => Response> = {
    'GET /api/v1/phone-numbers': () => jsonResponse(numbers),
    'GET /api/v1/agents': () => jsonResponse(AGENTS),
    'GET /api/v1/team': () => jsonResponse([ANA, LUIS]),
    'GET /api/v1/plan/features': () => jsonResponse(PLAN(direct)),
    'PATCH /api/v1/phone-numbers/n2': () => jsonResponse(EMPTY_NUMBER),
    'PATCH /api/v1/phone-numbers/n4': () => jsonResponse(AGENT_NUMBER),
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
      calls.push({ method: req.method, path: url.pathname, body });
      const route = routes[`${req.method} ${url.pathname}`];
      return route ? route() : jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
  return calls;
}

const patched = (calls: Seen[], id: string) =>
  calls.find((c) => c.method === 'PATCH' && c.path === `/api/v1/phone-numbers/${id}`)?.body;

async function openEdit(e164: string) {
  await userEvent.click(await screen.findByRole('button', { name: `Editar ${e164}` }));
  return screen.findByRole('dialog', { name: `Editar ${e164}` });
}

afterEach(() => vi.unstubAllGlobals());

describe('números: quién atiende', () => {
  it('lista el equipo con sus personas, el equipo sin personas y el agente', async () => {
    mockApi([TEAM_NUMBER, EMPTY_NUMBER, EMPTY_WITH_AGENT, AGENT_NUMBER]);
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });

    const team = await screen.findByRole('row', { name: /\+541155550001/ });
    expect(within(team).getByText('Equipo')).toBeInTheDocument();
    expect(within(team).getByText('Ana Pérez, Luis Gómez')).toBeInTheDocument();
    expect(within(team).getByText('Suena primero en el panel')).toBeInTheDocument();

    const empty = screen.getByRole('row', { name: /\+541155550002/ });
    expect(within(empty).getByText('Equipo sin personas')).toBeInTheDocument();
    expect(within(empty).getByText('Sin personas: no atiende nadie')).toBeInTheDocument();

    const fallback = screen.getByRole('row', { name: /\+541155550003/ });
    expect(within(fallback).getByText('Sin personas: atiende el agente Comercial')).toBeInTheDocument();

    const agent = screen.getByRole('row', { name: /\+541155550004/ });
    await waitFor(() =>
      expect(within(agent).getByRole('textbox', { name: /Agente de/ })).toHaveValue('Comercial'),
    );
  });

  it('la fila dice "rotativa" solo si el número rota', async () => {
    mockApi([
      TEAM_NUMBER,
      {
        ...EMPTY_WITH_AGENT,
        id: 'n7',
        e164: '+541155550007',
        members: TEAM_NUMBER.members,
        strategy: 'round_robin',
      } as PhoneNumber,
    ]);
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    const plain = await screen.findByRole('row', { name: /\+541155550001/ });
    expect(within(plain).getByText('Suena primero en el panel')).toBeInTheDocument();
    const rotating = screen.getByRole('row', { name: /\+541155550007/ });
    expect(within(rotating).getByText(/Suena primero en su teléfono · rotativa/)).toBeInTheDocument();
  });

  it('pasa un número sin personas al equipo: personas en orden, panel primero, timbre y respaldo al agente', async () => {
    const calls = mockApi([EMPTY_NUMBER]);
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    const dialog = await openEdit('+541155550002');
    expect(within(dialog).getByRole('radio', { name: /El equipo/ })).toBeChecked();

    // Sin personas no se puede guardar.
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    expect(await within(dialog).findByText('Elegí al menos una persona')).toBeInTheDocument();
    expect(patched(calls, 'n2')).toBeUndefined();

    const add = within(dialog).getByRole('textbox', { name: 'Agregar persona al número' });
    await userEvent.click(add);
    await userEvent.click(await screen.findByRole('option', { name: 'Ana Pérez', hidden: true }));
    await userEvent.click(within(dialog).getByRole('textbox', { name: 'Agregar persona al número' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Luis Gómez', hidden: true }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Subir a Luis Gómez' }));
    expect(within(dialog).getByText('Solo en el panel')).toBeInTheDocument();
    expect(within(dialog).getByText('Solo en el teléfono')).toBeInTheDocument();

    await userEvent.click(within(dialog).getByText('En el panel'));
    expect(within(dialog).getByText(/Siempre empieza por la primera persona/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByText('Rotativa'));
    expect(within(dialog).getByText(/En el panel suena a todas a la vez y no rota/)).toBeInTheDocument();
    const ring = within(dialog).getByLabelText(/Timbre por persona/);
    await userEvent.clear(ring);
    await userEvent.type(ring, '30');

    await userEvent.click(within(dialog).getByRole('textbox', { name: 'Si nadie atiende' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Pasa al agente', hidden: true }));
    // El respaldo al agente pide el agente.
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    expect(
      await within(dialog).findByText('Elegí el agente que atiende si nadie del equipo lo hace'),
    ).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('textbox', { name: /Agente de respaldo/ }));
    await userEvent.click(await screen.findByRole('option', { name: 'Comercial', hidden: true }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(patched(calls, 'n2')).toBeDefined());
    expect(patched(calls, 'n2')).toEqual({
      label: 'Soporte',
      answer_mode: 'team',
      agent_id: 'ag1',
      record_full_call: false,
      member_ids: ['m2', 'm1'],
      strategy: 'round_robin',
      ring_first: 'panel',
      ring_seconds: 30,
      team_connect_on_answer: false,
      team_hold_music: true,
      team_retry_seconds: 0,
      team_retry_interval_seconds: 30,
      team_retry_message: '',
      schedule: null,
      team_fallback: 'agent',
      team_fallback_member_id: null,
      team_fallback_message: '',
    });
  });

  it('los switches de la espera cargan lo guardado, se guardan y la fila los muestra', async () => {
    const custom = { ...TEAM_NUMBER, team_connect_on_answer: true, team_hold_music: false } as PhoneNumber;
    const calls = mockApi([TEAM_NUMBER, { ...custom, id: 'n8', e164: '+541155550008' } as PhoneNumber], {
      'PATCH /api/v1/phone-numbers/n1': () => jsonResponse(custom),
    });
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });

    const plain = await screen.findByRole('row', { name: /\+541155550001/ });
    expect(within(plain).queryByText(/conecta al atender/)).not.toBeInTheDocument();
    expect(within(plain).queryByText(/sin música/)).not.toBeInTheDocument();
    const marked = screen.getByRole('row', { name: /\+541155550008/ });
    expect(
      within(marked).getByText('Suena primero en el panel · conecta al atender · sin música'),
    ).toBeInTheDocument();

    const dialog = await openEdit('+541155550001');
    const connect = within(dialog).getByRole('switch', { name: /Conectar al atender/ });
    const music = within(dialog).getByRole('switch', { name: /Música mientras suena/ });
    expect(connect).not.toBeChecked();
    expect(music).toBeChecked();
    expect(within(dialog).getByText(/Vale para los teléfonos/)).toBeInTheDocument();
    await userEvent.click(connect);
    await userEvent.click(music);
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(patched(calls, 'n1')).toBeDefined());
    expect(patched(calls, 'n1')).toMatchObject({ team_connect_on_answer: true, team_hold_music: false });
  });

  it('grabar la llamada completa: el switch carga lo guardado, se manda con el agente y con el equipo, y la fila lo dice', async () => {
    const recording = { ...AGENT_NUMBER, record_full_call: true } as PhoneNumber;
    const calls = mockApi([TEAM_NUMBER, { ...recording, id: 'n9', e164: '+541155550009' } as PhoneNumber], {
      'PATCH /api/v1/phone-numbers/n1': () => jsonResponse({ ...TEAM_NUMBER, record_full_call: true }),
      'PATCH /api/v1/phone-numbers/n9': () => jsonResponse(recording),
    });
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });

    expect(
      within(await screen.findByRole('row', { name: /\+541155550001/ })).queryByText('Graba la llamada completa'),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByRole('row', { name: /\+541155550009/ })).getByText('Graba la llamada completa'),
    ).toBeInTheDocument();

    // Con el equipo: arranca apagado, avisa que es solo por teléfono y se guarda con el resto.
    const team = await openEdit('+541155550001');
    const toggle = within(team).getByRole('switch', { name: /Grabar la llamada completa/ });
    expect(toggle).not.toBeChecked();
    expect(within(team).getByText(/Solo llamadas por teléfono/)).toBeInTheDocument();
    await userEvent.click(toggle);
    await userEvent.click(within(team).getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(patched(calls, 'n1')).toBeDefined());
    expect(patched(calls, 'n1')).toMatchObject({ answer_mode: 'team', record_full_call: true });
  });

  it('grabar la llamada completa: con el agente se apaga y se manda solo con el modo y el agente', async () => {
    const recording = { ...AGENT_NUMBER, record_full_call: true } as PhoneNumber;
    const calls = mockApi([recording], { 'PATCH /api/v1/phone-numbers/n4': () => jsonResponse(AGENT_NUMBER) });
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    const dialog = await openEdit(recording.e164);
    const toggle = within(dialog).getByRole('switch', { name: /Grabar la llamada completa/ });
    expect(toggle).toBeChecked();
    await userEvent.click(toggle);
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(patched(calls, 'n4')).toBeDefined());
    expect(patched(calls, 'n4')).toMatchObject({ answer_mode: 'agent', record_full_call: false });
    expect(patched(calls, 'n4')).not.toHaveProperty('member_ids');
  });

  it('reintentos: elegir duración, intervalo y aviso se guarda y la fila lo dice', async () => {
    const saved = {
      ...TEAM_NUMBER,
      team_retry_seconds: 180,
      team_retry_interval_seconds: 15,
      team_retry_message: 'Espere en línea.',
    } as PhoneNumber;
    const calls = mockApi([TEAM_NUMBER, { ...saved, id: 'n8', e164: '+541155550008' } as PhoneNumber], {
      'PATCH /api/v1/phone-numbers/n1': () => jsonResponse(saved),
    });
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    expect(
      within(await screen.findByRole('row', { name: /\+541155550001/ })).queryByText(/reintenta/),
    ).not.toBeInTheDocument();
    expect(
      within(screen.getByRole('row', { name: /\+541155550008/ })).getByText(
        'Suena primero en el panel · reintenta 3 min cada 15 s',
      ),
    ).toBeInTheDocument();

    const dialog = await openEdit('+541155550001');
    // Sin reintentos no se piden ni el intervalo ni el aviso.
    expect(within(dialog).getByRole('textbox', { name: /Volver a intentar/ })).toHaveValue('No, pasar al respaldo');
    expect(within(dialog).queryByLabelText(/Cada/)).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('Aviso de espera')).not.toBeInTheDocument();
    expect(within(dialog).getByText('Si nadie atiende o es fuera de horario')).toBeInTheDocument();
    expect(within(dialog).getByText('Segundos antes de pasar a la siguiente.')).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole('textbox', { name: /Volver a intentar/ }));
    await userEvent.click(await screen.findByRole('option', { name: 'Durante 3 minutos', hidden: true }));
    expect(within(dialog).getByText('Si sigue sin atender, o fuera de horario')).toBeInTheDocument();
    expect(within(dialog).getByText(/El buzón de un celular atiende a los ~33 s/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('textbox', { name: /Cada/ }));
    await userEvent.click(await screen.findByRole('option', { name: '15 s', hidden: true }));
    const notice = within(dialog).getByLabelText('Aviso de espera');
    expect(notice).toHaveAttribute('placeholder', expect.stringContaining('esperá en línea'));
    await userEvent.type(notice, ' Espere en línea. ');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(patched(calls, 'n1')).toBeDefined());
    expect(patched(calls, 'n1')).toMatchObject({
      team_retry_seconds: 180,
      team_retry_interval_seconds: 15,
      team_retry_message: 'Espere en línea.',
    });
  });

  it('reintentos: elegir "No" esconde el intervalo y el aviso y manda 0', async () => {
    const withRetry = {
      ...TEAM_NUMBER,
      team_retry_seconds: 120,
      team_retry_message: 'Espere.',
    } as PhoneNumber;
    const calls = mockApi([withRetry], {
      'PATCH /api/v1/phone-numbers/n1': () => jsonResponse(TEAM_NUMBER),
    });
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    const dialog = await openEdit('+541155550001');
    expect(within(dialog).getByLabelText('Aviso de espera')).toHaveValue('Espere.');
    await userEvent.click(within(dialog).getByRole('textbox', { name: /Volver a intentar/ }));
    await userEvent.click(await screen.findByRole('option', { name: 'No, pasar al respaldo', hidden: true }));
    expect(within(dialog).queryByLabelText(/Cada/)).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('Aviso de espera')).not.toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(patched(calls, 'n1')).toBeDefined());
    expect(patched(calls, 'n1')).toMatchObject({ team_retry_seconds: 0, team_retry_interval_seconds: 30 });
  });

  it('reintentos: un valor de la API fuera de las opciones (150 s, 45 s) aparece como opción', async () => {
    const odd = {
      ...TEAM_NUMBER,
      team_retry_seconds: 150,
      team_retry_interval_seconds: 45,
    } as PhoneNumber;
    mockApi([odd]);
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    expect(
      within(await screen.findByRole('row', { name: /\+541155550001/ })).getByText(
        'Suena primero en el panel · reintenta 150 s cada 45 s',
      ),
    ).toBeInTheDocument();
    const dialog = await openEdit('+541155550001');
    const duration = within(dialog).getByRole('textbox', { name: /Volver a intentar/ });
    expect(duration).toHaveValue('Durante 150 s');
    await userEvent.click(duration);
    expect(await screen.findByRole('option', { name: 'Durante 150 s', hidden: true })).toBeInTheDocument();
    await userEvent.keyboard('{Escape}');
    const every = within(dialog).getByRole('textbox', { name: /Cada/ });
    expect(every).toHaveValue('45 s');
    await userEvent.click(every);
    expect(await screen.findByRole('option', { name: '45 s', hidden: true })).toBeInTheDocument();
  });

  it('el modal abre con los switches de un número que ya los tiene cambiados', async () => {
    const custom = { ...TEAM_NUMBER, team_connect_on_answer: true, team_hold_music: false } as PhoneNumber;
    mockApi([custom]);
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    const dialog = await openEdit('+541155550001');
    expect(within(dialog).getByRole('switch', { name: /Conectar al atender/ })).toBeChecked();
    expect(within(dialog).getByRole('switch', { name: /Música mientras suena/ })).not.toBeChecked();
  });

  it('si nadie atiende, una persona fuera del número y con teléfono', async () => {
    const onlyLuis = {
      ...TEAM_NUMBER,
      id: 'n8',
      e164: '+541155550008',
      members: [{ id: 'm2', name: 'Luis Gómez', phone: null, user_id: 'u-2' }],
    } as PhoneNumber;
    const calls = mockApi([onlyLuis], {
      'PATCH /api/v1/phone-numbers/n8': () => jsonResponse(onlyLuis),
    });
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    const dialog = await openEdit('+541155550008');
    await userEvent.click(within(dialog).getByRole('textbox', { name: 'Si nadie atiende' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Llama a una persona', hidden: true }));
    expect(within(dialog).queryByLabelText('Mensaje')).not.toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    expect(await within(dialog).findByText('Elegí la persona a la que se llama')).toBeInTheDocument();
    expect(patched(calls, 'n8')).toBeUndefined();
    // Solo Ana: Luis está en el número y no tiene teléfono.
    await userEvent.click(within(dialog).getByRole('textbox', { name: /Persona/ }));
    expect(screen.queryByRole('option', { name: /^Luis Gómez ·/, hidden: true })).not.toBeInTheDocument();
    await userEvent.click(
      await screen.findByRole('option', { name: 'Ana Pérez · +5493515551234', hidden: true }),
    );
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(patched(calls, 'n8')).toBeDefined());
    expect(patched(calls, 'n8')).toMatchObject({
      member_ids: ['m2'],
      team_fallback: 'member',
      team_fallback_member_id: 'm1',
    });
  });

  it('horario opcional y mensaje de respaldo', async () => {
    const calls = mockApi([TEAM_NUMBER], {
      'PATCH /api/v1/phone-numbers/n1': () => jsonResponse(TEAM_NUMBER),
    });
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    const dialog = await openEdit('+541155550001');
    await userEvent.click(within(dialog).getByRole('switch', { name: /Atiende siempre/ }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Quitar franja 1 del viernes' }));
    const message = within(dialog).getByLabelText('Mensaje');
    expect(message).toHaveAttribute('placeholder', expect.stringContaining('Dejá tu mensaje'));
    await userEvent.type(message, 'Volvemos mañana.');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(patched(calls, 'n1')).toBeDefined());
    expect(patched(calls, 'n1')).toMatchObject({
      answer_mode: 'team',
      member_ids: ['m1', 'm2'],
      schedule: {
        tz: 'America/Argentina/Buenos_Aires',
        week: { mon: [['09:00', '18:00']], thu: [['09:00', '18:00']] },
        closed: [],
      },
      team_fallback: 'voicemail',
      team_fallback_message: 'Volvemos mañana.',
    });
  });

  it('pasa al agente: manda el modo y el agente, sin lo del equipo', async () => {
    const calls = mockApi([EMPTY_WITH_AGENT], {
      'PATCH /api/v1/phone-numbers/n3': () => jsonResponse(AGENT_NUMBER),
    });
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    const dialog = await openEdit('+541155550003');
    await userEvent.click(within(dialog).getByRole('radio', { name: /El agente/ }));
    expect(within(dialog).getByRole('textbox', { name: 'Agente que atiende' })).toHaveValue('Comercial');
    expect(within(dialog).queryByText('Suena primero')).not.toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(patched(calls, 'n3')).toBeDefined());
    expect(patched(calls, 'n3')).toEqual({
      label: 'Cobranzas',
      answer_mode: 'agent',
      agent_id: 'ag1',
      record_full_call: false,
    });
  });

  it('el toggle de la fila pasa del agente al equipo si ya tiene personas, y vuelve', async () => {
    const withPeople = {
      ...AGENT_NUMBER,
      id: 'n6',
      e164: '+541155550006',
      members: TEAM_NUMBER.members,
    } as PhoneNumber;
    const calls = mockApi([withPeople, TEAM_NUMBER], {
      'PATCH /api/v1/phone-numbers/n6': () => jsonResponse({ ...withPeople, answer_mode: 'team' }),
      'PATCH /api/v1/phone-numbers/n1': () => jsonResponse({ ...TEAM_NUMBER, answer_mode: 'agent' }),
    });
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });

    const agentRow = await screen.findByRole('row', { name: /\+541155550006/ });
    expect(within(agentRow).getByRole('radio', { name: 'Agente' })).toBeChecked();
    await userEvent.click(within(agentRow).getByRole('radio', { name: 'Equipo' }));
    await waitFor(() => expect(patched(calls, 'n6')).toEqual({ answer_mode: 'team' }));

    const teamRow = screen.getByRole('row', { name: /\+541155550001/ });
    expect(within(teamRow).getByRole('radio', { name: 'Equipo' })).toBeChecked();
    await userEvent.click(within(teamRow).getByRole('radio', { name: 'Agente' }));
    await waitFor(() => expect(patched(calls, 'n1')).toEqual({ answer_mode: 'agent' }));
  });

  it('el toggle pasa a Equipo un número sin personas abriendo el editor, sin tocar la API', async () => {
    const calls = mockApi([AGENT_NUMBER]);
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    const row = await screen.findByRole('row', { name: /\+541155550004/ });
    await userEvent.click(within(row).getByRole('radio', { name: 'Equipo' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar +541155550004' });
    expect(within(dialog).getByRole('radio', { name: /El equipo/ })).toBeChecked();
    expect(patched(calls, 'n4')).toBeUndefined();
  });

  it('sin llamadas directas en el plan el toggle no deja elegir el equipo', async () => {
    mockApi([AGENT_NUMBER], {}, false);
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    const row = await screen.findByRole('row', { name: /\+541155550004/ });
    await waitFor(() => expect(within(row).getByRole('radio', { name: 'Equipo' })).toBeDisabled());
  });

  it('sin llamadas directas en el plan avisa y no deja elegir el equipo', async () => {
    mockApi([AGENT_NUMBER], {}, false);
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    const dialog = await openEdit('+541155550004');
    expect(await within(dialog).findByText(/no incluye que atienda el equipo/)).toBeInTheDocument();
    expect(within(dialog).getByRole('radio', { name: /El equipo/ })).toBeDisabled();
    expect(within(dialog).getByRole('radio', { name: /El agente/ })).toBeChecked();
  });

  it('un 429 del plan se muestra en el campo y no cierra el editor', async () => {
    mockApi([AGENT_NUMBER], {
      'PATCH /api/v1/phone-numbers/n4': () =>
        jsonResponse(
          { detail: 'Tu plan no incluye llamadas directas.', code: 'direct_calls_not_in_plan' },
          429,
        ),
    });
    renderWithProviders(<NumbersSection clientId="c-1" canAssign={false} />, { me: CLIENT_USER });
    const dialog = await openEdit('+541155550004');
    await userEvent.click(within(dialog).getByRole('radio', { name: /El equipo/ }));
    await userEvent.click(within(dialog).getByRole('textbox', { name: 'Agregar persona al número' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Ana Pérez', hidden: true }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    expect(await within(dialog).findByText('Tu plan no incluye llamadas directas.')).toBeInTheDocument();
    expect(screen.getByRole('dialog', { name: 'Editar +541155550004' })).toBeInTheDocument();
  });

  it('un número libre solo edita la etiqueta', async () => {
    const free = { ...EMPTY_NUMBER, client_id: null, client_name: null, id: 'n5', e164: '+541155550005' };
    const calls = mockApi([free as PhoneNumber], {
      'PATCH /api/v1/phone-numbers/n5': () => jsonResponse(free),
    });
    const { EditNumberModal } = await import('./EditNumberModal');
    renderWithProviders(<EditNumberModal number={free as PhoneNumber} onClose={() => undefined} />, {
      me: CLIENT_USER,
    });
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).queryByText('Quién atiende las entrantes')).not.toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(patched(calls, 'n5')).toEqual({ label: 'Soporte' }));
  });
});

describe('números: formulario y errores', () => {
  it('arma el PATCH del equipo y del agente desde el número', () => {
    const draft = toAnsweringDraft(TEAM_NUMBER);
    expect(draft.member_ids).toEqual(['m1', 'm2']);
    expect(draft.strategy).toBe('sequential');
    expect(draft.schedule).toEqual(toDraft(null));
    expect(toAnsweringBody({ ...draft, label: ' Ventas ', team_fallback_message: ' hola ' })).toEqual({
      label: 'Ventas',
      answer_mode: 'team',
      agent_id: null,
      record_full_call: false,
      member_ids: ['m1', 'm2'],
      strategy: 'sequential',
      ring_first: 'panel',
      ring_seconds: 20,
      team_connect_on_answer: false,
      team_hold_music: true,
      team_retry_seconds: 0,
      team_retry_interval_seconds: 30,
      team_retry_message: '',
      schedule: null,
      team_fallback: 'voicemail',
      team_fallback_member_id: null,
      team_fallback_message: 'hola',
    });
    expect(toAnsweringBody({ ...draft, answer_mode: 'agent', agent_id: 'ag2' })).toEqual({
      label: 'Ventas',
      answer_mode: 'agent',
      agent_id: 'ag2',
      record_full_call: false,
    });
  });

  it('cada error de la API cae en su campo', () => {
    const err = (status: number, message: string, code?: string) => new ApiError(status, message, code);
    expect(answeringErrorField(err(422, 'x', 'members_required'))).toBe('member_ids');
    expect(answeringErrorField(err(422, 'x', 'invalid_members'))).toBe('member_ids');
    expect(answeringErrorField(err(422, 'x', 'agent_required'))).toBe('agent_id');
    expect(answeringErrorField(err(422, 'x', 'invalid_fallback_member'))).toBe('team_fallback_member_id');
    expect(answeringErrorField(err(429, 'x', 'direct_calls_not_in_plan'))).toBe('answer_mode');
    expect(answeringErrorField(err(403, 'x', 'terms_pending'))).toBe('answer_mode');
    expect(answeringErrorField(err(422, 'El timbre por persona va de 5 a 60 segundos'))).toBe('ring_seconds');
    expect(answeringErrorField(err(422, 'ring_seconds: Input should be less than or equal to 60'))).toBe(
      'ring_seconds',
    );
    expect(answeringErrorField(err(422, 'Horarios superpuestos el lunes'))).toBe('schedule');
    expect(answeringErrorField(err(422, 'El mensaje va hasta 500 caracteres'))).toBe('team_fallback_message');
    expect(answeringErrorField(err(422, 'team_retry_seconds: de 0 a 300, de a 15'))).toBe('team_retry_seconds');
    expect(answeringErrorField(err(422, 'team_retry_interval_seconds: de 15 a 120'))).toBe(
      'team_retry_interval_seconds',
    );
    expect(answeringErrorField(err(422, 'El mensaje de espera va hasta 500 caracteres'))).toBe(
      'team_retry_message',
    );
    expect(answeringErrorField(err(409, 'otra cosa'))).toBeUndefined();
    expect(answeringErrorField(new Error('red'))).toBeUndefined();
  });
});
