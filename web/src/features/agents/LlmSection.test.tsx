import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useEffect, useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { LlmConnection } from '@/api/types';
import { ADMIN, jsonResponse, renderWithProviders } from '@/test/render';
import { type Draft, fromDraft, toDraft } from './draft';
import { LlmSection } from './LlmSection';

const CONN: LlmConnection = {
  id: 'k-1',
  client_id: 'c-1',
  name: 'Claude',
  kind: 'anthropic',
  base_url: 'https://api.anthropic.com',
  last4: 'zz99',
  default_model: 'claude-haiku-5-5',
  json_mode: 'json_schema',
  created_by: null,
  created_at: '2026-10-15T12:00:00Z',
  last_test_at: null,
  last_test_ok: true,
  last_test_detail: 'json_schema · 380 ms',
  used_by: 0,
};

const DEF = {
  id: 'a',
  version: 1,
  engine: 'classic',
  agent: { name: 'S', role: 'r', language: 'es-AR' },
  objective: { description: 'x' },
  conversation: { opening: 'Hola', rules: [] },
  knowledge: '',
  fields: {},
  completion: { when: 'all_required_fields_completed', outcomes: [{ id: 'ok', label: 'ok', when: {}, message: 'm', goal: true }] },
};

/** El borrador vigente, para verificar lo que saldria a la definicion. */
const latest = { current: null as unknown as Draft };

function Harness({ initial }: { initial: Draft }) {
  const [draft, setDraft] = useState(initial);
  useEffect(() => {
    latest.current = draft;
  }, [draft]);
  return <LlmSection draft={draft} update={(fn) => setDraft(fn)} clientId="c-1" />;
}

function mockApi(connections: LlmConnection[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const path = new URL(req.url).pathname;
      if (path.endsWith('/models')) return jsonResponse(['claude-haiku-5-5', 'claude-sonnet-5-5']);
      if (path.endsWith('/llm-connections')) return jsonResponse(connections);
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('LlmSection', () => {
  it('sin plan: una etapa con el servidor Atentina y sin aviso de privacidad', async () => {
    mockApi([CONN]);
    renderWithProviders(<Harness initial={toDraft(DEF)} />, { me: ADMIN });
    expect(await screen.findByText('Desde el turno')).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Modelo de lenguaje' })).toHaveValue('Servidor Atentina');
    expect(screen.queryByText(/salen del servidor/)).not.toBeInTheDocument();
    expect(fromDraft(latest.current)).not.toHaveProperty('llm');
  });

  it('elegir una conexión propone su modelo, avisa y guarda la etapa', async () => {
    mockApi([CONN]);
    renderWithProviders(<Harness initial={toDraft(DEF)} />, { me: ADMIN });
    await userEvent.click(await screen.findByRole('textbox', { name: 'Modelo de lenguaje' }));
    await userEvent.click(await screen.findByRole('option', { name: 'Claude · …zz99', hidden: true }));
    expect(await screen.findByDisplayValue('claude-haiku-5-5')).toBeInTheDocument();
    expect(screen.getByText(/Desde el turno 1, este agente manda la conversación a Anthropic/)).toBeInTheDocument();
    expect(fromDraft(latest.current)).toMatchObject({
      llm: { stages: [{ from_turn: 1, connection: 'k-1', model: 'claude-haiku-5-5' }], fallback_local: true },
    });
  });

  it('agrega una etapa desde el turno 4 y el límite es de tres', async () => {
    mockApi([CONN]);
    const initial = toDraft({
      ...DEF,
      llm: { stages: [{ from_turn: 1 }], fallback_local: true },
    });
    renderWithProviders(<Harness initial={initial} />, { me: ADMIN });
    const add = await screen.findByRole('button', { name: /Agregar etapa/ });
    await userEvent.click(add);
    expect(latest.current.llm?.stages.map((s) => s.fromTurn)).toEqual([1, 4]);
    await userEvent.click(add);
    expect(latest.current.llm?.stages.map((s) => s.fromTurn)).toEqual([1, 4, 7]);
    expect(add).toBeDisabled();
    await userEvent.click(within(document.body).getAllByRole('button', { name: 'Quitar etapa' })[0]!);
    expect(latest.current.llm?.stages).toHaveLength(2);
  });

  it('una conexión dada de baja se ve como tal en la etapa', async () => {
    mockApi([]);
    const initial = toDraft({
      ...DEF,
      llm: { stages: [{ from_turn: 1, connection: 'gone', model: 'm' }], fallback_local: true },
    });
    renderWithProviders(<Harness initial={initial} />, { me: ADMIN });
    expect(await screen.findByDisplayValue('Conexión dada de baja')).toBeInTheDocument();
  });
});
