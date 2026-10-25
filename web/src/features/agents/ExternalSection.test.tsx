import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useEffect, useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { LlmConnection } from '@/api/types';
import { ADMIN, CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { type Draft, fromDraft, toDraft } from './draft';
import { ExternalSection } from './ExternalSection';

const conn = (id: string, kind: LlmConnection['kind'], name: string): LlmConnection => ({
  id,
  client_id: 'c-1',
  name,
  kind,
  base_url: 'https://agente.acme.com/v1',
  last4: 'ab12',
  default_model: 'acme-agent',
  json_mode: 'json_schema',
  created_by: null,
  created_at: '2026-10-25T12:00:00Z',
  last_test_at: null,
  last_test_ok: null,
  last_test_detail: '',
  used_by: 0,
});

const DEF = {
  id: 'a',
  version: 1,
  engine: 'classic',
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

const latest = { current: null as unknown as Draft };

function Harness({ initial }: { initial: Draft }) {
  const [draft, setDraft] = useState(initial);
  useEffect(() => {
    latest.current = draft;
  }, [draft]);
  return <ExternalSection draft={draft} update={(fn) => setDraft(fn)} clientId="c-1" />;
}

function mockApi(connections: LlmConnection[], externalInPlan = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const path = new URL(req.url).pathname;
      if (path.endsWith('/llm-connections')) return jsonResponse(connections);
      if (path.endsWith('/handoff-areas')) return jsonResponse([]);
      if (path.endsWith('/plan/features'))
        return jsonResponse({
          client_id: 'c-1',
          tier_name: 'Sucursal',
          free: false,
          features: {
            external_agent: externalInPlan
              ? { enabled: true, reason: null }
              : { enabled: false, reason: 'Disponible en el plan Central.' },
          },
        });
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('ExternalSection', () => {
  it('prenderlo pasa al motor external con el primer endpoint compatible con OpenAI; apagarlo vuelve al clásico', async () => {
    mockApi([conn('k-anthropic', 'anthropic', 'Claude'), conn('k-ep', 'openai_compatible', 'Mi agente')]);
    renderWithProviders(<Harness initial={toDraft(DEF)} />, { me: ADMIN });
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    await userEvent.click(screen.getByRole('switch', { name: /^Que conteste tu propio agente/ }));
    await waitFor(() => expect(latest.current.engine).toBe('external'));
    expect(fromDraft(latest.current)).toMatchObject({
      engine: 'external',
      external: { connection: 'k-ep', on_errors: 'hang_up' },
    });
    expect(await screen.findByRole('button', { name: 'Probar el endpoint' })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('switch', { name: /^Que conteste tu propio agente/ }));
    expect(latest.current.engine).toBe('classic');
    expect(fromDraft(latest.current)).not.toHaveProperty('external');
  });

  it('sin endpoint cargado pide cargar uno', async () => {
    mockApi([conn('k-anthropic', 'anthropic', 'Claude')]);
    renderWithProviders(
      <Harness initial={toDraft({ ...DEF, engine: 'external', external: { connection: '' } })} />,
      {
        me: ADMIN,
      },
    );
    expect(await screen.findByRole('link', { name: 'Cargar el endpoint' })).toHaveAttribute(
      'href',
      '/clients/c-1?tab=modelos',
    );
  });

  it('con un plan que no lo incluye: aviso y switch deshabilitado', async () => {
    mockApi([], false);
    renderWithProviders(<Harness initial={toDraft(DEF)} />, { me: CLIENT_USER });
    expect(await screen.findByText(/no incluye usar tu propio agente/)).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: /^Que conteste tu propio agente/ })).toBeDisabled();
  });
});
