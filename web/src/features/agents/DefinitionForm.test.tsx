import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useEffect, useState } from 'react';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { EditorView } from '@codemirror/view';
import type { Definition } from '@/api/types';
import type { FieldError } from '@/api/errors';
import { CATALOG } from '@/components/variables/fixtures';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { DefinitionForm } from './DefinitionForm';
import { type Draft, fromDraft, type Part, toDraft } from './draft';

// CodeMirror mide el texto con rectángulos que jsdom no calcula.
beforeAll(() => {
  const rect = { x: 0, y: 0, top: 0, left: 0, bottom: 0, right: 0, width: 0, height: 0, toJSON: () => ({}) };
  const rects = Object.assign([], { item: () => null });
  Range.prototype.getClientRects = () => rects as unknown as DOMRectList;
  Range.prototype.getBoundingClientRect = () => rect as DOMRect;
  Element.prototype.getClientRects = () => rects as unknown as DOMRectList;
});

const ANALYSIS = {
  summary: true,
  instructions: '',
  fields: [{ name: 'quiere', description: 'Quiere', type: 'boolean' }],
};
const DEF = {
  id: 'a',
  version: 1,
  agent: { name: 'Sofía', language: 'es-AR' },
  prompt: '# Identidad\nSos Sofía.',
  first_message: 'Hola',
  variables: [{ name: 'deuda', default: '1000', description: 'Lo que debe' }],
  analysis: ANALYSIS,
} as Definition;

// Las áreas del cliente: el cierre de turn_attention elige entre las del agente (draft.handoff).
const AREAS = [
  { id: 'a1', name: 'Ventas' },
  { id: 'a2', name: 'Administración' },
];

function mockApi() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL((input instanceof Request ? input : new Request(input)).url);
      if (url.pathname === '/api/v1/variables/catalog') return jsonResponse(CATALOG);
      if (url.pathname.endsWith('/tools')) return jsonResponse([]);
      if (url.pathname === '/api/v1/voices') return jsonResponse([]);
      if (url.pathname === '/api/v1/handoff-areas') return jsonResponse(AREAS);
      return jsonResponse({ detail: 'no mock' }, 404);
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

const props = {
  draft: toDraft(DEF),
  update: () => undefined,
  opened: new Set<string>(),
  toggle: () => undefined,
  voiceSeed: 'a',
  clientId: 'c-1',
  agentId: 'a',
};

describe('DefinitionForm', () => {
  it('muestra el 422 de prompt en su sección', async () => {
    mockApi();
    renderWithProviders(
      <DefinitionForm
        part="conversacion"
        {...props}
        errors={[{ path: 'prompt', message: '{{secrets.X}} no puede ir al LLM (solo en herramientas)' }]}
      />,
      { me: CLIENT_USER },
    );
    expect(await screen.findByText(/no puede ir al LLM/)).toBeInTheDocument();
  });

  it('en la otra pestaña el error de prompt no aparece', async () => {
    mockApi();
    renderWithProviders(
      <DefinitionForm
        part="datos"
        {...props}
        errors={[{ path: 'prompt', message: 'El error del prompt' }]}
      />,
      { me: CLIENT_USER },
    );
    expect(await screen.findByText('Análisis al terminar')).toBeInTheDocument();
    expect(screen.queryByText('El error del prompt')).toBeNull();
  });
});

// El formulario con estado real, en la pestaña que se pida.
const latest = { current: null as unknown as Draft };

function FormHarness({ initial, errors, part = 'voz' }: { initial: Draft; errors?: FieldError[]; part?: Part }) {
  const [draft, setDraft] = useState(initial);
  useEffect(() => {
    latest.current = draft;
  }, [draft]);
  return (
    <DefinitionForm
      part={part}
      draft={draft}
      update={(fn) => setDraft(fn)}
      opened={new Set()}
      toggle={() => undefined}
      voiceSeed="a"
      clientId="c-1"
      agentId="a"
      errors={errors}
    />
  );
}

/** Las opciones de un selector, por su rótulo: el dropdown está en el DOM aunque esté cerrado. */
const optionsOf = (label: RegExp) => within(screen.getByRole('listbox', { name: label, hidden: true }));

/** El CodeMirror del editor de texto con variables (uno por pestaña). */
const viewOf = () => EditorView.findFromDOM(document.querySelector('.cm-editor') as HTMLElement)!;

/** Tipea como una persona (userEvent.type no llega al estado de CodeMirror en jsdom). */
function type(view: EditorView, text: string) {
  act(() => {
    const pos = view.state.selection.main.head;
    view.dispatch({
      changes: { from: pos, insert: text },
      selection: { anchor: pos + text.length },
      userEvent: 'input.type',
    });
  });
}

describe('DefinitionForm: Si la persona no responde', () => {
  it('la sección se muestra con sus defaults y apagada no guarda nada', async () => {
    mockApi();
    renderWithProviders(<FormHarness initial={toDraft(DEF)} />, { me: CLIENT_USER });
    expect(await screen.findByText('Si la persona no responde')).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: /^Activar/ })).not.toBeChecked();
    expect(screen.getByRole('textbox', { name: /Repetir la última pregunta a los/ })).toHaveValue('7');
    expect(screen.getByRole('textbox', { name: 'Cantidad de avisos' })).toHaveValue('2');
    expect(screen.getByRole('textbox', { name: /Espera entre avisos/ })).toHaveValue('7');
    expect(screen.getByRole('textbox', { name: /Cerrar la llamada a los/ })).toHaveValue('30');
    expect(screen.getByRole('textbox', { name: /Al cerrar/ })).toHaveValue('Cortar');
    // Los textos vacíos usan el placeholder con el texto de la plataforma.
    expect(screen.getByPlaceholderText('¿Me escuchás? Te repito:')).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText('No te escucho bien. Podés volver a llamarnos o escribirnos por WhatsApp. ¡Gracias!'),
    ).toBeInTheDocument();
    expect(fromDraft(latest.current!)).not.toHaveProperty('turn_attention');
  });

  it('el switch Activar prende el bloque y se guarda con enabled', async () => {
    mockApi();
    renderWithProviders(<FormHarness initial={toDraft(DEF)} />, { me: CLIENT_USER });
    await screen.findByText('Si la persona no responde');
    await userEvent.click(screen.getByRole('switch', { name: /^Activar/ }));
    expect(latest.current!.turnAttention.enabled).toBe(true);
    expect(fromDraft(latest.current!).turn_attention).toMatchObject({
      enabled: true,
      end_after_ms: 30000,
    });
  });

  it('Al cerrar=Pasar muestra el Select de áreas del agente y elige una', async () => {
    mockApi();
    const d = toDraft({
      ...DEF,
      handoff: {
        areas: [{ area_id: 'a1', when: '' }],
        hold_music: { enabled: true, track: 'default', volume: 0.3 },
      },
    } as Definition);
    renderWithProviders(<FormHarness initial={d} />, { me: CLIENT_USER });
    await screen.findByText('Si la persona no responde');
    // Con Cortar no hay Select de área.
    expect(screen.queryByRole('textbox', { name: /Pasar al área/ })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('textbox', { name: /Al cerrar/ }));
    await userEvent.click(optionsOf(/Al cerrar/).getByRole('option', { name: 'Pasar con una persona', hidden: true }));
    expect(latest.current!.turnAttention.onEnd).toBe('transfer');

    const area = await screen.findByRole('textbox', { name: /Pasar al área/ });
    expect(area).toHaveAttribute('placeholder', 'La primera área');
    await userEvent.click(area);
    // El nombre viene de la lista de áreas del cliente, no el id.
    await userEvent.click(
      await optionsOf(/Pasar al área/).findByRole('option', { name: 'Ventas', hidden: true }),
    );
    expect(latest.current!.turnAttention.onEndAreaId).toBe('a1');
    expect(fromDraft(latest.current!).turn_attention).toMatchObject({
      on_end: 'transfer',
      on_end_area_id: 'a1',
    });
  });

  it('el error turn_attention.end_after_ms se muestra en su campo', async () => {
    mockApi();
    renderWithProviders(
      <FormHarness
        initial={toDraft(DEF)}
        errors={[
          {
            path: 'turn_attention.end_after_ms',
            message: 'El cierre no puede ser antes del primer aviso (reminder_after_ms)',
          },
        ]}
      />,
      { me: CLIENT_USER },
    );
    // El mensaje queda dentro del campo "Cerrar la llamada a los", con su etiqueta.
    const error = await screen.findByText(/no puede ser antes del primer aviso/);
    const root = error.closest('div')!;
    expect(within(root).getByRole('textbox', { name: /Cerrar la llamada a los/ })).toBeInTheDocument();
  });
});

describe('DefinitionForm: Análisis al terminar', () => {
  it('el prompt se edita con el editor de variables y Restaurar lo deja en el de la plataforma', async () => {
    mockApi();
    renderWithProviders(<FormHarness part="datos" initial={toDraft(DEF)} />, { me: CLIENT_USER });
    await screen.findByTestId('prompt-editor');
    const view = viewOf();
    // El editor arranca con el prompt del borrador (vacío: el de la plataforma).
    expect(view.state.doc.toString()).toBe('');
    // Vacío: la acción de la cabecera es partir del default (habilitada cuando cargó el catálogo).
    const start = await screen.findByRole('button', { name: 'Partir del predeterminado' });
    await waitFor(() => expect(start).toBeEnabled());
    view.focus();
    type(view, 'Sos el extractor de esta cuenta. Mirá {{');
    // Tipear {{ ofrece las declaradas y las del sistema que aplican al análisis (call.phone, no).
    const labels = () =>
      [...document.querySelectorAll('.cm-tooltip-autocomplete [role=option] .cm-completionLabel')].map(
        (e) => e.textContent,
      );
    await waitFor(() => expect(labels()).toEqual(['deuda', 'today']));
    type(view, 'tod');
    await waitFor(() => expect(labels()).toEqual(['today']));
    await act(() => new Promise<void>((r) => setTimeout(r, 120)));
    act(() => {
      view.contentDOM.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true, cancelable: true }),
      );
    });
    await waitFor(() =>
      expect(latest.current!.analysis.prompt).toBe('Sos el extractor de esta cuenta. Mirá {{today}}'),
    );
    expect(fromDraft(latest.current!).analysis).toMatchObject({
      prompt: 'Sos el extractor de esta cuenta. Mirá {{today}}',
    });
    // Con texto, la misma cabecera ofrece volver al default.
    await userEvent.click(screen.getByRole('button', { name: 'Restaurar el predeterminado' }));
    expect(latest.current!.analysis.prompt).toBe('');
  });

  it('Partir del predeterminado copia el default al editor y queda editable', async () => {
    mockApi();
    renderWithProviders(<FormHarness part="datos" initial={toDraft(DEF)} />, { me: CLIENT_USER });
    const start = await screen.findByRole('button', { name: 'Partir del predeterminado' });
    await waitFor(() => expect(start).toBeEnabled());
    await userEvent.click(start);
    // El default entra tal cual al editor (no como sugerencia gris).
    await waitFor(() => expect(latest.current!.analysis.prompt).toBe(CATALOG.defaults.analysis_prompt));
    const view = viewOf();
    expect(view.state.doc.toString()).toBe(CATALOG.defaults.analysis_prompt);
    // Editable como cualquier prompt: el cursor al final y se le agrega texto.
    view.focus();
    act(() => view.dispatch({ selection: { anchor: view.state.doc.length } }));
    type(view, ' EXTRA.');
    await waitFor(() =>
      expect(latest.current!.analysis.prompt).toBe(`${CATALOG.defaults.analysis_prompt} EXTRA.`),
    );
    // Guardar lleva el texto copiado (el agente deja de seguir el default de la plataforma).
    const out = fromDraft(latest.current!) as { analysis: Record<string, unknown> };
    expect(out.analysis).toMatchObject({ prompt: `${CATALOG.defaults.analysis_prompt} EXTRA.` });
    expect(out.analysis).not.toHaveProperty('instructions');
  });

  it('Partir del predeterminado limpia las instrucciones viejas y el aviso se va', async () => {
    mockApi();
    const d = toDraft({ ...DEF, analysis: { ...ANALYSIS, instructions: 'Mirá la deuda.' } } as Definition);
    renderWithProviders(<FormHarness part="datos" initial={d} />, { me: CLIENT_USER });
    expect(await screen.findByText(/Instrucciones del análisis de una versión anterior/)).toBeInTheDocument();
    expect(screen.getByText('Mirá la deuda.')).toBeInTheDocument();
    await userEvent.click(await screen.findByRole('button', { name: 'Partir del predeterminado' }));
    expect(latest.current!.analysis.prompt).toBe(CATALOG.defaults.analysis_prompt);
    expect(latest.current!.analysis.legacyInstructions).toBe('');
    await waitFor(() => expect(screen.queryByText(/versión anterior/)).toBeNull());
    // Guardar lleva el default copiado como prompt; las instructions ya no viajan.
    const out = fromDraft(latest.current!) as { analysis: Record<string, unknown> };
    expect(out.analysis).toMatchObject({ prompt: CATALOG.defaults.analysis_prompt });
    expect(out.analysis).not.toHaveProperty('instructions');
  });

  it('guardar sin tocar el prompt conserva las instrucciones viejas', async () => {
    mockApi();
    const d = toDraft({ ...DEF, analysis: { ...ANALYSIS, instructions: 'Mirá la deuda.' } } as Definition);
    renderWithProviders(<FormHarness part="datos" initial={d} />, { me: CLIENT_USER });
    await screen.findByTestId('prompt-editor');
    expect(latest.current!.analysis.legacyInstructions).toBe('Mirá la deuda.');
    const out = fromDraft(latest.current!) as { analysis: Record<string, unknown> };
    expect(out.analysis).toMatchObject({ instructions: 'Mirá la deuda.' });
    expect(out.analysis).not.toHaveProperty('prompt');
  });

  it('Traer al prompt compone el default de la plataforma con las instrucciones viejas', async () => {
    mockApi();
    const d = toDraft({ ...DEF, analysis: { ...ANALYSIS, instructions: 'Mirá la deuda.' } } as Definition);
    renderWithProviders(<FormHarness part="datos" initial={d} />, { me: CLIENT_USER });
    const bring = await screen.findByRole('button', { name: 'Traer al prompt' });
    // Se habilita cuando carga el catálogo (el default que compone viene de ahí).
    await waitFor(() => expect(bring).toBeEnabled());
    await userEvent.click(bring);
    const composed = `${CATALOG.defaults.analysis_prompt}\n\nINSTRUCCIONES:\nMirá la deuda.`;
    expect(latest.current!.analysis.prompt).toBe(composed);
    // El aviso se oculta (hay prompt) y el próximo guardado migra: instructions no viaja.
    await waitFor(() => expect(screen.queryByText(/versión anterior/)).toBeNull());
    const out = fromDraft(latest.current!) as { analysis: Record<string, unknown> };
    expect(out.analysis).toMatchObject({ prompt: composed });
    expect(out.analysis).not.toHaveProperty('instructions');
  });

  it('sin catálogo, Partir del predeterminado y Traer al prompt quedan deshabilitados', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ detail: 'sin catálogo' }, 404)));
    const d = toDraft({ ...DEF, analysis: { ...ANALYSIS, instructions: 'Mirá la deuda.' } } as Definition);
    renderWithProviders(<FormHarness part="datos" initial={d} />, { me: CLIENT_USER });
    const start = await screen.findByRole('button', { name: 'Partir del predeterminado' });
    expect(start).toBeDisabled();
    const bring = await screen.findByRole('button', { name: 'Traer al prompt' });
    await waitFor(() => expect(bring).toBeDisabled());
    // Sin catálogo tampoco hay sugerencia gris en el editor.
    await screen.findByTestId('prompt-editor');
    expect(viewOf().state.doc.toString()).toBe('');
    expect(document.querySelector('.cm-placeholder')).toBeNull();
  });

  it('con prompt propio no aparece el aviso de instrucciones viejas', async () => {
    mockApi();
    const d = toDraft({ ...DEF, analysis: { ...ANALYSIS, prompt: 'Mi prompt.' } } as Definition);
    renderWithProviders(<FormHarness part="datos" initial={d} />, { me: CLIENT_USER });
    await screen.findByTestId('prompt-editor');
    expect(screen.queryByText(/versión anterior/)).toBeNull();
  });

  it('el 422 de variables prohibidas del prompt del análisis se muestra en el editor', async () => {
    mockApi();
    renderWithProviders(
      <FormHarness
        part="datos"
        initial={toDraft(DEF)}
        errors={[{ path: 'analysis.prompt', message: '{{fields.mail}} no puede ir al LLM (solo en herramientas)' }]}
      />,
      { me: CLIENT_USER },
    );
    expect(await screen.findByText(/no puede ir al LLM/)).toBeInTheDocument();
  });
});
