import { screen } from '@testing-library/react';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import type { Definition } from '@/api/types';
import { CATALOG } from '@/components/variables/fixtures';
import { CLIENT_USER, jsonResponse, renderWithProviders } from '@/test/render';
import { DefinitionForm } from './DefinitionForm';
import { toDraft } from './draft';

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
    outcomes: [{ id: 'ok', label: 'Ok', when: { quiere: true }, goal: true }],
  },
} as Definition;

function mockApi() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL((input instanceof Request ? input : new Request(input)).url);
      if (url.pathname === '/api/v1/variables/catalog') return jsonResponse(CATALOG);
      if (url.pathname.endsWith('/tools')) return jsonResponse([]);
      if (url.pathname === '/api/v1/voices') return jsonResponse([]);
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
