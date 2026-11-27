import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { HandoffArea, TeamMember } from '@/api/types';
import { CATALOG } from '@/components/variables/fixtures';
import { ADMIN, CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { AreaModal } from './AreaModal';
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
const BASE: HandoffArea = {
  id: 'a1',
  client_id: 'c-1',
  name: 'Ventas',
  description: '',
  active: true,
  member_ids: ['m1'],
  strategy: 'sequential',
  ring_seconds: 20,
  schedule: null,
  schedule_text: 'todos los días a toda hora',
  open_now: true,
  fallback: 'take_message',
  on_person_hangup: 'resume',
  return_digits: '2',
  messages: { transfer: 'Ya te paso con Ventas.', goodbye: 'Chau de Ventas.' },
  after_hours_area_id: null,
  no_answer_area_id: null,
  no_answer_member_id: null,
  delivery: 'call',
  connect_on_answer: false,
  whatsapp: null,
  used_by: { agents: [], phone_numbers: [], whatsapp_accounts: [] },
  created_at: '2026-10-20T12:00:00Z',
};
const VENTAS = BASE;
const SOPORTE: HandoffArea = {
  ...BASE,
  id: 'a2',
  name: 'Soporte',
  messages: { transfer: 'Soporte te atiende.' },
};
const VACIA: HandoffArea = { ...BASE, id: 'a3', name: 'Vacía', messages: {} };
const AJENA: HandoffArea = {
  ...BASE,
  id: 'a4',
  client_id: 'c-2',
  name: 'Ajena',
  messages: { transfer: 'Ajena.' },
};
const AREAS = [VENTAS, SOPORTE, VACIA, AJENA];

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
    'GET /api/v1/team': () => jsonResponse([ANA]),
    'GET /api/v1/handoff-areas': () => jsonResponse(AREAS),
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

async function openArea(name: string) {
  await userEvent.click(await screen.findByRole('button', { name: `Editar el área ${name}` }));
  return screen.findByRole('dialog', { name: `Editar área ${name}` });
}

const LABEL = 'Copiar mensajes de otra área';

async function listbox(dialog: HTMLElement) {
  await userEvent.click(within(dialog).getByRole('textbox', { name: LABEL }));
  return screen.getByRole('listbox', { name: LABEL, hidden: true });
}

async function pick(dialog: HTMLElement, area: string) {
  const list = await listbox(dialog);
  await userEvent.click(await within(list).findByRole('option', { name: area, hidden: true }));
}

describe('copiar mensajes de otra área', () => {
  it('ofrece solo áreas del mismo cliente con mensajes, sin la propia', async () => {
    mockApi();
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    const dialog = await openArea('Vacía');
    const list = await listbox(dialog);
    const names = within(list)
      .getAllByRole('option', { hidden: true })
      .map((o) => o.textContent);
    expect(names).toEqual(['Ventas', 'Soporte']);
  });

  it('copia a un área sin textos propios, sin llamar a la API, y el PATCH los lleva', async () => {
    const calls = mockApi({ 'PATCH /api/v1/handoff-areas/a3': () => jsonResponse(VACIA) });
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    const dialog = await openArea('Vacía');
    await pick(dialog, 'Ventas');
    expect(within(dialog).getByLabelText('Antes de transferir')).toHaveValue('Ya te paso con Ventas.');
    expect(calls.some((c) => c.method !== 'GET')).toBe(false);
    await userEvent.click(within(dialog).getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a3')).toBeDefined());
    expect(sent(calls, 'PATCH', '/api/v1/handoff-areas/a3')).toMatchObject({
      messages: { transfer: 'Ya te paso con Ventas.', goodbye: 'Chau de Ventas.' },
    });
  });

  it('con textos propios pide confirmación: cancelar no cambia nada y confirmar reemplaza', async () => {
    mockApi();
    renderWithProviders(<TeamPage />, { me: CLIENT_USER });
    const dialog = await openArea('Ventas');
    await pick(dialog, 'Soporte');
    const confirm = await screen.findByRole('dialog', { name: 'Copiar mensajes' });
    await userEvent.click(within(confirm).getByRole('button', { name: 'Cancelar' }));
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Reemplazar' })).not.toBeInTheDocument());
    expect(within(dialog).getByLabelText('Antes de transferir')).toHaveValue('Ya te paso con Ventas.');
    await pick(dialog, 'Soporte');
    await userEvent.click(await screen.findByRole('button', { name: 'Reemplazar' }));
    await waitFor(() =>
      expect(within(dialog).getByLabelText('Antes de transferir')).toHaveValue('Soporte te atiende.'),
    );
    // Lo que el origen no tiene queda vacío: el área queda igual a la de origen.
    expect(within(dialog).queryByLabelText('Despedida')).not.toBeInTheDocument();
  });

  it('un área nueva sin cliente fijo no ofrece copiar: no hay de qué cliente', async () => {
    mockApi();
    renderWithProviders(<AreaModal area={null} members={[]} areas={AREAS} onClose={() => {}} />, {
      me: ADMIN,
    });
    await screen.findByRole('dialog');
    await screen.findByText('Antes de transferir');
    expect(screen.queryByRole('textbox', { name: LABEL })).not.toBeInTheDocument();
  });
});
