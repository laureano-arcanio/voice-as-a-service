import { startCompletion } from '@codemirror/autocomplete';
import { EditorView } from '@codemirror/view';
import { act, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '@/test/render';
import { CATALOG, DECLARED } from './fixtures';
import PromptEditor, { type PromptEditorProps } from './PromptEditor';

// CodeMirror mide el texto con rectángulos que jsdom no calcula.
beforeAll(() => {
  const rect = { x: 0, y: 0, top: 0, left: 0, bottom: 0, right: 0, width: 0, height: 0, toJSON: () => ({}) };
  const rects = Object.assign([], { item: () => null });
  Range.prototype.getClientRects = () => rects as unknown as DOMRectList;
  Range.prototype.getBoundingClientRect = () => rect as DOMRect;
  Element.prototype.getClientRects = () => rects as unknown as DOMRectList;
});

function Harness({
  initial = '',
  onValue,
  ...rest
}: Partial<PromptEditorProps> & { initial?: string; onValue?: (v: string) => void }) {
  const [value, setValue] = useState(initial);
  return (
    <PromptEditor
      field="prompt"
      catalog={CATALOG}
      declared={DECLARED}
      {...rest}
      value={value}
      onChange={(v) => {
        setValue(v);
        onValue?.(v);
      }}
    />
  );
}

const viewOf = () => EditorView.findFromDOM(document.querySelector('.cm-editor') as HTMLElement)!;

/** Tipea como una persona: la transacción lleva `input.type`, que es lo que dispara el autocompletado. */
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

const settle = () => act(() => new Promise<void>((r) => setTimeout(r, 120)));

function press(view: EditorView, key: string, keyCode: number) {
  act(() => {
    view.contentDOM.dispatchEvent(
      new KeyboardEvent('keydown', { key, keyCode, bubbles: true, cancelable: true }),
    );
  });
}

const labels = () =>
  [...document.querySelectorAll('.cm-tooltip-autocomplete [role=option] .cm-completionLabel')].map(
    (e) => e.textContent,
  );

describe('PromptEditor', () => {
  it('al tipear {{ ofrece declaradas y del sistema del campo (no las de herramienta)', async () => {
    renderWithProviders(<Harness initial="Hola " />);
    const view = viewOf();
    view.focus();
    act(() => view.dispatch({ selection: { anchor: 5 } }));
    type(view, '{{');
    await waitFor(() => expect(labels().length).toBeGreaterThan(0));
    expect(labels()).toEqual(['nombre', 'deuda', 'call.phone', 'today']);
  });

  it('seguir tipeando filtra y Enter inserta {{today}} cerrado', async () => {
    const seen: string[] = [];
    renderWithProviders(<Harness onValue={(v) => seen.push(v)} />);
    const view = viewOf();
    view.focus();
    type(view, '{{');
    await waitFor(() => expect(labels().length).toBe(4));
    type(view, 'tod');
    await waitFor(() => expect(labels()).toEqual(['today']));
    await settle();
    press(view, 'Enter', 13);
    await waitFor(() => expect(view.state.doc.toString()).toBe('{{today}}'));
    expect(seen.at(-1)).toBe('{{today}}');
    expect(view.state.selection.main.head).toBe(9);
  });

  it('Tab también acepta, y se come un }} que ya estaba', async () => {
    renderWithProviders(<Harness initial="x {{no}} y" />);
    const view = viewOf();
    view.focus();
    act(() => view.dispatch({ selection: { anchor: 6 } }));
    act(() => {
      startCompletion(view);
    });
    await waitFor(() => expect(labels()).toEqual(['nombre']));
    await settle();
    press(view, 'Tab', 9);
    await waitFor(() => expect(view.state.doc.toString()).toBe('x {{nombre}} y'));
  });

  it('Escape cierra la lista sin insertar', async () => {
    renderWithProviders(<Harness />);
    const view = viewOf();
    view.focus();
    type(view, '{{');
    await waitFor(() => expect(labels().length).toBe(4));
    press(view, 'Escape', 27);
    await waitFor(() => expect(document.querySelector('.cm-tooltip-autocomplete')).toBeNull());
    expect(view.state.doc.toString()).toBe('{{');
  });

  it('marca cada {{x}} por su origen y los títulos #', async () => {
    renderWithProviders(<Harness initial={'# Identidad\n{{today}} {{nombre}} {{rara}} {{secrets.X}}'} />);
    await waitFor(() => expect(document.querySelectorAll('.cm-var').length).toBe(4));
    const cls = [...document.querySelectorAll('.cm-var')].map((e) => e.className.match(/cm-var-(\w+)/)![1]);
    expect(cls).toEqual(['system', 'declared', 'unknown', 'unknown']);
    expect(document.querySelector('.cm-var-unknown')!.getAttribute('title')).toMatch(/Sin fuente declarada/);
    expect(document.querySelector('.cm-var-h')).not.toBeNull();
  });

  it('contador con separador de miles y en rojo al pasarse', () => {
    renderWithProviders(<Harness initial="abcd" maxLength={40000} />);
    expect(screen.getByTestId('prompt-counter')).toHaveTextContent('4 / 40.000');
    expect(screen.getByTestId('prompt-counter').getAttribute('style')).not.toMatch(/red/);
  });

  it('pasado el tope no corta lo escrito y el contador se marca', () => {
    renderWithProviders(<Harness initial="abcdef" maxLength={3} />);
    expect(screen.getByTestId('prompt-counter')).toHaveTextContent('6 / 3');
    expect(viewOf().state.doc.toString()).toBe('abcdef');
    expect(screen.getByTestId('prompt-counter').getAttribute('style')).toMatch(/red/);
  });

  it('muestra etiqueta y error', () => {
    renderWithProviders(<Harness label="Prompt" error="Muy largo" />);
    expect(screen.getByText('Prompt')).toBeInTheDocument();
    expect(screen.getByText('Muy largo')).toBeInTheDocument();
    expect(document.querySelector('.cm-content')!.getAttribute('aria-label')).toBe('Prompt');
  });

  it('en una herramienta ofrece fields.<campo> como prefijo abierto', async () => {
    renderWithProviders(<Harness field="tool" />);
    const view = viewOf();
    view.focus();
    type(view, '{{fie');
    await waitFor(() => expect(labels()).toEqual(['fields.<campo>']));
    await settle();
    press(view, 'Enter', 13);
    await waitFor(() => expect(view.state.doc.toString()).toBe('{{fields.'));
  });
});

vi.setConfig({ testTimeout: 15000 });
