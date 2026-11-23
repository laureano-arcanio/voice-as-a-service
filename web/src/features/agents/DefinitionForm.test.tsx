import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useEffect, useState } from 'react';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import type { Definition } from '@/api/types';
import type { FieldError } from '@/api/errors';
import { CATALOG } from '@/components/variables/fixtures';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { DefinitionForm } from './DefinitionForm';
import { type Draft, fromDraft, toDraft } from './draft';

// CodeMirror mide el texto con rectángulos que jsdom no calcula.
beforeAll(() => {
  const rect = { x: 0, y: 0, top: 0, left: 0, bottom: 0, right: 0, width: 0, height: 0, toJSON: () => ({}) };
  const rects = Object.assign([], { item: () => null });
  Range.prototype.getClientRects = () => rects as unknown as DOMRectList;
  Range.prototype.getBoundingClientRect = () => rect as DOMRect;
  Element.prototype.getClientRects = () => rects as unknown as DOMRectList;
});

const DEF = {
  id: 'a',
  version: 1,
  agent: { name: 'Sofía', language: 'es-AR' },
  prompt: '# Identidad\nSos Sofía.',
  first_message: 'Hola',
  variables: [{ name: 'deuda', default: '1000', description: 'Lo que debe' }],
  analysis: {
    summary: true,
    instructions: '',
    fields: [{ name: 'quiere', description: 'Quiere', type: 'boolean' }],
  },
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

// El formulario en la pestaña Voz (donde vive "Si la persona no responde"), con estado real.
const latest = { current: null as unknown as Draft };

function AttentionHarness({ initial, errors }: { initial: Draft; errors?: FieldError[] }) {
  const [draft, setDraft] = useState(initial);
  useEffect(() => {
    latest.current = draft;
  }, [draft]);
  return (
    <DefinitionForm
      part="voz"
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

describe('DefinitionForm: Si la persona no responde', () => {
  it('la sección se muestra con sus defaults y apagada no guarda nada', async () => {
    mockApi();
    renderWithProviders(<AttentionHarness initial={toDraft(DEF)} />, { me: CLIENT_USER });
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
    renderWithProviders(<AttentionHarness initial={toDraft(DEF)} />, { me: CLIENT_USER });
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
    renderWithProviders(<AttentionHarness initial={d} />, { me: CLIENT_USER });
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
      <AttentionHarness
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
