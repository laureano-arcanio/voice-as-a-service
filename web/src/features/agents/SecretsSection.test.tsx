import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AgentSecret, ClientSecret, ClientTool } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { type Draft, fromDraft, toDraft } from './draft';
import { neededSecrets } from './grants';
import { SecretsSection } from './SecretsSection';
import { ClientToolsEditor } from './ToolsSection';

const OWN: AgentSecret = {
  name: 'OWN_KEY',
  description: 'Key de este agente',
  last4: 'ab12',
  used_by: [],
  missing: false,
  source: 'agent',
  overrides: false,
  created_at: '2026-10-26T10:00:00Z',
  updated_at: '2026-10-26T10:00:00Z',
};

const CLIENT_SECRET: ClientSecret = {
  name: 'CRM_TOKEN',
  description: 'Token del CRM',
  last4: 'cd34',
  missing: false,
  used_by: ['consultar_turnos'],
  credentials: [],
  agents: [],
  created_at: '2026-10-26T10:00:00Z',
  updated_at: '2026-10-26T10:00:00Z',
};

const tool = (slug: string, secrets: string[], type: ClientTool['type'] = 'http'): ClientTool => ({
  id: slug,
  slug,
  type,
  definition: { description: `Hace ${slug}.` },
  revision: 1,
  secrets,
  llm_tool: null,
  used_by: [],
  last_test_at: null,
  last_test_ok: null,
  last_test_detail: '',
  created_at: '2026-10-26T10:00:00Z',
  updated_at: '2026-10-26T10:00:00Z',
});

const DEF = {
  id: 'a',
  version: 1,
  agent: { name: 'S', role: 'r', language: 'es-AR' },
  objective: { description: 'x' },
  conversation: { opening: 'Hola', rules: [] },
  knowledge: '',
  fields: {},
  completion: {
    when: 'all_required_fields_completed',
    outcomes: [{ id: 'ok', label: 'ok', when: {}, message: 'm', goal: true }],
  },
};

const posts: { path: string; body: unknown }[] = [];

function mockApi(tools: ClientTool[] = []) {
  posts.length = 0;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const path = new URL(req.url).pathname;
      if (req.method === 'POST') {
        const body: unknown = await req.json();
        posts.push({ path, body });
        return jsonResponse({ ...CLIENT_SECRET, ...(body as object), last4: '9999', used_by: [] }, 201);
      }
      if (path === '/api/v1/agents/a-1/secrets') return jsonResponse([OWN]);
      if (path === '/api/v1/clients/c-1/secrets') return jsonResponse([CLIENT_SECRET]);
      if (path === '/api/v1/clients/c-1/tools') return jsonResponse(tools);
      if (path === '/api/v1/plan/features')
        return jsonResponse({ client_id: 'c-1', tier_name: 'Sucursal', free: false, features: {} });
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('SecretsSection', () => {
  it('muestra los del cliente y los propios sin valor, marca los que faltan y los carga en el cliente', async () => {
    mockApi();
    const needed = new Map([
      ['CRM_TOKEN', ['consultar_turnos']],
      ['AGENDA_KEY', ['reservar']],
    ]);
    renderWithProviders(<SecretsSection clientId="c-1" agentId="a-1" needed={needed} />, { me: CLIENT_USER });
    const own = (await screen.findByText('OWN_KEY')).closest('tr')!;
    expect(within(own).getByText('••••ab12')).toBeInTheDocument();
    expect(within(own).getByRole('button', { name: 'Reemplazar valor' })).toBeInTheDocument();
    const inherited = (await screen.findByText('CRM_TOKEN')).closest('tr')!;
    expect(within(inherited).getByText('Del cliente')).toBeInTheDocument();
    expect(within(inherited).getByRole('button', { name: 'Usar otro valor acá' })).toBeInTheDocument();

    const missing = screen.getByText('AGENDA_KEY').closest('tr')!;
    expect(within(missing).getByText('Falta')).toBeInTheDocument();
    expect(within(missing).getByText('reservar')).toBeInTheDocument();
    await userEvent.click(within(missing).getByRole('button', { name: 'Cargar valor' }));
    await userEvent.type(await screen.findByLabelText(/^Valor/), 's3cr3t-valor');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar secreto' }));
    await waitFor(() =>
      expect(posts).toEqual([
        {
          path: '/api/v1/clients/c-1/secrets',
          body: { name: 'AGENDA_KEY', value: 's3cr3t-valor', description: '' },
        },
      ]),
    );
  });
});

describe('ClientToolsEditor', () => {
  let last: Draft = toDraft(DEF);
  function Harness() {
    const [draft, setDraft] = useState(() => toDraft(DEF));
    return (
      <ClientToolsEditor
        draft={draft}
        update={(fn) =>
          setDraft((d) => {
            last = fn(d);
            return last;
          })
        }
        clientId="c-1"
      />
    );
  }

  it('elige herramientas del cliente y pide los secretos que usan', async () => {
    const tools = [tool('consultar_turnos', ['CRM_TOKEN']), tool('deuda', ['AGENDA_KEY'], 'code')];
    mockApi(tools);
    renderWithProviders(<Harness />, { me: CLIENT_USER });
    await userEvent.click(await screen.findByRole('textbox', { name: 'Herramientas' }));
    await userEvent.click(await screen.findByRole('option', { name: 'deuda · Código', hidden: true }));
    await waitFor(() => expect(last.clientTools.map((g) => g.tool)).toEqual(['deuda']));
    expect(fromDraft(last).tools).toEqual([{ tool: 'deuda' }]);
    expect(neededSecrets(last, tools)).toEqual(new Map([['AGENDA_KEY', ['deuda']]]));
  });
});
