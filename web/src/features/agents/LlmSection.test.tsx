import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useEffect, useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { LlmConnection } from '@/api/types';
import { LOCAL_LABEL } from '@/features/llm/labels';
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

/** Conexión OpenRouter y una openai_compatible, para el enrutado por proveedores (T4). */
const OR_CONN: LlmConnection = {
  ...CONN,
  id: 'k-or',
  name: 'Mi OpenRouter',
  kind: 'openrouter',
  base_url: 'https://openrouter.ai/api/v1',
  last4: 'or91',
  default_model: 'deepseek/deepseek-v4.1-flash-1017',
};

const COMPAT_CONN: LlmConnection = {
  ...CONN,
  id: 'k-c',
  name: 'Compatible',
  kind: 'openai_compatible',
  base_url: 'https://api.vendor.com/v1',
  last4: 'cc99',
  default_model: 'vendor/model',
};

/** El catálogo de proveedores del modelo de la etapa (GET /llm/openrouter-providers). */
const OR_CATALOG = [
  { tag: 'nebius/fp4', provider_name: 'Nebius', quantization: 'fp4', supports_json_schema: true, supports_tools: true },
  { tag: 'baseten', provider_name: 'Basent', quantization: 'fp8', supports_json_schema: false, supports_tools: true },
];

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
      const url = new URL(req.url);
      const path = url.pathname;
      if (path.endsWith('/llm/params')) return jsonResponse(PARAMS);
      if (path.endsWith('/models')) return jsonResponse(['claude-haiku-5-5', 'claude-sonnet-5-5']);
      if (path.endsWith('/llm-connections')) return jsonResponse(connections);
      // El catálogo de proveedores: lleno para el modelo de OR_CONN, vacío para cualquier otro.
      if (path.endsWith('/openrouter-providers')) {
        const model = url.searchParams.get('model') ?? '';
        return jsonResponse(model === OR_CONN.default_model ? OR_CATALOG : []);
      }
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
}

/** El <input> de un campo de Mantine: getByLabelText también trae un div etiquetado (familia Combobox). */
async function fieldInput(label: string): Promise<HTMLInputElement> {
  const input = (await screen.findAllByLabelText(label)).find((el) => el instanceof HTMLInputElement);
  if (!input) throw new Error(`sin input para ${label}`);
  return input as HTMLInputElement;
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

  // --- Proveedores de OpenRouter (docs/features/LLM_CONEXIONES.md, "UI") -------------------------

  it('con conexión openrouter: selector con el catálogo del modelo y switches deshabilitados sin tags', async () => {
    mockApi([OR_CONN]);
    const initial = toDraft({
      ...DEF,
      llm: { stages: [{ from_turn: 1, connection: 'k-or', model: OR_CONN.default_model }], fallback_local: true },
    });
    renderWithProviders(<Harness initial={initial} />, { me: ADMIN });
    const tags = await fieldInput('Proveedores de OpenRouter');
    // El catálogo del modelo de la etapa autocompleta los tags.
    await userEvent.click(tags);
    expect(
      await screen.findByRole('option', { name: 'nebius/fp4', hidden: true }),
    ).toBeInTheDocument();
    const allow = screen.getByRole('switch', { name: 'Permitir otros proveedores' });
    const require = screen.getByRole('switch', { name: 'Solo proveedores que soportan todo lo que pedimos' });
    expect(allow).toBeDisabled();
    expect(require).toBeDisabled();
    expect(screen.getByText('Se aplican cuando fijás al menos un proveedor.')).toBeInTheDocument();
    // Sin tags no viaja a la definición.
    const out = fromDraft(latest.current) as { llm?: { stages: Record<string, unknown>[] } };
    expect(out.llm!.stages[0]).not.toHaveProperty('provider');

    // Elegir del catálogo arma el chip, habilita los switches y guarda el provider.
    await userEvent.click(screen.getByRole('option', { name: 'nebius/fp4', hidden: true }));
    expect(await screen.findByText('nebius/fp4')).toBeInTheDocument();
    expect(allow).toBeEnabled();
    expect(require).toBeEnabled();
    expect(fromDraft(latest.current)).toMatchObject({
      llm: { stages: [{ provider: { only: ['nebius/fp4'], allow_fallbacks: true, require_parameters: true } }] },
    });
    await userEvent.click(allow);
    expect(fromDraft(latest.current)).toMatchObject({
      llm: { stages: [{ provider: { allow_fallbacks: false } }] },
    });
  });

  it('con anthropic u openai_compatible no hay selector ni switches', async () => {
    for (const conn of [CONN, COMPAT_CONN]) {
      mockApi([conn]);
      const initial = toDraft({
        ...DEF,
        llm: { stages: [{ from_turn: 1, connection: conn.id, model: 'm' }], fallback_local: true },
      });
      const view = renderWithProviders(<Harness initial={initial} />, { me: ADMIN });
      expect(await screen.findByDisplayValue('m')).toBeInTheDocument();
      expect(screen.queryByLabelText('Proveedores de OpenRouter')).not.toBeInTheDocument();
      expect(
        screen.queryByRole('switch', { name: 'Permitir otros proveedores' }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('switch', { name: 'Solo proveedores que soportan todo lo que pedimos' }),
      ).not.toBeInTheDocument();
      view.unmount();
    }
  });

  it('rojo si el tag no soporta lo que pedimos; suave si no está en el catálogo', async () => {
    mockApi([OR_CONN]);
    const initial = toDraft({
      ...DEF,
      llm: {
        stages: [
          {
            from_turn: 1,
            connection: 'k-or',
            model: OR_CONN.default_model,
            provider: { only: ['baseten', 'libre/x'], allow_fallbacks: true, require_parameters: false },
          },
        ],
        fallback_local: true,
      },
    });
    renderWithProviders(<Harness initial={initial} />, { me: ADMIN });
    // La etapa ya traía tags: chips, aviso de soporte y aviso de no verificado; no bloquea el guardado.
    expect(await screen.findByText(/baseten \(Basent\) no soporta salida JSON guiada/)).toBeInTheDocument();
    expect(screen.getByText(/libre\/x: no apareció en el catálogo/)).toBeInTheDocument();
    expect(fromDraft(latest.current)).toMatchObject({
      llm: { stages: [{ provider: { only: ['baseten', 'libre/x'], require_parameters: false } }] },
    });
  });

  it('cambiar el modelo mantiene los tags y avisa los que no aparecen', async () => {
    mockApi([OR_CONN]);
    const initial = toDraft({
      ...DEF,
      llm: {
        stages: [
          {
            from_turn: 1,
            connection: 'k-or',
            model: OR_CONN.default_model,
            provider: { only: ['nebius/fp4'], allow_fallbacks: false },
          },
        ],
        fallback_local: true,
      },
    });
    renderWithProviders(<Harness initial={initial} />, { me: ADMIN });
    expect(await screen.findByText('nebius/fp4')).toBeInTheDocument();
    // Modelo nuevo: catálogo vacío → los tags se conservan con aviso, sin bloquear el guardado.
    const model = await fieldInput('Modelo del proveedor');
    await userEvent.clear(model);
    await userEvent.type(model, 'openai/gpt-5.2');
    expect(await screen.findByText(/Este modelo no listó proveedores/)).toBeInTheDocument();
    expect(screen.getByText('nebius/fp4')).toBeInTheDocument();
    expect(fromDraft(latest.current)).toMatchObject({
      llm: { stages: [{ model: 'openai/gpt-5.2', provider: { only: ['nebius/fp4'], allow_fallbacks: false } }] },
    });
  });

  it('cambiar a una conexión no OpenRouter o a local limpia los tags', async () => {
    mockApi([OR_CONN, CONN]);
    const initial = toDraft({
      ...DEF,
      llm: {
        stages: [
          {
            from_turn: 1,
            connection: 'k-or',
            model: OR_CONN.default_model,
            provider: { only: ['nebius/fp4'], allow_fallbacks: false },
          },
        ],
        fallback_local: true,
      },
    });
    renderWithProviders(<Harness initial={initial} />, { me: ADMIN });
    expect(await screen.findByText('nebius/fp4')).toBeInTheDocument();
    await userEvent.click(await fieldInput('Contesta'));
    await userEvent.click(await screen.findByRole('option', { name: /Claude/, hidden: true }));
    // Se va el selector y el guardado no lleva provider.
    await waitFor(() =>
      expect(screen.queryByLabelText('Proveedores de OpenRouter')).not.toBeInTheDocument(),
    );
    let out = fromDraft(latest.current) as { llm?: { stages: Record<string, unknown>[] } };
    expect(out.llm!.stages[0]).not.toHaveProperty('provider');
    // Volver al modelo de Atentina: sin tags, la etapa local hace que el plan ni viaje (isLocalOnly).
    await userEvent.click(await fieldInput('Contesta'));
    await userEvent.click(
      await screen.findByRole('option', { name: new RegExp(LOCAL_LABEL), hidden: true }),
    );
    out = fromDraft(latest.current) as { llm?: { stages: Record<string, unknown>[] } };
    expect(out).not.toHaveProperty('llm');
  });
});
