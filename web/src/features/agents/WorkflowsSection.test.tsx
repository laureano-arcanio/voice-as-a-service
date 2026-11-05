import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ClientTool } from '@/api/types';
import { ADMIN, jsonResponse, renderWithProviders } from '@/test/render';
import { type Draft, errorTarget, fromDraft, pathLabel, toDraft } from './draft';
import { DefinitionForm } from './DefinitionForm';
import { WorkflowsEditor } from './WorkflowsSection';

const tool = (slug: string, type: 'http' | 'code', definition: Record<string, unknown>): ClientTool => ({
  id: `t-${slug}`,
  slug,
  type,
  definition,
  revision: 1,
  secrets: [],
  llm_tool: null,
  used_by: [],
  last_test_at: null,
  last_test_ok: null,
  last_test_detail: '',
  created_at: '2026-10-26T10:00:00Z',
  updated_at: '2026-10-26T10:00:00Z',
});

// Con todos los valores fijos: sirve en un workflow.
const BUSCAR = tool('buscar_ficha', 'http', {
  description: 'Busca.',
  http: {
    method: 'POST',
    url: 'https://x',
    body: { type: 'object', properties: { from: { type: 'string', value: '{{call.phone}}' } } },
  },
});
const COBRAR = tool('registrar_cobro', 'http', {
  description: 'Cobra.',
  http: { method: 'POST', url: 'https://x/charges' },
});
const CONSULTAR_GET = tool('consultar', 'http', {
  description: 'Lee.',
  http: { method: 'GET', url: 'https://x/q' },
});
// Con un parámetro que completa el modelo: no sirve.
const ELEGIR = tool('elegir_persona', 'http', {
  description: 'Elige.',
  http: {
    method: 'POST',
    url: 'https://x/s',
    body: { type: 'object', properties: { ref: { type: 'string' } } },
  },
});
const CODIGO = tool('calcular', 'code', {
  description: 'Calcula.',
  code: 'return 1',
  parameters: { type: 'object', properties: {} },
});
const TOOLS = [BUSCAR, COBRAR, CONSULTAR_GET, ELEGIR, CODIGO];

const DEF = {
  agent: { name: 'Sofía', role: 'r', language: 'es-AR' },
  objective: { description: 'o' },
  conversation: { opening: 'Hola', rules: [] },
  fields: {},
  completion: { outcomes: [{ id: 'default', label: 'C', when: {}, message: 'Chau' }] },
};

let last: Draft;

function renderEditor(initial: Draft) {
  last = initial;
  function Harness() {
    const [draft, setDraft] = useState<Draft>(initial);
    const update = (fn: (d: Draft) => Draft) =>
      setDraft((d) => {
        last = fn(d);
        return last;
      });
    return <WorkflowsEditor draft={draft} update={update} clientId="c-1" />;
  }
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse(TOOLS)),
  );
  return renderWithProviders(<Harness />, { me: ADMIN });
}

afterEach(() => vi.unstubAllGlobals());

/** Las opciones de un selector, por su rótulo: ambos dropdowns están en el DOM aunque estén cerrados. */
const optionsOf = (label: RegExp) => within(screen.getByRole('listbox', { name: label, hidden: true }));

describe('workflows del agente', () => {
  it('ida y vuelta de pre_call y post_call con sus valores', () => {
    const wf = {
      pre_call: { tool: 'buscar_ficha', timeout_ms: 2000 },
      post_call: { tool: 'registrar_cobro', when: 'always' },
    };
    expect(fromDraft(toDraft({ ...DEF, workflows: wf } as never)).workflows).toEqual(wf);
  });

  it('los defaults: 1500 ms y handoff_accepted; sin bloque no manda nada', () => {
    const d = toDraft({
      ...DEF,
      workflows: { pre_call: { tool: 'a' }, post_call: { tool: 'b' } },
    } as never);
    expect(d.workflows).toEqual({
      preCall: { tool: 'a', timeoutMs: 1500 },
      postCall: { tool: 'b', when: 'handoff_accepted' },
    });
    expect(fromDraft(toDraft(DEF as never))).not.toHaveProperty('workflows');
  });

  it('con tu propio agente conserva workflows: el post-call (el cobro) corre igual', () => {
    const wf = { pre_call: { tool: 'a', timeout_ms: 1500 }, post_call: { tool: 'b', when: 'always' } };
    const d = toDraft({ ...DEF, workflows: wf } as never);
    const ext = fromDraft({
      ...d,
      external: {
        connection: 'c1',
        model: '',
        system: '',
        firstTokenTimeoutMs: 4000,
        errorMessage: 'x',
        maxErrors: 2,
        onErrors: 'hang_up',
      },
    });
    expect(ext.workflows).toEqual(wf);
    // Una definicion externa que ya los trae pasa por el formulario sin perderlos.
    const back = fromDraft(toDraft({ ...DEF, workflows: wf, external: { connection: 'c1' } } as never));
    expect(back.workflows).toEqual(wf);
  });

  it('el formulario muestra la sección con tu propio agente', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse(TOOLS)),
    );
    const draft = toDraft({
      ...DEF,
      workflows: { post_call: { tool: 'registrar_cobro' } },
      external: { connection: 'c1' },
    } as never);
    renderWithProviders(
      <DefinitionForm
        part="herramientas"
        draft={draft}
        update={() => undefined}
        opened={new Set()}
        toggle={() => undefined}
        voiceSeed="x"
        clientId="c-1"
      />,
      { me: ADMIN },
    );
    expect(await screen.findByRole('textbox', { name: /Después de la conversación/ })).toHaveValue(
      'registrar_cobro · API',
    );
  });

  it('el error workflows.post_call.tool lleva a su sección', () => {
    const d = toDraft(DEF as never);
    expect(errorTarget(d, 'workflows.post_call.tool')).toEqual({ section: 'automaticas' });
    expect(pathLabel(d, 'workflows.post_call.tool')).toBe(
      'Automáticas › después de la conversación › herramienta',
    );
  });
});

describe('WorkflowsEditor', () => {
  it('no ofrece las que piden parámetros al modelo ni las visibles; el post-call tampoco las GET', async () => {
    renderEditor(toDraft({ ...DEF, tools: [{ tool: 'calcular' }] } as never));
    const pre = await screen.findByRole('textbox', { name: /Antes de la conversación/ });
    await userEvent.click(pre);
    const preOptions = optionsOf(/Antes de la conversación/);
    expect(await preOptions.findByRole('option', { name: /buscar_ficha/, hidden: true })).toBeInTheDocument();
    expect(preOptions.getByRole('option', { name: /registrar_cobro/, hidden: true })).toBeInTheDocument();
    expect(preOptions.getByRole('option', { name: /consultar/, hidden: true })).toBeInTheDocument();
    expect(
      preOptions.queryByRole('option', { name: /elegir_persona/, hidden: true }),
    ).not.toBeInTheDocument();
    // calcular es una herramienta visible del agente.
    expect(preOptions.queryByRole('option', { name: /calcular/, hidden: true })).not.toBeInTheDocument();

    await userEvent.click(preOptions.getByRole('option', { name: /buscar_ficha/, hidden: true }));
    expect(last.workflows.preCall).toEqual({ tool: 'buscar_ficha', timeoutMs: 1500 });

    const post = screen.getByRole('textbox', { name: /Después de la conversación/ });
    await userEvent.click(post);
    const postOptions = optionsOf(/Después de la conversación/);
    expect(
      await postOptions.findByRole('option', { name: /registrar_cobro/, hidden: true }),
    ).toBeInTheDocument();
    // La del pre-call no se repite; una GET no lleva Idempotency-Key.
    expect(postOptions.queryByRole('option', { name: /buscar_ficha/, hidden: true })).not.toBeInTheDocument();
    expect(postOptions.queryByRole('option', { name: /consultar/, hidden: true })).not.toBeInTheDocument();
    expect(
      postOptions.queryByRole('option', { name: /elegir_persona/, hidden: true }),
    ).not.toBeInTheDocument();
  });

  it('elige el post-call y su condición, y los guarda en la definición', async () => {
    renderEditor(toDraft(DEF as never));
    const post = await screen.findByRole('textbox', { name: /Después de la conversación/ });
    await userEvent.click(post);
    await userEvent.click(
      await optionsOf(/Después de la conversación/).findByRole('option', {
        name: /registrar_cobro/,
        hidden: true,
      }),
    );
    expect(fromDraft(last).workflows).toEqual({
      post_call: { tool: 'registrar_cobro', when: 'handoff_accepted' },
    });
    await userEvent.click(screen.getByRole('textbox', { name: /Cuándo corre/ }));
    await userEvent.click(
      await optionsOf(/Cuándo corre/).findByRole('option', { name: /Siempre, al terminar/, hidden: true }),
    );
    expect(fromDraft(last).workflows).toEqual({ post_call: { tool: 'registrar_cobro', when: 'always' } });
  });

  it('avisa que la condición "acepta la derivación" no se cumple si el agente no tiene áreas', async () => {
    const aviso = /no tiene áreas de derivación/;
    // Sin áreas: el valor por defecto sigue siendo handoff_accepted, pero se avisa; con "Siempre", no.
    renderEditor(toDraft({ ...DEF, workflows: { post_call: { tool: 'registrar_cobro' } } } as never));
    expect(await screen.findByText(aviso)).toBeInTheDocument();
    expect(fromDraft(last).workflows).toEqual({
      post_call: { tool: 'registrar_cobro', when: 'handoff_accepted' },
    });
    await userEvent.click(screen.getByRole('textbox', { name: /Cuándo corre/ }));
    await userEvent.click(
      await optionsOf(/Cuándo corre/).findByRole('option', { name: /Siempre, al terminar/, hidden: true }),
    );
    expect(screen.queryByText(aviso)).not.toBeInTheDocument();
  });

  it('no avisa si el agente tiene áreas, ni si no hay post-call', async () => {
    const aviso = /no tiene áreas de derivación/;
    renderEditor(
      toDraft({
        ...DEF,
        handoff: { areas: [{ area_id: 'a1' }] },
        workflows: { post_call: { tool: 'registrar_cobro' } },
      } as never),
    );
    await screen.findByRole('textbox', { name: /Cuándo corre/ });
    expect(screen.queryByText(aviso)).not.toBeInTheDocument();
  });

  it('sin post-call no avisa de nada', async () => {
    renderEditor(toDraft(DEF as never));
    await screen.findByRole('textbox', { name: /Después de la conversación/ });
    expect(screen.queryByText(/no tiene áreas de derivación/)).not.toBeInTheDocument();
  });

  it('cambia el tiempo máximo del pre-call y avisa de una herramienta que ya no sirve', async () => {
    renderEditor(
      toDraft({
        ...DEF,
        workflows: {
          pre_call: { tool: 'buscar_ficha', timeout_ms: 1500 },
          post_call: { tool: 'consultar', when: 'handoff_accepted' },
        },
      } as never),
    );
    const timeout = await screen.findByRole('textbox', { name: /Tiempo máximo/ });
    await userEvent.clear(timeout);
    await userEvent.type(timeout, '2500');
    expect(last.workflows.preCall?.timeoutMs).toBe(2500);
    // consultar es GET: se avisa, aunque esté elegida (el servidor también la rechaza).
    const alert = screen.getByText(/consultar no sirve para esto/);
    expect(within(alert.closest('[role="alert"]') as HTMLElement).getByText(/no sirve/)).toBeInTheDocument();
  });
});
