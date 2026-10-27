import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AgentSecret, ClientTool } from '@/api/types';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { type Draft, fromDraft, toDraft } from './draft';
import { neededSecrets } from './grants';
import { SecretsSection } from './SecretsSection';
import { ClientToolsEditor } from './ToolsSection';

const SECRET: AgentSecret = {
  name: 'CRM_TOKEN',
  description: 'Token del CRM',
  last4: 'ab12',
  used_by: ['consultar_turnos'],
  missing: false,
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
        return jsonResponse({ ...SECRET, ...(body as object), last4: '9999', used_by: [] }, 201);
      }
      if (path === '/api/v1/agents/a-1/secrets') return jsonResponse([SECRET]);
      if (path === '/api/v1/clients/c-1/tools') return jsonResponse(tools);
      if (path === '/api/v1/plan/features')
        return jsonResponse({ client_id: 'c-1', tier_name: 'Sucursal', free: false, features: {} });
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('SecretsSection', () => {
  it('muestra los cargados sin valor, marca los que faltan y carga uno', async () => {
    mockApi();
    renderWithProviders(<SecretsSection agentId="a-1" needed={new Map([['AGENDA_KEY', ['reservar']]])} />, {
      me: CLIENT_USER,
    });
    const loaded = (await screen.findByText('CRM_TOKEN')).closest('tr')!;
    expect(within(loaded).getByText('••••ab12')).toBeInTheDocument();
    expect(within(loaded).getByRole('button', { name: 'Reemplazar valor' })).toBeInTheDocument();

    const missing = screen.getByText('AGENDA_KEY').closest('tr')!;
    expect(within(missing).getByText('Falta')).toBeInTheDocument();
    expect(within(missing).getByText('reservar')).toBeInTheDocument();
    await userEvent.click(within(missing).getByRole('button', { name: 'Cargar valor' }));
    await userEvent.type(await screen.findByLabelText(/^Valor/), 's3cr3t-valor');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar secreto' }));
    await waitFor(() =>
      expect(posts).toEqual([
        {
          path: '/api/v1/agents/a-1/secrets',
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
