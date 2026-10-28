import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { notifications } from '@mantine/notifications';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Contact } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { ContactDetailPage } from './ContactDetailPage';
import { ContactsPage } from './ContactsPage';
import { parseRows, previewCsv } from './csv';
import { attributesText, parseAttribute } from './labels';

const ANA: Contact = {
  id: 'k1',
  client_id: 'c-1',
  phone: '+5493515551234',
  name: 'Ana Pérez',
  email: 'ana@acme.com',
  external_id: 'A-1',
  attributes: { deuda: 15000 },
  tags: ['mora', 'vip'],
  source: 'csv',
  archived_at: null,
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
};
const LUIS: Contact = {
  ...ANA,
  id: 'k2',
  phone: '+5493515550002',
  name: null,
  email: null,
  external_id: null,
  attributes: {},
  tags: [],
  archived_at: '2026-10-10T12:00:00Z',
};

const PLAN = {
  client_id: 'c-1',
  tier_name: 'Pro',
  channels: ['voice'],
  followup: false,
  max_campaigns_per_month: null,
  campaigns_started: 0,
  max_campaign_contacts: null,
  max_campaign_concurrency: null,
  max_contacts: 100,
  contacts_active: 40,
};

interface Seen {
  method: string;
  path: string;
  search: string;
  body?: unknown;
}

function mockApi(routes: Record<string, () => Response>) {
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

const page = (items: Contact[]) => ({ items, total: items.length });

const routes = (items: Contact[] = [ANA, LUIS]) => ({
  'GET /api/v1/contacts': () => jsonResponse(page(items)),
  'GET /api/v1/campaigns/plan': () => jsonResponse(PLAN),
  'POST /api/v1/contacts/k1/archive': () => jsonResponse({ ...ANA, archived_at: '2026-10-19T12:00:00Z' }),
  'POST /api/v1/contacts/k2/unarchive': () => jsonResponse({ ...LUIS, archived_at: null }),
  'POST /api/v1/contacts/archive': () => jsonResponse({ archived: 2 }),
  'GET /api/v1/clients': () => jsonResponse([{ id: 'c-1', name: 'Acme' }]),
});

afterEach(() => vi.unstubAllGlobals());

describe('contactos: CSV', () => {
  it('entiende las columnas como la API', () => {
    const p = previewCsv('Teléfono;Nombre;Deuda ($);Etiquetas\n351 555-1234;Ana;15000;mora|vip\n');
    expect(p?.error).toBeNull();
    expect(p?.columns.map((c) => c.role)).toEqual(['phone', 'name', 'attribute', 'tags']);
    expect(p?.rows).toEqual([['351 555-1234', 'Ana', '15000', 'mora|vip']]);
    expect(previewCsv('nombre,deuda\nAna,1')?.error).toMatch(/Falta la columna del teléfono/);
    expect(previewCsv('')).toBeNull();
  });

  it('lee comillas, separadores y saltos de línea', () => {
    expect(parseRows('a,b\n"x, y","z ""q"""\r\n\r\n1,2')).toEqual([
      ['a', 'b'],
      ['x, y', 'z "q"'],
      ['1', '2'],
    ]);
  });

  it('atributos: números como números y texto de resumen', () => {
    expect(parseAttribute(' 15000 ')).toBe(15000);
    expect(parseAttribute('2026-11-01')).toBe('2026-11-01');
    expect(attributesText({ deuda: 15000, vence: '2026-11-01' })).toBe('deuda: 15000 · vence: 2026-11-01');
  });
});

describe('contactos: lista', () => {
  it('cliente: tabla con etiquetas, archivados marcados y uso del plan', async () => {
    mockApi(routes());
    renderWithProviders(<ContactsPage />, { me: CLIENT_USER });
    expect(await screen.findByRole('link', { name: '+5493515551234' })).toHaveAttribute(
      'href',
      '/contacts/k1',
    );
    const row = screen.getByRole('row', { name: /5493515551234/ });
    expect(within(row).getByText('mora')).toBeInTheDocument();
    expect(screen.getByText('deuda: 15000')).toBeInTheDocument();
    expect(screen.getByText('Archivado')).toBeInTheDocument();
    expect(await screen.findByText('40 de 100 contactos activos en tu plan.')).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Cliente' })).not.toBeInTheDocument();
  });

  it('busca y filtra por estado y por etiqueta', async () => {
    const calls = mockApi(routes());
    renderWithProviders(<ContactsPage />, { me: CLIENT_USER });
    await screen.findByRole('link', { name: '+5493515551234' });
    await userEvent.type(screen.getByLabelText('Buscar'), 'ana');
    await waitFor(() => expect(calls.some((c) => c.search.includes('q=ana'))).toBe(true));
    await userEvent.click(screen.getByRole('radio', { name: 'Archivados', hidden: true }));
    await waitFor(() => expect(calls.some((c) => c.search.includes('archived=true'))).toBe(true));
  });

  it('archiva uno con confirmación, sin borrar', async () => {
    const calls = mockApi(routes());
    renderWithProviders(<ContactsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Archivar Ana Pérez' }));
    const dialog = await screen.findByRole('dialog', { name: /Archivar a Ana Pérez/ });
    expect(within(dialog).getByText(/No se borra/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Archivar' }));
    await waitFor(() => expect(calls.some((c) => c.path === '/api/v1/contacts/k1/archive')).toBe(true));
    expect(screen.queryByRole('button', { name: /Borrar/ })).not.toBeInTheDocument();
  });

  it('desarchiva un archivado sin pedir confirmación', async () => {
    const calls = mockApi(routes());
    renderWithProviders(<ContactsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: 'Desarchivar +5493515550002' }));
    await waitFor(() => expect(calls.some((c) => c.path === '/api/v1/contacts/k2/unarchive')).toBe(true));
  });

  it('en lote: archiva los elegidos y desarchiva de a uno', async () => {
    const calls = mockApi(routes());
    renderWithProviders(<ContactsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('checkbox', { name: 'Seleccionar todos' }));
    expect(screen.getByText('2 seleccionados')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Archivar' }));
    const dialog = await screen.findByRole('dialog', { name: /Archivar 2 contactos/ });
    await userEvent.click(within(dialog).getByRole('button', { name: 'Archivar' }));
    await waitFor(() => expect(calls.some((c) => c.path === '/api/v1/contacts/archive')).toBe(true));
    expect(calls.find((c) => c.path === '/api/v1/contacts/archive')?.body).toEqual({
      contact_ids: ['k1', 'k2'],
    });

    await userEvent.click(await screen.findByRole('checkbox', { name: 'Seleccionar todos' }));
    await userEvent.click(screen.getByRole('button', { name: 'Desarchivar' }));
    await waitFor(() => expect(calls.filter((c) => c.path.endsWith('/unarchive')).length).toBe(2));
  });

  it('vacío: explica cómo se llena', async () => {
    mockApi(routes([]));
    renderWithProviders(<ContactsPage />, { me: CLIENT_USER });
    expect(await screen.findByText(/Todavía no hay contactos/)).toBeInTheDocument();
  });
});

describe('contactos: alta e importación', () => {
  it('crea uno con datos', async () => {
    const calls = mockApi({
      ...routes(),
      'POST /api/v1/contacts': () =>
        jsonResponse({ created: 1, updated: 0, archived: 0, invalid: [], contacts: [ANA] }, 201),
    });
    renderWithProviders(<ContactsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Nuevo contacto/ }));
    await userEvent.type(await screen.findByLabelText('Teléfono'), '351 555-1234');
    await userEvent.type(screen.getByLabelText('Nombre'), 'Ana');
    await userEvent.click(screen.getByRole('button', { name: 'Agregar dato' }));
    await userEvent.type(screen.getByLabelText('Nombre del dato 1'), 'deuda');
    await userEvent.type(screen.getByLabelText('Valor del dato 1'), '15000');
    await userEvent.click(screen.getByRole('button', { name: 'Agregar contacto' }));
    await waitFor(() =>
      expect(calls.some((c) => c.method === 'POST' && c.path === '/api/v1/contacts')).toBe(true),
    );
    // Un objeto solo, no una lista: así un rechazo vuelve como error y no como "ya existía".
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      phone: '351 555-1234',
      name: 'Ana',
      email: null,
      external_id: null,
      tags: [],
      attributes: { deuda: 15000 },
    });
  });

  it('muestra el motivo si el alta se rechaza', async () => {
    const show = vi.spyOn(notifications, 'show');
    mockApi({
      ...routes(),
      'POST /api/v1/contacts': () =>
        jsonResponse({ detail: 'Contacto inválido: email inválido', code: 'invalid' }, 400),
    });
    renderWithProviders(<ContactsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Nuevo contacto/ }));
    await userEvent.type(await screen.findByLabelText('Teléfono'), '351 555-1234');
    await userEvent.type(screen.getByLabelText('Email'), 'laureano');
    await userEvent.click(screen.getByRole('button', { name: 'Agregar contacto' }));
    await waitFor(() =>
      expect(show).toHaveBeenCalledWith(
        expect.objectContaining({ color: 'red', message: expect.stringMatching(/email inválido/) }),
      ),
    );
    expect(show).not.toHaveBeenCalledWith(
      expect.objectContaining({ message: expect.stringMatching(/ya estaba en la agenda/) }),
    );
  });

  it('importa un CSV con vista previa y muestra creados, archivados e inválidos', async () => {
    const calls = mockApi({
      ...routes(),
      'POST /api/v1/contacts/import': () =>
        jsonResponse({
          created: 1,
          updated: 1,
          archived: 1,
          invalid: [{ phone: '555', reason: 'teléfono inválido', line: 4 }],
          contacts: [],
        }),
    });
    renderWithProviders(<ContactsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Importar CSV/ }));
    const csv = 'telefono,nombre,deuda\n351 555-1234,Ana,15000\n351 555-0002,Luis,0';
    await userEvent.click(await screen.findByLabelText('Contactos (CSV)'));
    await userEvent.paste(csv);
    expect(await screen.findByText(/para cargar/)).toBeInTheDocument();
    expect(screen.getByText('2', { selector: 'b' })).toBeInTheDocument();
    expect(screen.getAllByText('Dato').length).toBe(1);
    await userEvent.click(screen.getByRole('button', { name: 'Importar' }));
    expect(await screen.findByText(/ya estaba archivado/)).toBeInTheDocument();
    expect(screen.getByText('teléfono inválido')).toBeInTheDocument();
    expect(calls.find((c) => c.path === '/api/v1/contacts/import')?.body).toEqual({ csv, tags: [] });
  });

  it('un CSV sin teléfono no se puede importar', async () => {
    mockApi(routes());
    renderWithProviders(<ContactsPage />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('button', { name: /Importar CSV/ }));
    await userEvent.click(await screen.findByLabelText('Contactos (CSV)'));
    await userEvent.paste('nombre,deuda\nAna,1');
    expect(await screen.findByText(/Falta la columna del teléfono/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Importar' })).toBeDisabled();
  });
});

describe('contactos: ficha', () => {
  it('muestra los datos y las campañas del contacto', async () => {
    mockApi({
      'GET /api/v1/contacts/k1': () => jsonResponse(ANA),
      'GET /api/v1/contacts/k1/campaigns': () =>
        jsonResponse([
          {
            campaign_id: 'cmp-1',
            campaign_name: 'Mora octubre',
            channel: 'voice',
            campaign_status: 'running',
            status: 'done',
            result: 'answered',
            attempts: 2,
            last_attempt_at: '2026-10-19T13:00:00Z',
            sent_at: null,
            conversation_id: 'conv-1',
          },
        ]),
    });
    renderWithProviders(<ContactDetailPage />, {
      me: CLIENT_USER,
      path: '/contacts/k1',
      routes: [{ path: '/contacts/:id', element: <ContactDetailPage /> }],
    });
    expect(await screen.findByText('Ana Pérez')).toBeInTheDocument();
    expect(screen.getByText('15000')).toBeInTheDocument();
    expect(screen.getByText('ana@acme.com')).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'Mora octubre' })).toHaveAttribute(
      'href',
      '/campaigns/cmp-1',
    );
    expect(screen.getByText('Atendió')).toBeInTheDocument();
    expect(screen.getByText('Llamadas')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ver conversación' })).toHaveAttribute('href', '/calls/conv-1');
    expect(screen.getByRole('button', { name: 'Archivar' })).toBeInTheDocument();
  });

  it('un contacto de otro cliente da no encontrado', async () => {
    mockApi({ 'GET /api/v1/contacts/zz': () => jsonResponse({ detail: 'Contacto inexistente' }, 404) });
    renderWithProviders(<ContactDetailPage />, {
      me: CLIENT_USER,
      path: '/contacts/zz',
      routes: [{ path: '/contacts/:id', element: <ContactDetailPage /> }],
    });
    expect(await screen.findByText('El contacto no existe o no tenés acceso.')).toBeInTheDocument();
  });
});
