import { screen, waitFor, within } from '@testing-library/react';
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

/** El borrador vigente, para verificar lo que saldria a la definicion. */
const latest = { current: null as unknown as Draft };

function Harness({ initial }: { initial: Draft }) {
  const [draft, setDraft] = useState(initial);
  useEffect(() => {
    latest.current = draft;
  }, [draft]);
  return <LlmSection draft={draft} update={(fn) => setDraft(fn)} clientId="c-1" />;
}

const PARAMS = {
  local_model: 'cyankiwi/gemma-4-26B',
  local_defaults: { temperature: 1, enable_thinking: false, top_k: 64 },
  providers: [
    {
      kind: 'vllm',
      label: 'Servidor propio (local)',
      params: [
        {
          name: 'temperature',
          label: 'Temperatura',
          type: 'number',
          minimum: 0,
          maximum: 2,
          choices: [],
          hint: '',
        },
        { name: 'top_k', label: 'Top K', type: 'int', minimum: 0, choices: [], hint: '' },
        { name: 'enable_thinking', label: 'Razonamiento', type: 'bool', choices: [], hint: '' },
      ],
    },
    {
      kind: 'anthropic',
      label: 'Anthropic',
      params: [
        { name: 'effort', label: 'Esfuerzo', type: 'choice', choices: ['low', 'medium', 'high'], hint: '' },
      ],
    },
  ],
};

function mockApi(connections: LlmConnection[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const req = input instanceof Request ? input : new Request(input);
      const path = new URL(req.url).pathname;
      if (path.endsWith('/llm/params')) return jsonResponse(PARAMS);
      if (path.endsWith('/models')) return jsonResponse(['claude-haiku-5-5', 'claude-sonnet-5-5']);
      if (path.endsWith('/llm-connections')) return jsonResponse(connections);
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('LlmSection', () => {
  it('por defecto: el modelo de Atentina, sin etapas ni aviso de privacidad', async () => {
    mockApi([CONN]);
    renderWithProviders(<Harness initial={toDraft(DEF)} />, { me: ADMIN });
    expect(await screen.findByRole('radio', { name: 'Modelo atentina-conversational-v1' })).toBeChecked();
    expect(screen.queryByText('Desde el turno')).not.toBeInTheDocument();
    expect(screen.queryByText(/salen de Atentina/)).not.toBeInTheDocument();
    expect(fromDraft(latest.current)).not.toHaveProperty('llm');
  });

  it('sin claves cargadas: las etapas no se habilitan y se pide cargar una', async () => {
    mockApi([]);
    renderWithProviders(<Harness initial={toDraft(DEF)} />, { me: ADMIN });
    expect(await screen.findByRole('link', { name: 'Cargar una clave' })).toHaveAttribute(
      'href',
      '/models',
    );
    expect(screen.getByRole('radio', { name: 'Mis proveedores, por etapas' })).toBeDisabled();
  });

  it('con una clave: pasar a etapas propone la conexión y su modelo, avisa y guarda', async () => {
    mockApi([CONN]);
    renderWithProviders(<Harness initial={toDraft(DEF)} />, { me: ADMIN });
    const byok = await screen.findByRole('radio', { name: 'Mis proveedores, por etapas' });
    await waitFor(() => expect(byok).toBeEnabled());
    await userEvent.click(byok);
    expect(await screen.findByDisplayValue('claude-haiku-5-5')).toBeInTheDocument();
    expect(
      screen.getByText(/Desde el turno 1, este agente manda la conversación a Anthropic/),
    ).toBeInTheDocument();
    expect(fromDraft(latest.current)).toMatchObject({
      llm: { stages: [{ from_turn: 1, connection: 'k-1', model: 'claude-haiku-5-5' }], fallback_local: true },
    });

    // Volver al de Atentina pregunta y quita las etapas.
    await userEvent.click(screen.getByRole('radio', { name: 'Modelo atentina-conversational-v1' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Volver' }));
    await waitFor(() => expect(latest.current.llm).toBeNull());
  });

  it('agrega una etapa desde el turno 4 y el límite es de tres', async () => {
    mockApi([CONN]);
    const initial = toDraft({
      ...DEF,
      llm: { stages: [{ from_turn: 1, connection: 'k-1', model: 'm' }], fallback_local: true },
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

  it('muestra los defaults y cambiarlos pide confirmación', async () => {
    mockApi([CONN]);
    renderWithProviders(<Harness initial={toDraft(DEF)} />, { me: ADMIN });
    await userEvent.click(await screen.findByRole('button', { name: /Configurar parámetros del modelo/ }));
    // El default de la familia local (gemma) es 1, y se ve sin tocar nada.
    const temp = await screen.findByRole('textbox', { name: 'Temperatura' });
    await waitFor(() => expect(temp).toHaveValue('1'));
    expect(temp).toBeDisabled();
    expect(screen.getByRole('textbox', { name: 'Top K' })).toHaveValue('64');

    await userEvent.click(screen.getByRole('button', { name: 'Cambiar valores' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Cambiar' }));
    await waitFor(() => expect(temp).toBeEnabled());
    await userEvent.clear(temp);
    await userEvent.type(temp, '0.5');
    expect(fromDraft(latest.current)).toMatchObject({ generation: { params: { temperature: 0.5 } } });

    await userEvent.click(screen.getByRole('button', { name: 'Volver al default: Temperatura' }));
    expect(fromDraft(latest.current)).not.toHaveProperty('generation');
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
